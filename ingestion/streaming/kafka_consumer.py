import json
import psycopg2
import logging
from kafka import KafkaConsumer
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka1:9094")


PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "database": os.getenv("POSTGRES_DB", "irrigation"),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "password123")
}


def get_connection():
    return psycopg2.connect(**PG_CONFIG)

consumer = KafkaConsumer(
    "capteurs-sol",
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="irrigation-live"
)

log.info("🎧 Consumer démarré — en attente de messages...")
count = 0

for message in consumer:
    data = message.value
    try:
        parcelle_id = data.get("parcelle_id", f"parcelle_{data.get('sensor_id', 1)}")
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO capteurs_sol (parcelle_id, humidite_sol, temperature, ph_sol)
            VALUES (%s, %s, %s, %s)
        """, (
            parcelle_id,
            data.get("humidity"),
            data.get("temperature"),
            data.get("ph_sol", 6.5)
        ))
        conn.commit()
        cur.close()
        conn.close()
        count += 1
        log.info(f"✅ [{count}] {parcelle_id} | humidity={data.get('humidity')} | temp={data.get('temperature')}")
    except Exception as e:
        log.error(f"❌ Erreur : {e}")