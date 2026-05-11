import streamlit as st
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from src.db import get_connection, init_db
from src.ui import (
    inject_global_css, kpi_card, render_sidebar_header,
    empty_state, section_header,
)

# ───── CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Seguimiento de Fugas — Acueducto",
    page_icon="assets/favicon.png" if os.path.exists("assets/favicon.png") else "💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
init_db()

# ───── SIDEBAR ──────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_header(active_page="home")


# ───── KPIs DEL DÍA ──────────────────────────────────────────────────────
def get_home_kpis():
    """KPIs específicos para el home, accionables."""
    conn = get_connection()
    out = {}

    out["total_leaks"] = conn.execute("SELECT COUNT(*) FROM leaks").fetchone()[0]
    if out["total_leaks"] == 0:
        conn.close()
        return out

    row = conn.execute(
        """SELECT COUNT(*), AVG(dias_sin_reparar)
           FROM leaks
           WHERE repaired != 'Yes' AND alerta_antiguedad = 'critica'"""
    ).fetchone()
    out["criticas"] = row[0] or 0
    out["criticas_dias_avg"] = round(row[1] or 0, 0)

    out["ot_pendientes"] = conn.execute(
        """SELECT COUNT(*) FROM leaks
           WHERE repaired != 'Yes'
             AND (ot_estado IS NULL OR ot_estado = 'Pendiente por generar')"""
    ).fetchone()[0]

    out["reparadas_semana"] = conn.execute(
        """SELECT COUNT(*) FROM leaks
           WHERE repair_date_excel >= date('now', '-7 days')"""
    ).fetchone()[0]

    pendientes = conn.execute(
        "SELECT COUNT(*) FROM leaks WHERE repaired != 'Yes'"
    ).fetchone()[0]
    rep_30d = conn.execute(
        "SELECT COUNT(*) FROM leaks WHERE repair_date_excel >= date('now','-30 days')"
    ).fetchone()[0]
    vel_semana = rep_30d / 30 * 7
    if vel_semana > 0:
        out["backlog_semanas"] = round(pendientes / vel_semana, 0)
    else:
        out["backlog_semanas"] = None

    out["pendientes"] = pendientes
    conn.close()
    return out


kpis = get_home_kpis()

# ───── HEADER ────────────────────────────────────────────────────────────
col_t, col_d = st.columns([6, 2])
with col_t:
    st.markdown("# 💧 Seguimiento de Fugas")
    st.caption(f"Hub operativo · {datetime.now().strftime('%A %d de %B de %Y').capitalize()}")
with col_d:
    st.markdown("<div style='text-align:right;padding-top:18px'>", unsafe_allow_html=True)
    if kpis["total_leaks"] > 0 and st.button("📊 Dashboard completo", use_container_width=True):
        st.switch_page("pages/1_Dashboard.py")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ───── ESTADO SIN DATOS ──────────────────────────────────────────────────
if kpis["total_leaks"] == 0:
    empty_state(
        icon="💧",
        title="Bienvenido al Sistema de Seguimiento de Fugas",
        message=(
            "Aún no hay datos cargados. Para empezar, importa el archivo "
            "AMB_1.xlsx que el contratista actualiza diariamente."
        ),
        cta_label="📥 Cargar primer Excel",
        cta_page="pages/5_Cargar_Excel.py",
    )
    st.stop()

# ───── BANDA DE KPIs DEL DÍA ─────────────────────────────────────────────
section_header("Estado actual", subtitle="Lo que necesitas saber hoy")

c1, c2, c3, c4 = st.columns(4)
with c1:
    delta = f"{int(kpis['criticas_dias_avg'])} días promedio" if kpis["criticas"] > 0 else None
    kpi_card(
        "Fugas críticas pendientes", kpis["criticas"],
        delta=delta,
        color="danger" if kpis["criticas"] > 0 else "success",
        icon="🚨",
    )
with c2:
    kpi_card(
        "OTs por generar", kpis["ot_pendientes"],
        delta=f"{kpis['pendientes']} pendientes en total",
        color="warning" if kpis["ot_pendientes"] > 10 else "primary",
        icon="📋",
    )
with c3:
    kpi_card(
        "Reparadas esta semana", kpis["reparadas_semana"],
        delta="últimos 7 días",
        color="success" if kpis["reparadas_semana"] > 0 else "primary",
        icon="✅",
    )
with c4:
    if kpis["backlog_semanas"] is not None:
        kpi_card(
            "Backlog estimado", f"~{int(kpis['backlog_semanas'])} sem.",
            delta="al ritmo actual", color="primary", icon="📅",
        )
    else:
        kpi_card(
            "Backlog estimado", "—",
            delta="sin datos suficientes", color="primary", icon="📅",
        )

st.markdown("<br>", unsafe_allow_html=True)

# ───── ACCIONES RÁPIDAS ──────────────────────────────────────────────────
section_header("Acciones rápidas", subtitle="Atajos a las tareas más comunes")

a1, a2, a3, a4 = st.columns(4)

with a1:
    if st.button("🚨 Ver fugas críticas", use_container_width=True, type="primary"):
        st.session_state["preset_filtro"] = {
            "prioridad": ["ALTA"],
            "alerta": ["critica"],
            "solo_no_reparadas": True,
        }
        st.switch_page("pages/2_Fugas.py")
    st.caption("Filtra prioridad ALTA + alerta crítica.")

with a2:
    if st.button("📥 Cargar Excel del día", use_container_width=True):
        st.switch_page("pages/5_Cargar_Excel.py")
    st.caption("Importar AMB_1.xlsx actualizado.")

with a3:
    if st.button("📧 Enviar solicitud OT", use_container_width=True):
        st.switch_page("pages/6_Correos.py")
    st.caption("Generar correo y PDF para el contratista.")

with a4:
    if st.button("🗺️ Ver mapa", use_container_width=True):
        st.switch_page("pages/3_Mapa.py")
    st.caption("Ubicación geográfica de todas las fugas.")

st.markdown("<br>", unsafe_allow_html=True)

# ───── TIP DE ACTUALIZACIÓN ─────────────────────────────────────────────
try:
    conn = get_connection()
    last_load = conn.execute(
        "SELECT fecha_carga FROM import_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if last_load:
        try:
            last_dt = datetime.fromisoformat(last_load[0])
            horas = (datetime.now() - last_dt).total_seconds() / 3600
            if horas > 24:
                dias = int(horas / 24)
                st.warning(
                    f"⏰ El último archivo fue cargado hace **{dias} día(s)**. "
                    f"Considera actualizar para tener datos al día."
                )
        except Exception:
            pass
except Exception:
    pass

# ───── CONFIG SMTP CHECK ────────────────────────────────────────────────
try:
    from src.utils import load_config
    cfg = load_config()
    if not cfg.get("smtp", {}).get("user") or not cfg.get("destinatarios", {}).get("fijo"):
        col_w1, col_w2 = st.columns([5, 1])
        with col_w1:
            st.info(
                "⚙️ **Configuración pendiente:** para enviar correos al contratista "
                "configura las credenciales de Gmail y el destinatario fijo."
            )
        with col_w2:
            if st.button("Configurar", use_container_width=True):
                st.switch_page("pages/7_Configuracion.py")
except Exception:
    pass
