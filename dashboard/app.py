import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
st.set_page_config(
    page_title="💧 Irrigation Intelligente by adib",
    page_icon="💧",
    layout="wide"
)



PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "database": os.getenv("POSTGRES_DB", "irrigation"),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "password123")
}

# ── AUTO REFRESH toutes les 5 secondes ────────────────────
st.markdown(
    "<meta http-equiv='refresh' content='60'>",
    unsafe_allow_html=True
)

# ── CHARGEMENT DONNÉES ────────────────────────────────────
def load_stress():
    conn = psycopg2.connect(**PG_CONFIG)
    df = pd.read_sql("""
        SELECT DISTINCT ON (parcelle_id)
            parcelle_id, etp, score_stress, volume_irrigation, alerte, timestamp
        FROM stress_hydrique
        ORDER BY parcelle_id, timestamp DESC
    """, conn)
    conn.close()
    return df

def load_capteurs():
    conn = psycopg2.connect(**PG_CONFIG)
    df = pd.read_sql("""
        SELECT parcelle_id, humidite_sol, temperature, timestamp
        FROM capteurs_sol
        ORDER BY timestamp DESC
        LIMIT 100
    """, conn)
    conn.close()
    return df

def load_meteo():
    conn = psycopg2.connect(**PG_CONFIG)
    df = pd.read_sql("""
        SELECT parcelle_id, date, temp_max, temp_min, pluie, rayonnement
        FROM meteo ORDER BY date DESC
    """, conn)
    conn.close()
    return df

df_stress   = load_stress()
df_capteurs = load_capteurs()
df_meteo    = load_meteo()
alertes     = df_stress[df_stress["alerte"] == True]

# ── HEADER ────────────────────────────────────────────────
st.title("💧 Gestion Intelligente des Ressources en Eau")
st.caption(f"🕐 Dernière mise à jour : {datetime.now().strftime('%H:%M:%S')} — Refresh auto toutes les 5s")

# ── KPIs ──────────────────────────────────────────────────
st.subheader("📊 État des Parcelles")
col1, col2, col3, col4 = st.columns(4)
col1.metric("🔴 Parcelles en alerte",     len(alertes),                              f"/{len(df_stress)} total")
col2.metric("💧 Volume irrigation total", f"{df_stress['volume_irrigation'].sum():,.0f} L", "aujourd'hui")
col3.metric("🌡️ ETP moyenne",             f"{df_stress['etp'].mean():.2f} mm/j")
col4.metric("📡 Capteurs actifs",          df_capteurs["parcelle_id"].nunique(),       "parcelles")

st.divider()

# ── HUMIDITE TEMPS REEL ───────────────────────────────────
st.subheader("📈 Humidité Sol en Temps Réel (Kafka)")

col_a, col_b, col_c = st.columns(3)
for parcelle, col in zip(["parcelle_1", "parcelle_2", "parcelle_3"], [col_a, col_b, col_c]):
    df_p = df_capteurs[df_capteurs["parcelle_id"] == parcelle]
    if not df_p.empty:
        last = df_p.iloc[0]
        stress_row = df_stress[df_stress["parcelle_id"] == parcelle]
        score = stress_row["score_stress"].values[0] if not stress_row.empty else 0
        emoji = "🔴" if score >= 7 else "🟠" if score >= 4 else "🟢"
        col.metric(
            label=f"{emoji} {parcelle}",
            value=f"{last['humidite_sol']:.1f}%",
            delta=f"🌡️ {last['temperature']:.1f}°C"
        )

fig3 = px.line(
    df_capteurs,
    x="timestamp",
    y="humidite_sol",
    color="parcelle_id",
    color_discrete_map={
        "parcelle_1": "orange",
        "parcelle_2": "green",
        "parcelle_3": "red"
    },
    title="Évolution Humidité Sol — 100 dernières mesures"
)
fig3.add_hline(y=30, line_dash="dash", line_color="red",   annotation_text="Seuil critique (30%)")
fig3.add_hline(y=60, line_dash="dash", line_color="green", annotation_text="Niveau optimal (60%)")
fig3.update_layout(yaxis_title="Humidité (%)", xaxis_title="Temps", height=400)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── STRESS PAR PARCELLE ───────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🌿 Score de Stress Hydrique")
    colors = []
    for _, row in df_stress.iterrows():
        if row["score_stress"] >= 7:
            colors.append("red")
        elif row["score_stress"] >= 4:
            colors.append("orange")
        else:
            colors.append("green")

    fig = go.Figure(go.Bar(
        x=df_stress["parcelle_id"],
        y=df_stress["score_stress"],
        marker_color=colors,
        text=df_stress["score_stress"],
        textposition="outside"
    ))
    fig.add_hline(y=6, line_dash="dash", line_color="red", annotation_text="Seuil alerte")
    fig.update_layout(
        yaxis=dict(range=[0, 10], title="Score (0-10)"),
        xaxis_title="Parcelle",
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("💦 Volume d'Irrigation Recommandé (L)")
    fig2 = px.pie(
        df_stress,
        values="volume_irrigation",
        names="parcelle_id",
        color_discrete_sequence=["#ef553b", "#ffa15a", "#00cc96"]
    )
    fig2.update_layout(height=350)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── ALERTES ───────────────────────────────────────────────
st.subheader("🚨 Alertes Irrigation")
if len(alertes) > 0:
    for _, row in alertes.iterrows():
        st.error(f"""
        🔴 **{row['parcelle_id']}** — Stress critique : {row['score_stress']}/10
        → Volume recommandé : **{row['volume_irrigation']:,.0f} L**
        → ETP : {row['etp']} mm/jour
        """)
else:
    st.success("✅ Aucune alerte — toutes les parcelles sont bien irriguées")

st.divider()

# ── METEO ─────────────────────────────────────────────────
st.subheader("🌤️ Données Météo (Open-Meteo + NASA)")
st.dataframe(
    df_meteo.style.format({
        "temp_max":      "{:.1f}°C",
        "temp_min":      "{:.1f}°C",
        "pluie":         "{:.1f} mm",
        "rayonnement":   "{:.2f}"
    }),
    use_container_width=True
)

# ── REFRESH MANUEL ────────────────────────────────────────
st.button("🔄 Rafraîchir maintenant", on_click=st.cache_data.clear)