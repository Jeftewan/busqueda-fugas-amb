import streamlit as st
import sys, os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models import get_crew_performance
from src.ui import (
    inject_global_css, render_sidebar_header, empty_state,
    section_header, crew_card, COLOR,
)

st.set_page_config(page_title="Cuadrillas", page_icon="👷", layout="wide")
inject_global_css()

with st.sidebar:
    render_sidebar_header(active_page="cuadrillas")

st.markdown("# 👷 Productividad de Cuadrillas")
st.caption("Comparativa entre equipos y tendencia de productividad")

df = get_crew_performance()
if df.empty:
    empty_state(
        "👷", "Sin datos de cuadrillas",
        "Importa el Excel para ver la productividad diaria por cuadrilla.",
        cta_label="📥 Cargar Excel",
        cta_page="pages/5_Cargar_Excel.py",
    )
    st.stop()

# Renombrar
df.columns = ["date", "crew", "work_hours", "pois_investigated", "leaks",
              "suspected", "quiet", "unverifiable", "pipe_length_km"]

# Asegurar fechas
df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
df = df.dropna(subset=["date"])

# ───── FILTRO DE RANGO ──────────────────────────────────────────────────
fecha_min = df["date"].min().date()
fecha_max = df["date"].max().date()

with st.sidebar:
    st.markdown("### 📅 Rango de fechas")
    rango = st.date_input(
        "Período de análisis",
        value=(max(fecha_min, fecha_max - timedelta(days=30)), fecha_max),
        min_value=fecha_min, max_value=fecha_max,
        key="crew_dates",
    )

# Filtrar por rango
if isinstance(rango, tuple) and len(rango) == 2:
    desde, hasta = rango
    df = df[(df["date"] >= pd.to_datetime(desde)) & (df["date"] <= pd.to_datetime(hasta))]

if df.empty:
    empty_state("📅", "Sin datos en el rango", "Selecciona un rango de fechas que contenga datos.")
    st.stop()

# ───── KPIs CUADRILLAS LADO A LADO ─────────────────────────────────────
section_header("Comparativa entre cuadrillas",
               subtitle=f"Datos del {desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}")

kpis_crew = df.groupby("crew").agg(
    dias_trabajo=("date", "count"),
    total_pois=("pois_investigated", "sum"),
    total_fugas=("leaks", "sum"),
    total_km=("pipe_length_km", "sum"),
    horas_total=("work_hours", "sum"),
).reset_index()

kpis_crew["tasa_deteccion"] = (kpis_crew["total_fugas"] / kpis_crew["total_pois"] * 100).round(1)
kpis_crew["km_por_dia"] = (kpis_crew["total_km"] / kpis_crew["dias_trabajo"]).round(2)
kpis_crew["pois_por_dia"] = (kpis_crew["total_pois"] / kpis_crew["dias_trabajo"]).round(1)

# Calcular máximos para barras comparativas
maximos = {
    "POIs investigados": int(kpis_crew["total_pois"].max()),
    "Fugas detectadas": int(kpis_crew["total_fugas"].max()),
    "Tasa detección": float(kpis_crew["tasa_deteccion"].max()),
    "KM totales": float(kpis_crew["total_km"].max()),
    "POIs/día prom.": float(kpis_crew["pois_por_dia"].max()),
}

cols = st.columns(len(kpis_crew))
for i, (_, row) in enumerate(kpis_crew.iterrows()):
    metrics = {
        "POIs investigados": int(row["total_pois"]),
        "Fugas detectadas": int(row["total_fugas"]),
        "Tasa detección": f"{row['tasa_deteccion']}%",
        "KM totales": f"{row['total_km']:.1f}",
        "POIs/día prom.": row["pois_por_dia"],
    }
    with cols[i]:
        crew_card(row["crew"], metrics, maximos)

st.markdown("<br>", unsafe_allow_html=True)


# ───── GRÁFICOS ────────────────────────────────────────────────────────
def style_fig(fig, title=None, subtitle=None):
    fig.update_layout(
        font=dict(family="Inter, sans-serif", size=12, color=COLOR["text"]),
        margin=dict(t=60, b=30, l=20, r=20),
        paper_bgcolor="white", plot_bgcolor="white",
    )
    if title:
        fig.update_layout(title=dict(
            text=f"<b>{title}</b>" + (f"<br><span style='font-size:11px;color:{COLOR['text_2']}'>{subtitle}</span>" if subtitle else ""),
            x=0.02, y=0.96, font=dict(size=14),
        ))
    return fig


