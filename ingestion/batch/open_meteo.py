import requests
import json
import boto3
import psycopg2
from datetime import datetime, date
import logging
import os

# ── Logging structuré ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────
PARCELLES = [
    {"id": "parcelle_1", "lat": 36.8, "lon": 10.1},
    {"id": "parcelle_2", "lat": 36.9, "lon": 10.2},
    {"id": "parcelle_3", "lat": 37.0, "lon": 10.3},
]


MINIO_CONFIG = {
    "endpoint_url":          f"http://{os.getenv('MINIO_HOST', 'minio')}:9000",
    "aws_access_key_id":  ${MINIO_ROOT_USER},
    "aws_secret_access_key":${MINIO_ROOT_PASSWORD}
}


DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "database": os.getenv("POSTGRES_DB", "irrigation"),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "password123")
}

# ── MinIO client ───────────────────────────────────────────
s3 = boto3.client("s3", **MINIO_CONFIG)

def fetch_open_meteo(parcelle):
    """Appel API Open-Meteo avec retry"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": parcelle["lat"],
        "longitude": parcelle["lon"],
        "daily": ["temperature_2m_max", "temperature_2m_min",
                  "precipitation_sum", "et0_fao_evapotranspiration"],
        "forecast_days": 3,
        "timezone": "Africa/Tunis"
    }

    for attempt in range(3):  # retry 3 fois
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            log.info(f"✅ Open-Meteo OK — {parcelle['id']}")
            return response.json()
        except Exception as e:
            log.warning(f"⚠️ Tentative {attempt+1}/3 échouée : {e}")

    log.error(f"❌ Open-Meteo FAILED — {parcelle['id']}")
    return None

def save_to_minio(data, parcelle_id):
    """Sauvegarde raw data dans MinIO"""
    key = f"meteo/open_meteo/{parcelle_id}/{date.today()}.json"
    s3.put_object(
        Bucket="raw-data",
        Key=key,
        Body=json.dumps(data)
    )
    log.info(f"✅ MinIO saved — {key}")

def save_to_postgres(data, parcelle_id):
    """Insère données transformées dans PostgreSQL"""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    daily = data["daily"]
    for i in range(len(daily["time"])):
        cur.execute("""
            INSERT INTO meteo (date, parcelle_id, temp_max, temp_min, pluie, rayonnement)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            daily["time"][i],
            parcelle_id,
            daily["temperature_2m_max"][i],
            daily["temperature_2m_min"][i],
            daily["precipitation_sum"][i],
            daily["et0_fao_evapotranspiration"][i]
        ))

    conn.commit()
    cur.close()
    conn.close()
    log.info(f"✅ PostgreSQL inserted — {parcelle_id}")

def run():
    log.info("🚀 Démarrage ingestion Open-Meteo")
    for parcelle in PARCELLES:
        data = fetch_open_meteo(parcelle)
        if data:
            save_to_minio(data, parcelle["id"])
            save_to_postgres(data, parcelle["id"])
    log.info("✅ Ingestion Open-Meteo terminée")

if __name__ == "__main__":
    run()