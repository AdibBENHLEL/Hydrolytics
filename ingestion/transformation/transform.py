import psycopg2
import logging
import os
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "database": os.getenv("POSTGRES_DB", "irrigation"),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "password123")
}
def calcul_etp(temp_max, temp_min, rayonnement):
    if None in (temp_max, temp_min, rayonnement):
        return 0.0
    t_max = max(temp_max, temp_min)
    t_min = min(temp_max, temp_min)
    diff  = max(t_max - t_min, 0.1)
    etp   = 0.0023 * diff**0.5 * (t_max + 17.8) * max(rayonnement, 1)
    return round(max(0, etp), 2)

def calcul_stress(etp, humidite_sol, pluie):
    if humidite_sol is None:
        humidite_sol = 50.0
    if humidite_sol < 20:
        score = 9.0
    elif humidite_sol < 30:
        score = 7.0
    elif humidite_sol < 40:
        score = 5.0
    elif humidite_sol < 50:
        score = 3.0
    elif humidite_sol < 60:
        score = 1.5
    else:
        score = 0.5
    return round(score, 2)

def calcul_volume(etp, pluie, humidite_sol, surface_m2=1000):
    if humidite_sol is None:
        humidite_sol = 50.0
    pluie = pluie or 0
    deficit_humidite = max(0, 60 - humidite_sol) / 100
    volume = deficit_humidite * surface_m2 * 10
    return round(volume, 2)

def run():
    log.info("🚀 Démarrage des transformations")
    conn = psycopg2.connect(**PG_CONFIG)
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM capteurs_sol")
    count = cur.fetchone()[0]
    log.info(f"💧 {count} lignes dans capteurs_sol")

    cur.execute("""
        SELECT parcelle_id, AVG(humidite_sol)
        FROM capteurs_sol GROUP BY parcelle_id
    """)
    humidity_map = {r[0]: r[1] for r in cur.fetchall()}
    log.info(f"💧 Parcelles : {list(humidity_map.keys())}")

    cur.execute("""
        SELECT parcelle_id, date, temp_max, temp_min, pluie, rayonnement
        FROM meteo ORDER BY date
    """)
    rows = cur.fetchall()
    log.info(f"📊 {len(rows)} lignes météo")

    inserted = 0
    for row in rows:
        parcelle_id, date, temp_max, temp_min, pluie, rayonnement = row
        humidite_sol = humidity_map.get(parcelle_id, 50.0)

        etp    = calcul_etp(temp_max, temp_min, rayonnement)
        stress = calcul_stress(etp, humidite_sol, pluie)
        volume = calcul_volume(etp, pluie, humidite_sol)
        alerte = stress > 6

        log.info(f"  {parcelle_id} | ETP={etp} | stress={stress} | alerte={alerte}")

        cur.execute("""
            INSERT INTO stress_hydrique
                (parcelle_id, etp, score_stress, volume_irrigation, alerte)
            VALUES (%s, %s, %s, %s, %s)
        """, (parcelle_id, etp, stress, volume, alerte))
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    log.info(f"✅ {inserted} lignes insérées")

if __name__ == "__main__":
    run()