col_a, col_b = st.columns(2)

with col_a:
    metricas = ["total_pois", "total_fugas", "total_km"]
    df_comp = kpis_crew.melt(id_vars="crew", value_vars=metricas,
                              var_name="Métrica", value_name="Valor")
    labels = {"total_pois": "Total POIs", "total_fugas": "Total Fugas", "total_km": "Total KM"}
    df_comp["Métrica"] = df_comp["Métrica"].map(labels)
    fig = px.bar(df_comp, x="Métrica", y="Valor", color="crew", barmode="group",
                 color_discrete_sequence=[COLOR["primary"], COLOR["accent"], COLOR["primary_lt"]],
                 text="Valor")
    fig.update_traces(textposition="outside", marker=dict(line=dict(width=0)))
    fig = style_fig(fig, title="Comparativa de volumen", subtitle="POIs investigados, fugas detectadas y kilómetros recorridos")
    fig.update_layout(height=380, xaxis_title=None, yaxis_title=None,
                      legend=dict(orientation="h", yanchor="bottom", y=-0.2, x=0, title=""),
                      yaxis=dict(showgrid=True, gridcolor="#F0F4F8"))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    df_sorted = df.sort_values("date")
    fig2 = px.line(df_sorted, x="date", y="pois_investigated", color="crew",
                   markers=True,
                   color_discrete_sequence=[COLOR["primary"], COLOR["accent"], COLOR["primary_lt"]])
    fig2.update_traces(line=dict(width=2.5), marker=dict(size=7))
    fig2 = style_fig(fig2, title="Tendencia diaria de POIs investigados",
                     subtitle="Productividad día a día por cuadrilla")
    fig2.update_layout(height=380, xaxis_title=None, yaxis_title="POIs",
                       legend=dict(orientation="h", yanchor="bottom", y=-0.2, x=0, title=""),
                       yaxis=dict(showgrid=True, gridcolor="#F0F4F8"),
                       xaxis=dict(showgrid=False))
    st.plotly_chart(fig2, use_container_width=True)

# ───── HEATMAP SEMANAL ──────────────────────────────────────────────────
section_header("Heatmap semanal", subtitle="Intensidad de trabajo por día de la semana y cuadrilla")

df["dia_semana"] = df["date"].dt.day_name()
DIAS_ES = {"Monday": "Lun", "Tuesday": "Mar", "Wednesday": "Mié", "Thursday": "Jue",
           "Friday": "Vie", "Saturday": "Sáb", "Sunday": "Dom"}
df["dia_semana"] = df["dia_semana"].map(DIAS_ES)

heatmap = df.groupby(["crew", "dia_semana"])["pois_investigated"].sum().reset_index()
orden_dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
heatmap["dia_semana"] = pd.Categorical(heatmap["dia_semana"], categories=orden_dias, ordered=True)
heatmap_pivot = heatmap.pivot(index="crew", columns="dia_semana", values="pois_investigated").fillna(0)

fig3 = px.imshow(
    heatmap_pivot, aspect="auto", color_continuous_scale=[
        [0, "#F7F9FB"], [0.3, "#4FB8E6"], [0.6, "#0B6E99"], [1, "#0F2A3E"]
    ],
    text_auto=".0f", labels=dict(x="Día de la semana", y="Cuadrilla", color="POIs"),
)
fig3.update_traces(textfont=dict(family="Inter", size=12, color="white"))
fig3 = style_fig(fig3, title=None)
fig3.update_layout(height=240, margin=dict(t=20, b=20, l=20, r=20),
                   coloraxis_showscale=False)
st.plotly_chart(fig3, use_container_width=True)

# ───── DETALLE DIARIO ──────────────────────────────────────────────────
with st.expander("📋 Ver detalle diario completo"):
    df_show = df.copy()
    df_show["date"] = df_show["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(
        df_show.sort_values("date", ascending=False).rename(columns={
            "date": "Fecha", "crew": "Cuadrilla", "work_hours": "Horas",
            "pois_investigated": "POIs", "leaks": "Fugas", "suspected": "Sospechosas",
            "quiet": "Sin fuga", "unverifiable": "No verificable", "pipe_length_km": "KM",
        })[["Fecha", "Cuadrilla", "Horas", "POIs", "Fugas", "Sospechosas", "Sin fuga", "No verificable", "KM"]],
        use_container_width=True, hide_index=True,
    )
