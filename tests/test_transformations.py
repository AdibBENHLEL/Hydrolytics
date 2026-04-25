import pytest
import sys
import os

# Ajouter le chemin vers transform.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ingestion', 'transformation'))
from transform import calcul_etp, calcul_stress, calcul_volume

# ════════════════════════════════════════════
# TESTS ETP
# ════════════════════════════════════════════

def test_etp_valeurs_normales():
    """ETP doit être positive avec des valeurs normales"""
    result = calcul_etp(30, 15, 5)
    assert result > 0

def test_etp_valeur_none():
    """ETP doit retourner 0.0 si une valeur est None"""
    assert calcul_etp(None, 15, 5) == 0.0
    assert calcul_etp(30, None, 5) == 0.0
    assert calcul_etp(30, 15, None) == 0.0

def test_etp_temperatures_inversees():
    """ETP doit être identique peu importe l'ordre des températures"""
    result1 = calcul_etp(30, 15, 5)
    result2 = calcul_etp(15, 30, 5)
    assert result1 == result2

def test_etp_toujours_positive():
    """ETP ne doit jamais être négative"""
    result = calcul_etp(10, 9, 0.1)
    assert result >= 0

# ════════════════════════════════════════════
# TESTS STRESS HYDRIQUE
# ════════════════════════════════════════════

def test_stress_sol_tres_sec():
    """Humidité < 20% → stress = 9.0 (critique)"""
    result = calcul_stress(0.5, 15, 0)
    assert result == 9.0

def test_stress_sol_sec():
    """Humidité entre 20-30% → stress = 7.0"""
    result = calcul_stress(0.5, 25, 0)
    assert result == 7.0

def test_stress_sol_modere():
    """Humidité entre 30-40% → stress = 5.0"""
    result = calcul_stress(0.5, 35, 0)
    assert result == 5.0

def test_stress_sol_correct():
    """Humidité > 60% → stress = 0.5 (optimal)"""
    result = calcul_stress(0.5, 70, 2)
    assert result == 0.5

def test_stress_humidite_none():
    """Humidité None → valeur par défaut 50% → stress = 1.5"""
    result = calcul_stress(0.5, None, 0)
    assert result == 1.5  # ← 50% humidité = score 1.5

# ════════════════════════════════════════════
# TESTS VOLUME IRRIGATION
# ════════════════════════════════════════════

def test_volume_sol_sec():
    """Sol à 20% humidité → volume positif nécessaire"""
    result = calcul_volume(0.5, 0, 20)
    assert result == 4000.0  # (60-20)/100 * 1000 * 10

def test_volume_sol_humide():
    """Sol > 60% → pas d'irrigation nécessaire"""
    result = calcul_volume(0.5, 0, 65)
    assert result == 0.0

def test_volume_toujours_positif():
    """Volume ne doit jamais être négatif"""
    result = calcul_volume(0.5, 10, 30)
    assert result >= 0

# ════════════════════════════════════════════
# TESTS ALERTES
# ════════════════════════════════════════════

def test_alerte_declenchee():
    """Stress > 6 → alerte = True"""
    stress = calcul_stress(0.5, 15, 0)  # stress = 9.0
    assert stress > 6
    assert (stress > 6) == True

def test_pas_alerte_sol_humide():
    """Stress < 6 → alerte = False"""
    stress = calcul_stress(0.5, 70, 2)  # stress = 0.5
    assert stress <= 6
    assert (stress > 6) == False