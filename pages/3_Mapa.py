import streamlit as st
import sys, os
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import pandas as pd
from branca.element import Template, MacroElement

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models import get_all_leaks, get_remaining_pois, get_leak_by_id
from src.geo import detectar_clusters
from src.ui import (
    inject_global_css, render_sidebar_header, empty_state, COLOR,
    priority_badge, alert_pill, ot_pill, kpi_card,
)

st.set_page_config(page_title="Mapa", page_icon="🗺️", layout="wide")
inject_global_css()

PRIO_COLOR = {"ALTA": "#D7263D", "MEDIA": "#F46036", "BAJA": "#2EB872", None: "#A0AEC0"}
ALERTA_LABEL = {"normal": "Normal", "atencion": "Atención", "urgente": "Urgente", "critica": "Crítica"}

# ───── SIDEBAR ──────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_header(active_page="mapa")

    st.markdown("### 🗺️ Visualización")
    capa_base = st.selectbox(
        "Capa base", ["🗺️ Calles", "🛰️ Satélite", "⚫ Oscuro"],
        help="Cambia el fondo del mapa.",
    )
    mostrar_clusters = st.toggle("Mostrar clusters geográficos", value=True)
    radio_cluster = st.slider("Radio de cluster (m)", 50, 500, 100, step=50,
                               disabled=not mostrar_clusters)
    mostrar_pendientes = st.toggle("Mostrar POIs por inspeccionar", value=False)

    st.markdown("### 🔍 Filtros")
    if st.button("🔄 Limpiar filtros", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k.startswith("mp_flt_"):
                del st.session_state[k]
        st.rerun()

    solo_pendientes = st.toggle("Solo no reparadas", value=True, key="mp_flt_norep")

    prioridades_sel = st.multiselect(
        "Prioridad", ["ALTA", "MEDIA", "BAJA"],
        default=["ALTA", "MEDIA", "BAJA"],
        format_func=lambda x: f"{'🔴' if x=='ALTA' else '🟡' if x=='MEDIA' else '🟢'} {x}",
        key="mp_flt_prio",
    )
    alertas_sel = st.multiselect(
        "Alerta", ["critica", "urgente", "atencion", "normal"],
        default=["critica", "urgente", "atencion", "normal"],
        format_func=lambda x: f"{'🔴' if x=='critica' else '🟠' if x=='urgente' else '🟡' if x=='atencion' else '🟢'} {ALERTA_LABEL[x]}",
        key="mp_flt_alerta",
    )

# ───── HEADER ────────────────────────────────────────────────────────────
st.markdown("# 🗺️ Mapa de Fugas")
st.caption("Distribución geográfica con clusters y POIs por inspeccionar")

# ───── CONSULTA ─────────────────────────────────────────────────────────
filtros = {"solo_no_reparadas": solo_pendientes}
if prioridades_sel:
    filtros["prioridad"] = prioridades_sel
if alertas_sel:
    filtros["alerta"] = alertas_sel

df = get_all_leaks(filtros)
df_geo = df.dropna(subset=["actual_x", "actual_y"])

if df_geo.empty:
    empty_state(
        "🗺️", "Sin fugas para mostrar",
        "No hay fugas con coordenadas que coincidan con los filtros. Prueba a relajar los criterios o cargar datos desde el Excel.",
        cta_label="📥 Cargar Excel",
        cta_page="pages/5_Cargar_Excel.py",
    )
    st.stop()

# ───── KPIs RÁPIDOS ─────────────────────────────────────────────────────
sin_coords = len(df) - len(df_geo)
n_critica = int((df_geo["alerta_antiguedad"] == "critica").sum())
k1, k2, k3, k4 = st.columns(4)
with k1: kpi_card("Fugas en mapa", len(df_geo), icon="📍", color="primary")
with k2: kpi_card("Sin coordenadas", sin_coords, icon="❓", color="primary")
with k3: kpi_card("Críticas visibles", n_critica, color="danger" if n_critica else "success", icon="🚨")
with k4:
    n_alta = int((df_geo["prioridad_final"] == "ALTA").sum())
    kpi_card("Prioridad ALTA", n_alta, color="danger" if n_alta else "success", icon="🔴")

st.markdown("<br>", unsafe_allow_html=True)

# ───── MAPA + PANEL LATERAL ─────────────────────────────────────────────
col_map, col_panel = st.columns([3, 1])

with col_map:
    # Centro
    lat_center = df_geo["actual_y"].mean()
    lon_center = df_geo["actual_x"].mean()

    tiles_map = {
        "🗺️ Calles": "CartoDB positron",
        "🛰️ Satélite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "⚫ Oscuro": "CartoDB dark_matter",
    }
    selected_tile = tiles_map.get(capa_base, "CartoDB positron")

    if capa_base == "🛰️ Satélite":
        m = folium.Map(location=[lat_center, lon_center], zoom_start=13,
                       tiles=selected_tile, attr="Esri")
    else:
        m = folium.Map(location=[lat_center, lon_center], zoom_start=13, tiles=selected_tile)

    # Markers de fugas
    for _, row in df_geo.iterrows():
        color = PRIO_COLOR.get(row.get("prioridad_final"), "#A0AEC0")
        popup_html = f"""
        <div style="font-family:Inter,sans-serif;font-size:13px;min-width:200px">
            <div style="font-weight:700;color:#0B6E99;margin-bottom:4px">Leak #{row['leak_id']}</div>
            <div style="color:#5C7184;font-size:12px;margin-bottom:8px">{(row.get('address') or '—')[:60]}</div>
            <table style="width:100%;font-size:12px">
                <tr><td style="color:#5C7184">Tipo:</td><td><b>{row.get('leak_type','—')}</b></td></tr>
                <tr><td style="color:#5C7184">Días:</td><td><b>{int(row.get('dias_sin_reparar') or 0)}</b></td></tr>
                <tr><td style="color:#5C7184">Prioridad:</td><td><b>{row.get('prioridad_final','—')}</b></td></tr>
                <tr><td style="color:#5C7184">Alerta:</td><td><b>{ALERTA_LABEL.get(row.get('alerta_antiguedad',''),'—')}</b></td></tr>
                <tr><td style="color:#5C7184">OT:</td><td><b>{row.get('ot_estado','—')}</b></td></tr>
            </table>
        </div>
        """
        folium.CircleMarker(
            location=[row["actual_y"], row["actual_x"]],
            radius=8, color=color, fill=True, fill_color=color, fill_opacity=0.85,
            weight=2,
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"#{row['leak_id']} · {row.get('prioridad_final','—')} · {int(row.get('dias_sin_reparar') or 0)}d",
        ).add_to(m)

    # Clusters
    if mostrar_clusters and len(df_geo) > 0:
        leaks_list = df_geo[["leak_id", "actual_x", "actual_y"]].to_dict("records")
        clusters = detectar_clusters(leaks_list, radio_cluster)
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            cluster_df = df_geo[df_geo["leak_id"].isin(cluster)]
            c_lat = cluster_df["actual_y"].mean()
            c_lon = cluster_df["actual_x"].mean()
            folium.Circle(
                location=[c_lat, c_lon], radius=radio_cluster,
                color="#7C3AED", fill=True, fill_opacity=0.10,
                weight=2, opacity=0.6,
                tooltip=f"🔵 Cluster de {len(cluster)} fugas",
            ).add_to(m)

    # POIs pendientes
    if mostrar_pendientes:
        df_rem = get_remaining_pois().dropna(subset=["x", "y"])
        for _, row in df_rem.iterrows():
            folium.CircleMarker(
                location=[row["y"], row["x"]],
                radius=4, color="#A0AEC0", fill=True, fill_color="#A0AEC0",
                fill_opacity=0.5, weight=1,
                tooltip=f"POI por inspeccionar: {(row.get('poi_address') or '')[:40]}",
            ).add_to(m)

    # Leyenda flotante (HTML/CSS via Branca MacroElement)
    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed; top: 80px; left: 60px; z-index:9999;
        background: rgba(255,255,255,0.96);
        border: 1px solid #E1E8EE; border-radius: 10px;
        padding: 12px 14px; font-family: 'Inter', sans-serif; font-size: 12.5px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.10); min-width: 170px;">
      <div style="font-weight:700;color:#0F2A3E;margin-bottom:8px;border-bottom:1px solid #E1E8EE;padding-bottom:6px">
        Leyenda
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin:4px 0">
        <span style="width:12px;height:12px;border-radius:50%;background:#D7263D;display:inline-block"></span>
        <span>Prioridad ALTA</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin:4px 0">
        <span style="width:12px;height:12px;border-radius:50%;background:#F46036;display:inline-block"></span>
        <span>Prioridad MEDIA</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin:4px 0">
        <span style="width:12px;height:12px;border-radius:50%;background:#2EB872;display:inline-block"></span>
        <span>Prioridad BAJA</span>
      </div>
      <hr style="margin:8px 0;border:none;border-top:1px solid #E1E8EE">
      <div style="display:flex;align-items:center;gap:8px;margin:4px 0">
        <span style="width:8px;height:8px;border-radius:50%;background:#A0AEC0;display:inline-block"></span>
        <span>POI por inspeccionar</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin:4px 0">
        <span style="width:14px;height:14px;border-radius:50%;background:rgba(124,58,237,0.2);border:2px solid #7C3AED;display:inline-block"></span>
        <span>Cluster (≥2 fugas)</span>
      </div>
    </div>
    {% endmacro %}
    """
    macro = MacroElement()
    macro._template = Template(legend_html)
    m.get_root().add_child(macro)

    output = st_folium(m, use_container_width=True, height=620, key="folium_main",
                        returned_objects=["last_object_clicked_tooltip"])

with col_panel:
    st.markdown("##### 📍 Detalle del marker")

    last_tooltip = output.get("last_object_clicked_tooltip") if output else None
    last_leak_id = None
    if last_tooltip and last_tooltip.startswith("#"):
        try:
            last_leak_id = int(last_tooltip.split("·")[0].strip().lstrip("#"))
        except Exception:
            last_leak_id = None

    if last_leak_id:
        leak = get_leak_by_id(last_leak_id)
        if leak:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #E1E8EE;border-radius:12px;padding:14px;">
                <div style="color:#5C7184;font-size:0.7rem;font-weight:600;text-transform:uppercase">LEAK</div>
                <div style="font-size:1.3rem;font-weight:700;color:#0B6E99;margin:2px 0 6px 0">#{last_leak_id}</div>
                <div style="font-size:0.85rem;color:#5C7184;margin-bottom:10px">📍 {leak.get('address') or '—'}</div>
                <div style="margin:8px 0">
                    {priority_badge(leak.get('prioridad_final'))}
                </div>
                <div style="margin:6px 0">
                    {alert_pill(leak.get('alerta_antiguedad'))}
                </div>
                <div style="margin:6px 0">
                    {ot_pill(leak.get('ot_estado'))}
                </div>
                <hr style="margin:10px 0;border:none;border-top:1px solid #E1E8EE">
                <div style="font-size:0.8rem;color:#5C7184">
                    <div>🔧 Tipo: <b style="color:#0F2A3E">{leak.get('leak_type','—')}</b></div>
                    <div>👷 Cuadrilla: <b style="color:#0F2A3E">{leak.get('crew','—')}</b></div>
                    <div>📅 Días: <b style="color:#0F2A3E">{leak.get('dias_sin_reparar', 0)}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔍 Ver detalle completo", use_container_width=True, type="primary", key="ver_det_map"):
                st.session_state["ver_detalle"] = last_leak_id
                st.switch_page("pages/2_Fugas.py")
    else:
        st.markdown("""
        <div style="background:#F7F9FB;border:1px dashed #E1E8EE;border-radius:12px;
                    padding:24px;text-align:center;color:#5C7184;font-size:0.9rem">
            <div style="font-size:2rem;margin-bottom:8px">👆</div>
            Haz click en un marker para ver su información aquí
        </div>
        """, unsafe_allow_html=True)
