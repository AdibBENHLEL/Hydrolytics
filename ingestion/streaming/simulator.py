import time
import json
import random
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka1:9094")
TOPIC = os.getenv("TOPIC", "capteurs-sol")

PARCELLES = {
    "parcelle_1": {"humidity_range": (25, 45), "temp_range": (20, 38), "ph": 6.2},
    "parcelle_2": {"humidity_range": (45, 65), "temp_range": (18, 32), "ph": 6.8},
    "parcelle_3": {"humidity_range": (15, 35), "temp_range": (22, 40), "ph": 7.1},
}

print("🔄 Waiting for Kafka to be ready...")
producer = None
max_retries = 20  # ← attendre jusqu'à 100 secondes

for attempt in range(max_retries):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(3, 7, 0),
            request_timeout_ms=30000,
            metadata_max_age_ms=10000
        )
        # Test que Kafka répond vraiment
        producer.bootstrap_connected()
        print(f"✅ Connected to Kafka! ({KAFKA_BROKER})")
        break
    except Exception as e:
        print(f"⚠️ Tentative {attempt+1}/{max_retries} — Kafka pas prêt: {e}")
        time.sleep(5)

if producer is None:
    print("❌ Impossible de se connecter à Kafka après 20 tentatives")
    exit(1)

print("✅ Sending data...")
while True:
    try:
        for parcelle_id, config in PARCELLES.items():
            data = {
                "parcelle_id": parcelle_id,
                "sensor_id": int(parcelle_id.split("_")[1]),
                "humidity": round(random.uniform(*config["humidity_range"]), 2),
                "temperature": round(random.uniform(*config["temp_range"]), 2),
                "ph_sol": round(config["ph"] + random.uniform(-0.2, 0.2), 2)
            }
            producer.send(TOPIC, data)
            print(f"Sent: {data}")
        producer.flush()
        time.sleep(5)
    except Exception as e:
        print(f"❌ Erreur envoi: {e}")
        time.sleep(5)