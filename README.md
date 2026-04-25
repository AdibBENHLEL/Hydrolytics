# 💧 Gestion Intelligente des Ressources en Eau Agricole
## Pipeline Data Engineering End-to-End

> **Auteur :** Adib Ben Hlel  
> **Problème résolu :** Les agriculteurs gaspillent jusqu'à 40% de l'eau d'irrigation par manque de données en temps réel. Ce pipeline centralise météo, humidité du sol et consommation d'eau pour déclencher automatiquement des alertes et optimiser l'irrigation.

---

## 📋 Table des matières

- [Description du projet](#description)
- [Architecture](#architecture)
- [Sources de données](#sources)
- [Stack technologique](#stack)
- [Structure du projet](#structure)
- [Installation](#installation)
- [Déploiement](#deploiement)
- [Tests](#tests)
- [URLs d'accès](#urls)

---

## 📖 Description du projet <a name="description"></a>

Ce projet est un pipeline Data Engineering complet qui :

- **Collecte** des données météo (Open-Meteo, NASA POWER) et des données de capteurs IoT simulés via Kafka
- **Stocke** les données brutes dans MinIO (Data Lake) et les données transformées dans PostgreSQL
- **Transforme** les données pour calculer l'évapotranspiration (ETP), le stress hydrique et les recommandations d'irrigation
- **Orchestre** automatiquement le pipeline via n8n (toutes les heures)
- **Visualise** les résultats en temps réel via un dashboard Streamlit

---

## 🏗️ Architecture <a name="architecture"></a>

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INGESTION                                   │
│                                                                     │
│  [Open-Meteo API] ──batch──►┐                                       │
│  [NASA POWER API] ──batch──►├──► MinIO (Raw Zone / Data Lake)       │
│  [IoT Simulator]  ─stream──►┘         │                             │
│       │                               │                             │
│       ▼                               ▼                             │
│    Kafka ──► kafka-consumer ──► PostgreSQL (Clean Zone)             │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION                                 │
│                                                                     │
│   PostgreSQL (meteo + capteurs_sol)                                 │
│         │                                                           │
│         ▼                                                           │
│   transform.py                                                      │
│   ├── Calcul ETP (Hargreaves)                                       │
│   ├── Indice de Stress Hydrique (0-10)                              │
│   └── Volume Irrigation recommandé (L/m²)                          │
│         │                                                           │
│         ▼                                                           │
│   PostgreSQL (stress_hydrique)                                      │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION                                  │
│                                                                     │
│   n8n (Schedule toutes les heures)                                  │
│   ├── HTTP POST → /run/ingestion  (open_meteo + nasa_power)         │
│   ├── HTTP POST → /run/transform  (calculs ETP + stress)            │
│   ├── HTTP GET  → /status         (vérification données)            │
│   └── IF alerte → Code JS (CRITIQUE / OK)                          │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      VISUALISATION                                  │
│                                                                     │
│   Streamlit Dashboard (http://localhost:8501)                       │
│   ├── KPIs : alertes, volume total, ETP, capteurs actifs            │
│   ├── Humidité sol temps réel (Kafka) — refresh 5s                  │
│   ├── Score stress hydrique par parcelle (rouge/orange/vert)        │
│   ├── Volume irrigation recommandé (camembert)                      │
│   ├── Alertes critiques                                             │
│   └── Données météo historiques                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📡 Sources de données <a name="sources"></a>

| Source | Type | Outil | Données |
|--------|------|-------|---------|
| **Open-Meteo API** | Batch planifié (horaire) | Python + requests | Température max/min, précipitations, ETP FAO |
| **NASA POWER API** | Batch planifié (horaire) | Python + requests | Rayonnement solaire, humidité atmosphérique |
| **IoT Simulateur** | Streaming temps réel | Kafka + Python | Humidité sol, température, pH sol |

> ✅ Toutes les sources sont **gratuites** — aucune carte bancaire requise.  
> ✅ Les capteurs IoT sont simulés par un script Python (pratique standard en Data Engineering).

---

## 🛠️ Stack technologique <a name="stack"></a>

| Couche | Technologie | Justification |
|--------|-------------|---------------|
| **Ingestion Batch** | Python + requests | Léger, compatible toutes APIs REST |
| **Streaming** | Apache Kafka 3.7.0 | Standard industrie pour le temps réel |
| **Simulateur IoT** | Python (kafka-python) | Remplace le hardware — pas de matériel requis |
| **Data Lake** | MinIO | Compatible S3, dockerisable, 100% gratuit |
| **Base de données** | PostgreSQL 15 | Relationnel, stable, performant |
| **Transformation** | Python + Pandas | Lisible, testable, transformations documentées |
| **Orchestration** | n8n | Interface visuelle drag & drop, scheduling intégré, retry natif |
| **API Pipeline** | Flask | Expose les scripts Python pour n8n |
| **Visualisation** | Streamlit | Python natif, déploiement rapide, refresh auto |
| **Déploiement** | Docker Compose | Reproductible, tout-en-un |

---

## 📁 Structure du projet <a name="structure"></a>

```
project Big data/
├── docker-compose.yml
├── README.md
├── ingestion/
│   ├── batch/
│   │   ├── open_meteo.py          # Ingestion API Open-Meteo
│   │   ├── nasa_power.py          # Ingestion API NASA POWER
│   │   └── requirements.txt
│   ├── streaming/
│   │   ├── simulator.py           # Simulateur capteurs IoT → Kafka
│   │   ├── kafka_consumer.py      # Consumer Kafka → PostgreSQL
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── transformation/
│       └── transform.py           # 3 transformations métier
├── api/
│   ├── pipeline_api.py            # API Flask pour n8n
│   ├── Dockerfile
│   └── requirements.txt
├── dashboard/
│   ├── app.py                     # Dashboard Streamlit
│   ├── Dockerfile
│   └── requirements.txt
└── tests/
    └── test_transformations.py    # 10 tests unitaires
```

---

## 🔄 Transformations métier

### 1. Calcul de l'Évapotranspiration (ETP)
Formule de Hargreaves simplifiée combinant température max/min et rayonnement solaire.

```python
def calcul_etp(temp_max, temp_min, rayonnement):
    diff = max(temp_max - temp_min, 0.1)
    etp  = 0.0023 * diff**0.5 * (temp_max + 17.8) * rayonnement
    return round(max(0, etp), 2)
```

### 2. Indice de Stress Hydrique (0-10)
Score basé sur l'humidité du sol — plus le sol est sec, plus le score est élevé.

| Humidité sol | Score | Niveau |
|-------------|-------|--------|
| < 20% | 9.0 | 🔴 Critique |
| 20-30% | 7.0 | 🔴 Élevé |
| 30-40% | 5.0 | 🟠 Modéré |
| 40-50% | 3.0 | 🟡 Faible |
| 50-60% | 1.5 | 🟢 Normal |
| > 60% | 0.5 | 🟢 Optimal |

### 3. Volume d'Irrigation Recommandé
Calcule le volume d'eau nécessaire pour ramener l'humidité à 60%.

```python
def calcul_volume(etp, pluie, humidite_sol, surface_m2=1000):
    deficit  = max(0, 60 - humidite_sol) / 100
    volume   = deficit * surface_m2 * 10
    return round(volume, 2)
```

---

## 🚀 Installation <a name="installation"></a>

### Prérequis

- Docker Desktop installé et démarré
- Python 3.9+ (pour lancer les scripts localement si besoin)
- Git

### 1. Cloner le dépôt

```bash
git clone https://github.com/AdibBENHLEL/Hydrolytics.git
```

### 2. pull the image puis Lancer tous les services

docker pull adibbh/hydrolytics

```bash
docker-compose up -d --build
```

### 3. Vérifier que tout tourne

```bash
docker-compose ps
```

Résultat attendu :
```
NAME            STATUS
iot-simulator   Up
kafka1          Up
kafka-consumer  Up
minio           Up
n8n             Up
pipeline-api    Up
postgres        Up
streamlit       Up
```

### 4. Créer les tables PostgreSQL

```bash
docker exec -it postgres psql -U admin -d irrigation
```

```sql
CREATE TABLE meteo (
    id           SERIAL PRIMARY KEY,
    timestamp    TIMESTAMP DEFAULT NOW(),
    date         DATE,
    parcelle_id  VARCHAR(20),
    temp_max     FLOAT,
    temp_min     FLOAT,
    pluie        FLOAT,
    rayonnement  FLOAT,
    humidite_atm FLOAT
);

CREATE TABLE capteurs_sol (
    id           SERIAL PRIMARY KEY,
    timestamp    TIMESTAMP DEFAULT NOW(),
    parcelle_id  VARCHAR(20),
    humidite_sol FLOAT,
    temperature  FLOAT,
    ph_sol       FLOAT
);

CREATE TABLE stress_hydrique (
    id                SERIAL PRIMARY KEY,
    timestamp         TIMESTAMP DEFAULT NOW(),
    parcelle_id       VARCHAR(20),
    etp               FLOAT,
    score_stress      FLOAT,
    volume_irrigation FLOAT,
    alerte            BOOLEAN
);
```

### 5. Créer le bucket MinIO

Ouvre http://localhost:9001 → login `admin / password123` → crée le bucket `raw-data`.

### 6. Configurer n8n

Ouvre http://localhost:5678 → importe le workflow `Pipeline Irrigation` avec les nodes :

```
[Schedule: toutes les heures]
        │
        ▼
[HTTP POST → http://pipeline-api:8000/run/ingestion]
        │
        ▼
[HTTP POST → http://pipeline-api:8000/run/transform]
        │
        ▼
[HTTP GET  → http://pipeline-api:8000/status]
        │
        ▼
[IF stress_hydrique_count > 0]
  ├── true  → 🔴 ALERTE IRRIGATION
  └── false → ✅ Pipeline OK
```

---

## 🧪 Tests <a name="tests"></a>

```bash
pip install pytest
pytest tests/test_transformations.py -v
```

10 tests unitaires couvrant :
- Calcul ETP normal, avec valeurs None, avec températures inversées
- Score stress critique, optimal, modéré
- Volume irrigation sol sec et sol humide
- Déclenchement et non-déclenchement des alertes

---

## 🌐 URLs d'accès <a name="urls"></a>

| Service | URL | Credentials |
|---------|-----|-------------|
| **Streamlit Dashboard** | http://localhost:8501 | — |
| **n8n Orchestration** | http://localhost:5678 | admin / password123 |
| **MinIO Console** | http://localhost:9001 | admin / password123 |
| **Kafka** | localhost:9092 | — |
| **PostgreSQL** | localhost:5432 | admin / password123 / irrigation |
| **Pipeline API** | http://localhost:8000 | — |

### Endpoints API Flask

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/run/ingestion` | POST | Lance Open-Meteo + NASA POWER |
| `/run/transform` | POST | Lance les transformations |
| `/status` | GET | État du pipeline |

---

## 📊 Résultats observés

| Parcelle | Humidité Sol | Score Stress | Alerte |
|----------|-------------|-------------|--------|
| parcelle_3 | ~23% | 7.0 | 🔴 CRITIQUE |
| parcelle_1 | ~33% | 5.0 | 🟠 MODÉRÉ |
| parcelle_2 | ~55% | 1.5 | 🟢 OK |

---

## 📝 Licence

MIT License — Projet académique Data Engineering 2026
