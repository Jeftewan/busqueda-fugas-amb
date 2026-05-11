"""
src/ui.py — Helpers de UI reutilizables.

Centraliza la identidad visual (colores, tipografía, componentes) para que
todas las páginas se vean consistentes sin duplicar HTML/CSS.
"""
import streamlit as st
from datetime import datetime

# ───────────────────────────── PALETA ─────────────────────────────
COLOR = {
    "primary":      "#0B6E99",
    "primary_lt":   "#4FB8E6",
    "accent":       "#00A896",
    "bg":           "#F7F9FB",
    "surface":      "#FFFFFF",
    "text":         "#0F2A3E",
    "text_2":       "#5C7184",
    "border":       "#E1E8EE",

    "danger":       "#D7263D",   # ALTA / crítica
    "warning":      "#F46036",   # MEDIA / urgente
    "amber":        "#F7B801",   # atención
    "success":      "#2EB872",   # BAJA / normal
    "neutral":      "#A0AEC0",
}

# Mapeos semánticos
PRIO_COLOR = {
    "ALTA":  COLOR["danger"],
    "MEDIA": COLOR["warning"],
    "BAJA":  COLOR["success"],
    None:    COLOR["neutral"],
}

ALERTA_COLOR = {
    "critica":  COLOR["danger"],
    "urgente":  COLOR["warning"],
    "atencion": COLOR["amber"],
    "normal":   COLOR["success"],
    None:       COLOR["neutral"],
}

ALERTA_LABEL = {
    "critica":  "Crítica",
    "urgente":  "Urgente",
    "atencion": "Atención",
    "normal":   "Normal",
}

OT_COLOR = {
    "Pendiente por generar": COLOR["text_2"],
    "Generada":              COLOR["primary"],
    "Finalizada":            COLOR["success"],
}

# ───────────────────────────── CSS GLOBAL ─────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, .block-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Quitar el header de Streamlit por defecto, dejar más limpio */
header[data-testid="stHeader"] {
    background: transparent;
}

/* Padding del bloque principal más razonable */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* Títulos */
h1 { font-weight: 700 !important; color: #0F2A3E; letter-spacing: -0.02em; }
h2 { font-weight: 600 !important; color: #0F2A3E; }
h3 { font-weight: 600 !important; color: #0F2A3E; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #E1E8EE;
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem;
}

/* Botones primarios */
.stButton > button[kind="primary"] {
    background: #0B6E99;
    border: none;
    font-weight: 600;
    border-radius: 8px;
    transition: all 0.15s ease;
    box-shadow: 0 1px 2px rgba(11, 110, 153, 0.15);
}
.stButton > button[kind="primary"]:hover {
    background: #0A5F87;
    box-shadow: 0 4px 12px rgba(11, 110, 153, 0.25);
    transform: translateY(-1px);
}

.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    border: 1px solid #E1E8EE;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    border-color: #0B6E99;
    color: #0B6E99;
}

/* Métricas */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E1E8EE;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(15, 42, 62, 0.04);
}
[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
    color: #5C7184 !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    color: #0F2A3E !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid #E1E8EE;
}
.stTabs [data-baseweb="tab"] {
    height: 42px;
    padding: 0 16px;
    border-radius: 8px 8px 0 0;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    color: #0B6E99 !important;
    background: rgba(11, 110, 153, 0.06) !important;
}

/* DataFrames */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #E1E8EE;
}

