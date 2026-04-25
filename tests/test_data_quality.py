import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ingestion', 'transformation'))
from transform import calcul_etp, calcul_stress, calcul_volume

# ════════════════════════════════════════════
# TESTS QUALITE DES DONNEES
# ════════════════════════════════════════════

def test_etp_range_realiste():
    """ETP doit être dans une plage réaliste (0-20 mm/jour)"""
    result = calcul_etp(35, 20, 8)
    assert 0 <= result <= 20

def test_stress_range_valide():
    """Score stress doit toujours être entre 0 et 10"""
    for humidite in [10, 25, 35, 45, 55, 70]:
        result = calcul_stress(0.5, humidite, 0)
        assert 0 <= result <= 10, f"Score hors range pour humidité={humidite}"

def test_volume_range_valide():
    """Volume irrigation doit être entre 0 et 6000L pour 1000m²"""
    for humidite in [0, 20, 40, 60, 80]:
        result = calcul_volume(0.5, 0, humidite)
        assert 0 <= result <= 6000, f"Volume hors range pour humidité={humidite}"

def test_coherence_stress_volume():
    """Plus le stress est élevé, plus le volume doit être grand"""
    volume_sec    = calcul_volume(0.5, 0, 20)  # sol très sec
    volume_humide = calcul_volume(0.5, 0, 55)  # sol humide
    assert volume_sec > volume_humide

def test_parcelles_differentes():
    """3 parcelles avec humidités différentes → 3 scores différents"""
    stress_p1 = calcul_stress(0.5, 33, 0)  # parcelle_1
    stress_p2 = calcul_stress(0.5, 55, 0)  # parcelle_2
    stress_p3 = calcul_stress(0.5, 23, 0)  # parcelle_3
    assert stress_p3 > stress_p1 > stress_p2