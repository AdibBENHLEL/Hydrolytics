from flask import Flask, jsonify
import subprocess
import psycopg2
import os

app = Flask(__name__)

# ── Dans Docker, les scripts sont dans /app ────────────────
BASE_DIR = "/app"

# ── Config depuis variables d'environnement Docker ─────────
PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "database": os.getenv("POSTGRES_DB", "irrigation"),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "password123")
}

MINIO_HOST = os.getenv("MINIO_HOST", "minio")

@app.route('/run/ingestion', methods=['POST'])
def run_ingestion():
    env = {
        **os.environ,
        "POSTGRES_HOST": PG_CONFIG["host"],
        "MINIO_HOST":    MINIO_HOST
    }
    r1 = subprocess.run(
        ['python', f"{BASE_DIR}/ingestion/batch/open_meteo.py"],
        capture_output=True, text=True, cwd=BASE_DIR, env=env
    )
    r2 = subprocess.run(
        ['python', f"{BASE_DIR}/ingestion/batch/nasa_power.py"],
        capture_output=True, text=True, cwd=BASE_DIR, env=env
    )
    return jsonify({
        "status": "ok",
        "open_meteo": r1.stdout or r1.stderr,
        "nasa":       r2.stdout or r2.stderr
    })

@app.route('/run/transform', methods=['POST'])
def run_transform():
    env = {
        **os.environ,
        "POSTGRES_HOST": PG_CONFIG["host"]
    }
    r = subprocess.run(
        ['python', f"{BASE_DIR}/ingestion/transformation/transform.py"],
        capture_output=True, text=True, cwd=BASE_DIR, env=env
    )
    return jsonify({
        "status": "ok",
        "output": r.stdout or r.stderr
    })

@app.route('/status', methods=['GET'])
def status():
    conn = psycopg2.connect(**PG_CONFIG)
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM stress_hydrique WHERE alerte = true")
    alertes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM capteurs_sol")
    capteurs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM meteo")
    meteo = cur.fetchone()[0]
    conn.close()
    return jsonify({
        "stress_hydrique_count": alertes,
        "capteurs_count":        capteurs,
        "meteo_count":           meteo,
        "pipeline_status":       "OK"
    })

if __name__ == '__main__':
    print(f"🚀 Pipeline API démarrée — BASE_DIR: {BASE_DIR}")
    print(f"🐘 PostgreSQL: {PG_CONFIG['host']}")
    print(f"🪣 MinIO: {MINIO_HOST}")
    app.run(host='0.0.0.0', port=8000, debug=False)