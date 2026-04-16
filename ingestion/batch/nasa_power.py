import requests
import json
import boto3
import psycopg2
from datetime import datetime, date
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

PARCELLES = [
    {"id": "parcelle_1", "lat": 36.8, "lon": 10.1},
    {"id": "parcelle_2", "lat": 36.9, "lon": 10.2},
    {"id": "parcelle_3", "lat": 37.0, "lon": 10.3},
]


MINIO_CONFIG = {
    "endpoint_url":          f"http://{os.getenv('MINIO_HOST', 'minio')}:9000",
    "aws_access_key_id":     ${MINIO_ROOT_USER},
    "aws_secret_access_key": ${MINIO_ROOT_PASSWORD}
}


DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "database": os.getenv("POSTGRES_DB", "irrigation"),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "password123")
}

s3 = boto3.client("s3", **MINIO_CONFIG)

def fetch_nasa_power(parcelle):
    """Appel API NASA POWER avec retry"""
    today = date.today().strftime("%Y%m%d")
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,RH2M",
        "community": "AG",
        "longitude": parcelle["lon"],
        "latitude": parcelle["lat"],
        "start": today,
        "end": today,
        "format": "JSON"
    }

    for attempt in range(3):  # retry 3 fois
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            log.info(f"✅ NASA POWER OK — {parcelle['id']}")
            return response.json()
        except Exception as e:
            log.warning(f"⚠️ Tentative {attempt+1}/3 échouée : {e}")

    log.error(f"❌ NASA POWER FAILED — {parcelle['id']}")
    return None

def save_to_minio(data, parcelle_id):
    key = f"meteo/nasa_power/{parcelle_id}/{date.today()}.json"
    s3.put_object(
        Bucket="raw-data",
        Key=key,
        Body=json.dumps(data)
    )
    log.info(f"✅ MinIO saved — {key}")

def save_to_postgres(data, parcelle_id):
    """Enrichit la table meteo avec rayonnement + humidité atm"""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    properties = data.get("properties", {}).get("parameter", {})
    today = date.today().strftime("%Y-%m-%d")

    rayonnement = list(properties.get("ALLSKY_SFC_SW_DWN", {}).values())
    humidite    = list(properties.get("RH2M", {}).values())

    if rayonnement and humidite:
        cur.execute("""
            UPDATE meteo
            SET rayonnement  = %s,
                humidite_atm = %s
            WHERE date = %s AND parcelle_id = %s
        """, (rayonnement[0], humidite[0], today, parcelle_id))

    conn.commit()
    cur.close()
    conn.close()
    log.info(f"✅ PostgreSQL updated — {parcelle_id}")

def run():
    log.info("🚀 Démarrage ingestion NASA POWER")
    for parcelle in PARCELLES:
        data = fetch_nasa_power(parcelle)
        if data:
            save_to_minio(data, parcelle["id"])
            save_to_postgres(data, parcelle["id"])
    log.info("✅ Ingestion NASA POWER terminée")

if __name__ == "__main__":
    run()