/* Expanders */
.streamlit-expanderHeader {
    background: #FFFFFF;
    border-radius: 8px;
    border: 1px solid #E1E8EE;
    font-weight: 500;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stMultiSelect > div > div {
    border-radius: 8px !important;
    border-color: #E1E8EE !important;
}

/* Alerts (info, success, warning, error) */
[data-testid="stAlert"] {
    border-radius: 10px;
    border: none;
}

/* Estilos custom para componentes propios */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E1E8EE;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(15, 42, 62, 0.04);
    transition: all 0.2s ease;
    height: 100%;
}
.kpi-card:hover {
    border-color: #0B6E99;
    box-shadow: 0 4px 12px rgba(11, 110, 153, 0.08);
}
.kpi-card .kpi-label {
    font-size: 0.85rem;
    color: #5C7184;
    font-weight: 500;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.kpi-card .kpi-value {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.1;
    color: #0F2A3E;
}
.kpi-card .kpi-value.danger  { color: #D7263D; }
.kpi-card .kpi-value.warning { color: #F46036; }
.kpi-card .kpi-value.success { color: #2EB872; }
.kpi-card .kpi-value.primary { color: #0B6E99; }
.kpi-card .kpi-delta {
    font-size: 0.8rem;
    color: #5C7184;
    margin-top: 6px;
}

/* Pills / badges */
.pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1.4;
    white-space: nowrap;
}
.pill-danger  { background: rgba(215, 38, 61, 0.10);  color: #D7263D; }
.pill-warning { background: rgba(244, 96, 54, 0.10);  color: #F46036; }
.pill-amber   { background: rgba(247, 184, 1, 0.15);  color: #B58400; }
.pill-success { background: rgba(46, 184, 114, 0.10); color: #1F8E55; }
.pill-primary { background: rgba(11, 110, 153, 0.10); color: #0B6E99; }
.pill-neutral { background: rgba(160, 174, 192, 0.15); color: #5C7184; }

/* Section header */
.section-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin: 8px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #E1E8EE;
}
.section-header .title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0F2A3E;
}
.section-header .subtitle {
    font-size: 0.85rem;
    color: #5C7184;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 60px 24px;
    background: #FFFFFF;
    border: 1px dashed #E1E8EE;
    border-radius: 16px;
    margin: 24px 0;
}
.empty-state .empty-icon {
    font-size: 3.5rem;
    margin-bottom: 12px;
    opacity: 0.7;
}
.empty-state .empty-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: #0F2A3E;
    margin-bottom: 6px;
}
.empty-state .empty-message {
    color: #5C7184;
    margin-bottom: 20px;
    max-width: 420px;
    margin-left: auto;
    margin-right: auto;
}

/* Sidebar header custom */
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 16px 0;
    border-bottom: 1px solid #E1E8EE;
    margin-bottom: 16px;
}
.sidebar-brand .brand-icon {
    font-size: 1.6rem;
    line-height: 1;
}
.sidebar-brand .brand-text {
    font-weight: 700;
    color: #0F2A3E;
    line-height: 1.2;
}
.sidebar-brand .brand-sub {
    font-size: 0.75rem;
    color: #5C7184;
    font-weight: 400;
}

.sidebar-meta {
    font-size: 0.75rem;
    color: #5C7184;
    padding: 8px 0;
    margin-top: 4px;
    border-top: 1px solid #E1E8EE;
}
.sidebar-meta .meta-label { color: #5C7184; }
.sidebar-meta .meta-value { color: #0F2A3E; font-weight: 500; }

/* Detail header (página de Fugas detalle) */
.detail-header {
    background: linear-gradient(135deg, #FFFFFF 0%, #F7F9FB 100%);
    border: 1px solid #E1E8EE;
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 18px;
    box-shadow: 0 2px 6px rgba(15, 42, 62, 0.04);
}
.detail-header .leak-num {
    font-size: 0.78rem;
    color: #5C7184;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.detail-header .leak-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #0F2A3E;
    margin: 4px 0 4px 0;
}
.detail-header .leak-addr {
    color: #5C7184;
    font-size: 0.95rem;
    margin-bottom: 14px;
}
.detail-header .badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
}
.detail-header .meta-row {
    color: #5C7184;
    font-size: 0.85rem;
    border-top: 1px solid #E1E8EE;
    padding-top: 10px;
}

/* Quick action cards (Home) */
.quick-action {
    background: #FFFFFF;
    border: 1px solid #E1E8EE;
    border-radius: 12px;
    padding: 18px;
    text-align: left;
    cursor: pointer;
    transition: all 0.15s ease;
    height: 100%;
}
.quick-action:hover {
    border-color: #0B6E99;
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(11, 110, 153, 0.08);
}
.quick-action .qa-icon { font-size: 1.6rem; margin-bottom: 8px; }
.quick-action .qa-title { font-weight: 600; color: #0F2A3E; margin-bottom: 4px; }
.quick-action .qa-desc { font-size: 0.85rem; color: #5C7184; }

/* Sticky action bar (Fugas con selección) */
.sticky-actionbar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #FFFFFF;
    border: 1px solid #0B6E99;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 4px 14px rgba(11, 110, 153, 0.12);
}

/* Backlog card */
.backlog-card {
    background: linear-gradient(135deg, #FFFFFF 0%, #F0F7FA 100%);
    border: 1px solid #4FB8E6;
    border-radius: 14px;
    padding: 20px 24px;
    margin: 10px 0 20px 0;
}
.backlog-card .bl-title {
    font-size: 0.85rem;
    color: #0B6E99;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}
.backlog-card .bl-eta {
    font-size: 1.4rem;
    font-weight: 700;
    color: #0F2A3E;
}
.backlog-card .bl-detail {
    font-size: 0.9rem;
    color: #5C7184;
    margin-top: 4px;
}
.backlog-card .bl-bar {
    height: 8px;
    background: #E1E8EE;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 12px;
}
.backlog-card .bl-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #00A896, #0B6E99);
    border-radius: 999px;
    transition: width 0.4s ease;
}
.backlog-card .bl-bar-label {
    font-size: 0.75rem;
    color: #5C7184;
    margin-top: 6px;
    display: flex;
    justify-content: space-between;
}

/* Crew cards (Cuadrillas) */
.crew-card {
    background: #FFFFFF;
    border: 1px solid #E1E8EE;
    border-radius: 14px;
    padding: 22px 24px;
    height: 100%;
}
.crew-card .crew-name {
    font-size: 1.2rem;
    font-weight: 700;
    color: #0B6E99;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.crew-card .crew-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 10px 0;
}
.crew-card .crew-label { color: #5C7184; font-size: 0.88rem; }
.crew-card .crew-val   { color: #0F2A3E; font-weight: 600; }
.crew-card .crew-bar {
    height: 6px;
    background: #E1E8EE;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 4px;
}
.crew-card .crew-bar-fill {
    height: 100%;
    background: #0B6E99;
    border-radius: 999px;
}

/* Map legend */
.map-legend {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #E1E8EE;
    border-radius: 10px;
    padding: 12px 14px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
}
.map-legend .legend-title {
    font-weight: 700;
    color: #0F2A3E;
    margin-bottom: 8px;
    border-bottom: 1px solid #E1E8EE;
    padding-bottom: 6px;
}
.map-legend .legend-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 4px 0;
    color: #0F2A3E;
}
.map-legend .legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
}
</style>
"""


def inject_global_css():
    """Inyecta el CSS global. Llamar al inicio de cada página después de set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ───────────────────────────── COMPONENTES ─────────────────────────────

def kpi_card(label: str, value, delta: str = None, color: str = "primary", icon: str = ""):
    """Renderiza una card de KPI estilizada (no usa st.metric)."""
    color_class = color if color in ("primary", "danger", "warning", "success") else "primary"
    icon_html = f'<span style="font-size:1rem">{icon}</span> ' if icon else ""
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ''
    html = f"""
    <div class="kpi-card">
        <div class="kpi-label">{icon_html}{label}</div>
        <div class="kpi-value {color_class}">{value}</div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def priority_badge(prioridad: str) -> str:
    """Devuelve HTML de pill de prioridad. Usar dentro de st.markdown unsafe_allow_html=True."""
    if not prioridad:
        return '<span class="pill pill-neutral">— Sin clasificar</span>'
    klass = {"ALTA": "pill-danger", "MEDIA": "pill-warning", "BAJA": "pill-success"}.get(prioridad, "pill-neutral")
    return f'<span class="pill {klass}">● {prioridad}</span>'


def alert_pill(alerta: str) -> str:
    """Pill de alerta de antigüedad."""
    if not alerta:
        return ''
    label = ALERTA_LABEL.get(alerta, alerta)
    klass = {
        "critica": "pill-danger",
        "urgente": "pill-warning",
        "atencion": "pill-amber",
        "normal": "pill-success",
    }.get(alerta, "pill-neutral")
    return f'<span class="pill {klass}">⏱ {label}</span>'


def ot_pill(ot_estado: str) -> str:
    """Pill del estado de OT."""
    if not ot_estado:
        return ''
    klass = {
        "Pendiente por generar": "pill-neutral",
        "Generada": "pill-primary",
        "Finalizada": "pill-success",
    }.get(ot_estado, "pill-neutral")
    icon = {"Pendiente por generar": "⏳", "Generada": "📋", "Finalizada": "✅"}.get(ot_estado, "•")
    return f'<span class="pill {klass}">{icon} {ot_estado}</span>'


def empty_state(icon: str, title: str, message: str, cta_label: str = None, cta_page: str = None):
    """
    Muestra un estado vacío amigable con CTA opcional.
    Si cta_label y cta_page se dan, renderiza un botón que navega.
    """
    html = f"""
    <div class="empty-state">
        <div class="empty-icon">{icon}</div>
        <div class="empty-title">{title}</div>
        <div class="empty-message">{message}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    if cta_label and cta_page:
        col_l, col_c, col_r = st.columns([2, 2, 2])
        with col_c:
            if st.button(cta_label, type="primary", use_container_width=True, key=f"cta_{title[:10]}"):
                st.switch_page(cta_page)


def section_header(title: str, subtitle: str = None, icon: str = None):
    """Encabezado de sección consistente."""
    icon_html = f"{icon} " if icon else ""
    sub_html = f'<span class="subtitle">{subtitle}</span>' if subtitle else ''
    html = f"""
    <div class="section-header">
        <span class="title">{icon_html}{title}</span>
        {sub_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_sidebar_header(active_page: str = None):
    """
    Renderiza el header consistente del sidebar: brand + búsqueda global + última carga.
    Llamar al inicio del bloque `with st.sidebar:` en cada página.
    Devuelve el texto buscado (si lo hay) para que la página lo procese.
    """
    from src.models import get_import_log

    st.markdown(
        """
        <div class="sidebar-brand">
            <span class="brand-icon">💧</span>
            <div>
                <div class="brand-text">Seguimiento de Fugas</div>
                <div class="brand-sub">Acueducto · v1.0</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    busqueda = st.text_input(
        "🔍 Búsqueda global",
        placeholder="ID, Leak ID o dirección...",
        key=f"search_{active_page or 'global'}",
        label_visibility="collapsed",
    )
    if busqueda:
        st.session_state["filtro_global"] = busqueda
        # Solo redirigir si NO estamos ya en la página de fugas
        if active_page != "fugas":
            st.switch_page("pages/2_Fugas.py")

    # Última carga
    try:
        log_df = get_import_log()
        if not log_df.empty:
            ultima = log_df.iloc[0]["fecha_carga"]
            try:
                dt = datetime.fromisoformat(ultima)
                rel = _format_relative(dt)
                fecha_str = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                rel = ultima
                fecha_str = ultima
            st.markdown(
                f"""
                <div class="sidebar-meta">
                    <div><span class="meta-label">📥 Última carga:</span></div>
                    <div><span class="meta-value">{fecha_str}</span></div>
                    <div style="font-size:0.7rem;margin-top:2px;color:#A0AEC0">({rel})</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="sidebar-meta">
                    <span class="meta-label">📥 Sin datos cargados</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    except Exception:
        pass


def _format_relative(dt: datetime) -> str:
    """Devuelve 'hace X' a partir de un datetime."""
    delta = datetime.now() - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "hace unos segundos"
    if seconds < 3600:
        return f"hace {seconds // 60} min"
    if seconds < 86400:
        return f"hace {seconds // 3600} h"
    days = seconds // 86400
    if days < 7:
        return f"hace {days} días"
    return dt.strftime("%d/%m/%Y")


def render_action_card(icon: str, title: str, description: str, button_label: str,
                       page_path: str, button_type: str = "secondary", key: str = None):
    """
    Card visual con un botón de acción debajo. Útil para el Home y para CTAs grandes.
    """
    st.markdown(
        f"""
        <div class="quick-action">
            <div class="qa-icon">{icon}</div>
            <div class="qa-title">{title}</div>
            <div class="qa-desc">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(button_label, key=key or f"act_{title[:10]}", use_container_width=True, type=button_type):
        st.switch_page(page_path)


def detail_header(leak_id: int, address: str, prioridad: str, alerta: str,
                  ot_estado: str, fecha_det: str = None, crew: str = None,
                  leak_type: str = None, dias: int = None):
    """Header del detalle de una fuga con badges visuales."""
    badges = []
    if prioridad:
        badges.append(priority_badge(prioridad))
    if alerta:
        days_txt = f" · {dias}d" if dias is not None else ""
        klass = {
            "critica": "pill-danger",
            "urgente": "pill-warning",
            "atencion": "pill-amber",
            "normal": "pill-success",
        }.get(alerta, "pill-neutral")
        label = ALERTA_LABEL.get(alerta, alerta)
        badges.append(f'<span class="pill {klass}">⏱ {label}{days_txt}</span>')
    if ot_estado:
        badges.append(ot_pill(ot_estado))

    badge_html = "".join(badges) if badges else "—"

    meta_parts = []
    if fecha_det:
        meta_parts.append(f"📅 Detectada: {fecha_det}")
    if crew:
        meta_parts.append(f"👷 {crew}")
    if leak_type:
        meta_parts.append(f"🔧 {leak_type}")
    meta_html = " · ".join(meta_parts) if meta_parts else ""

    html = f"""
    <div class="detail-header">
        <div class="leak-num">LEAK</div>
        <div class="leak-title">#{leak_id}</div>
        <div class="leak-addr">📍 {address or 'Dirección no disponible'}</div>
        <div class="badge-row">{badge_html}</div>
        <div class="meta-row">{meta_html}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def backlog_card(velocidad_semana: float, pendientes: int, reparadas: int, total: int):
    """Card visual del estimador de backlog con barra de progreso."""
    if velocidad_semana > 0:
        semanas = round(pendientes / velocidad_semana, 1)
        eta = f"~{semanas} semanas"
        detalle = f"Al ritmo actual de {velocidad_semana:.1f} fugas/semana, el backlog se cierra en aproximadamente {semanas} semanas."
    else:
        eta = "Sin estimación"
        detalle = "No hay reparaciones recientes suficientes para estimar el ritmo de cierre del backlog."

    pct = round(reparadas / total * 100, 1) if total else 0

    html = f"""
    <div class="backlog-card">
        <div class="bl-title">📅 Estimador de backlog</div>
        <div class="bl-eta">{eta}</div>
        <div class="bl-detail">{detalle}</div>
        <div class="bl-bar">
            <div class="bl-bar-fill" style="width: {pct}%"></div>
        </div>
        <div class="bl-bar-label">
            <span>{reparadas} reparadas</span>
            <span><strong>{pct}%</strong></span>
            <span>{total} totales</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def crew_card(name: str, metrics: dict, max_values: dict):
    """
    Card de cuadrilla con métricas + barras comparativas (vs el máximo entre cuadrillas).

    metrics y max_values son dicts con las mismas keys: ej.
        metrics    = {"POIs": 116, "Fugas": 78, "Tasa det.": "67%", "KM/día": 2.3}
        max_values = {"POIs": 180, "Fugas": 136, "Tasa det.": 76, "KM/día": 3.1}
    """
    rows_html = ""
    for label, val in metrics.items():
        max_v = max_values.get(label)
        # extraer número para barra
        num = val
        if isinstance(val, str):
            try:
                num = float(val.replace("%", "").replace(",", ""))
            except ValueError:
                num = 0
        try:
            pct = (float(num) / float(max_v) * 100) if max_v else 0
        except (ValueError, TypeError, ZeroDivisionError):
            pct = 0
        pct = max(0, min(100, pct))
        rows_html += f"""
        <div>
            <div class="crew-row">
                <span class="crew-label">{label}</span>
                <span class="crew-val">{val}</span>
            </div>
            <div class="crew-bar"><div class="crew-bar-fill" style="width:{pct:.0f}%"></div></div>
        </div>
        """
    html = f"""
    <div class="crew-card">
        <div class="crew-name">👷 {name}</div>
        {rows_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def sticky_action_bar(text: str):
    """Renderiza el contenedor abierto de una sticky action bar. Usar como context."""
    st.markdown(f'<div class="sticky-actionbar"><strong>{text}</strong></div>', unsafe_allow_html=True)
