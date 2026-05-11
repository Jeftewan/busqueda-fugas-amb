import streamlit as st
import sys, os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models import (
    get_kpis, get_distribucion_por_prioridad, get_distribucion_por_alerta,
    get_distribucion_por_cuadrilla, get_tendencia_mensual, get_top_criticas,
    get_connection,
)
from src.ui import (
    inject_global_css, kpi_card, render_sidebar_header,
    empty_state, section_header, backlog_card, COLOR,
)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
inject_global_css()

with st.sidebar:
    render_sidebar_header(active_page="dashboard")

# ───── HEADER ────────────────────────────────────────────────────────────
col_t, col_b = st.columns([6, 2])
with col_t:
    st.markdown("# 📊 Dashboard General")
    st.caption("Visión global del contrato de búsqueda de fugas")
with col_b:
    st.markdown("<div style='padding-top:18px'>", unsafe_allow_html=True)
    descargar_pdf = st.button("📄 Descargar reporte", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

kpis = get_kpis()

# ───── ESTADO VACÍO ──────────────────────────────────────────────────────
if kpis["total_pois"] == 0:
    empty_state(
        icon="📊",
        title="Sin datos para mostrar",
        message="Para ver el dashboard, primero carga el Excel del día con los POIs y fugas detectadas.",
        cta_label="📥 Cargar Excel ahora",
        cta_page="pages/5_Cargar_Excel.py",
    )
    st.stop()

st.caption(f"💼 Total de POIs investigados: **{kpis['total_pois']}**")

# ───── KPIS EN GRID 2x3 ─────────────────────────────────────────────────
section_header("Indicadores principales")

# Datos adicionales para KPIs avanzados
conn = get_connection()
criticas = conn.execute(
    "SELECT COUNT(*) FROM leaks WHERE repaired!='Yes' AND alerta_antiguedad='critica'"
).fetchone()[0]
ot_generadas = conn.execute(
    "SELECT COUNT(*) FROM leaks WHERE ot_estado='Generada' AND repaired!='Yes'"
).fetchone()[0]
conn.close()

# Fila 1
r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    kpi_card("Fugas totales", kpis["total_leaks"], icon="💧", color="primary")
with r1c2:
    kpi_card(
        "Pendientes", kpis["pendientes"],
        delta=f"{round(kpis['pendientes']/kpis['total_leaks']*100,1)}% del total",
        color="danger" if kpis["pendientes"] > kpis["reparadas"] else "warning",
        icon="🔴",
    )
with r1c3:
    kpi_card(
        "Reparadas", kpis["reparadas"],
        delta=f"{kpis['pct_reparacion']}% de avance",
        color="success", icon="✅",
    )

# Fila 2
r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    kpi_card(
        "Días promedio pendiente", kpis["avg_dias_pendiente"],
        delta="entre fugas no reparadas",
        color="warning", icon="⏱️",
    )
with r2c2:
    kpi_card(
        "Críticas urgentes", criticas,
        delta="alerta = crítica + pendientes",
        color="danger" if criticas > 0 else "success", icon="🚨",
    )
with r2c3:
    kpi_card(
        "OTs en curso", ot_generadas,
        delta="generadas, sin finalizar",
        color="primary", icon="📋",
    )

st.markdown("<br>", unsafe_allow_html=True)

# ───── BACKLOG CARD ──────────────────────────────────────────────────────
vel = kpis["reparadas_30d"] / 30 * 7  # fugas/semana
backlog_card(vel, kpis["pendientes"], kpis["reparadas"], kpis["total_leaks"])

with st.expander("ℹ️ ¿Cómo se calcula el backlog?"):
    st.markdown(
        f"""
        - **Velocidad actual:** se calcula como el número de fugas reparadas en los últimos 30 días dividido entre 30, multiplicado por 7 → **{vel:.2f} fugas/semana**.
        - **Backlog:** fugas pendientes / velocidad semanal.
        - Si no ha habido reparaciones en 30 días, no es posible estimar.
        """
    )

st.markdown("<br>", unsafe_allow_html=True)

# ───── PLOTLY THEME COMÚN ───────────────────────────────────────────────
def style_fig(fig, title=None, subtitle=None):
    fig.update_layout(
        font=dict(family="Inter, sans-serif", size=13, color=COLOR["text"]),
        margin=dict(t=60 if title else 30, b=30, l=20, r=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hoverlabel=dict(font_size=12, font_family="Inter, sans-serif"),
    )
    if title:
        fig.update_layout(title=dict(
            text=f"<b>{title}</b>" + (f"<br><span style='font-size:11px;color:{COLOR['text_2']}'>{subtitle}</span>" if subtitle else ""),
            x=0.02, y=0.96, font=dict(size=15),
        ))
    return fig

# ───── GRÁFICOS FILA 1 ──────────────────────────────────────────────────
section_header("Distribución y estado")
col_a, col_b = st.columns(2)

with col_a:
    df_prio = get_distribucion_por_prioridad()
    if not df_prio.empty:
        # Calcular dato más relevante
        df_prio_filt = df_prio.dropna(subset=["prioridad"])
        if not df_prio_filt.empty:
            top = df_prio_filt.sort_values("total", ascending=False).iloc[0]
            pct_top = round(top["total"] / df_prio_filt["total"].sum() * 100, 0)
            subt = f"El {pct_top:.0f}% de las fugas son prioridad {top['prioridad']}"
        else:
            subt = ""
        color_map = {"ALTA": COLOR["danger"], "MEDIA": COLOR["warning"],
                     "BAJA": COLOR["success"], None: COLOR["neutral"]}
        fig = px.pie(df_prio, values="total", names="prioridad",
                     color="prioridad", color_discrete_map=color_map, hole=0.55)
        fig.update_traces(textposition="outside", textinfo="percent+label",
                          marker=dict(line=dict(color="white", width=2)))
        fig = style_fig(fig, title="¿Cómo se distribuye la urgencia?", subtitle=subt)
        fig.update_layout(showlegend=False, height=340)
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    df_alerta = get_distribucion_por_alerta()
    if not df_alerta.empty:
        labels_map = {"normal": "Normal", "atencion": "Atención",
                      "urgente": "Urgente", "critica": "Crítica"}
        color_map_a = {
            "Normal": COLOR["success"], "Atención": COLOR["amber"],
            "Urgente": COLOR["warning"], "Crítica": COLOR["danger"],
        }
        df_alerta["alerta_label"] = df_alerta["alerta"].map(labels_map).fillna("Sin clasificar")
        orden = ["Crítica", "Urgente", "Atención", "Normal", "Sin clasificar"]
        df_alerta["alerta_label"] = pd.Categorical(df_alerta["alerta_label"], categories=orden, ordered=True)
        df_alerta = df_alerta.sort_values("alerta_label")

        criticas_total = int(df_alerta[df_alerta["alerta_label"] == "Crítica"]["total"].sum())
        subt = f"Hay {criticas_total} fugas en estado crítico" if criticas_total > 0 else "Ninguna fuga en estado crítico"

        fig2 = px.bar(df_alerta, x="total", y="alerta_label", orientation="h",
                      color="alerta_label", color_discrete_map=color_map_a, text="total")
        fig2.update_traces(textposition="outside", marker=dict(line=dict(width=0)))
        fig2 = style_fig(fig2, title="¿Cuán urgentes son las pendientes?", subtitle=subt)
        fig2.update_layout(showlegend=False, height=340,
                           xaxis_title=None, yaxis_title=None,
                           xaxis=dict(showgrid=True, gridcolor="#F0F4F8"))
        st.plotly_chart(fig2, use_container_width=True)

# ───── GRÁFICOS FILA 2 ──────────────────────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    df_tend = get_tendencia_mensual()
    if not df_tend.empty:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df_tend["mes"], y=df_tend["detectadas"],
            mode="lines+markers", name="Detectadas",
            line=dict(color=COLOR["primary"], width=3),
            marker=dict(size=9), fill="tozeroy", fillcolor="rgba(11,110,153,0.08)"))
        fig3.add_trace(go.Scatter(
            x=df_tend["mes"], y=df_tend["reparadas"],
            mode="lines+markers", name="Reparadas",
            line=dict(color=COLOR["success"], width=3),
            marker=dict(size=9)))
        ult = df_tend.iloc[-1]
        subt = f"Último mes ({ult['mes']}): {int(ult['detectadas'])} detectadas / {int(ult['reparadas'])} reparadas"
        fig3 = style_fig(fig3, title="¿Cómo evoluciona el contrato?", subtitle=subt)
        fig3.update_layout(
            height=340, xaxis_title=None, yaxis_title="Fugas",
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#F0F4F8"))
        st.plotly_chart(fig3, use_container_width=True)

with col_d:
    df_crew = get_distribucion_por_cuadrilla()
    if not df_crew.empty:
        df_crew = df_crew.sort_values("fugas", ascending=False)
        top_crew = df_crew.iloc[0]
        subt = f"{top_crew['cuadrilla']} ha detectado más fugas: {int(top_crew['fugas'])}"
        fig4 = px.bar(df_crew, x="cuadrilla", y="fugas",
                      color="cuadrilla",
                      color_discrete_sequence=[COLOR["primary"], COLOR["accent"], COLOR["primary_lt"]],
                      text="fugas")
        fig4.update_traces(textposition="outside", marker=dict(line=dict(width=0)))
        fig4 = style_fig(fig4, title="¿Quién está detectando más?", subtitle=subt)
        fig4.update_layout(showlegend=False, height=340,
                           xaxis_title=None, yaxis_title="Fugas detectadas",
                           yaxis=dict(showgrid=True, gridcolor="#F0F4F8"))
        st.plotly_chart(fig4, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ───── TOP 10 CRÍTICAS ──────────────────────────────────────────────────
section_header("🚨 Top 10 fugas críticas pendientes",
               subtitle="Ordenadas por score y antigüedad. Click en una fila para enfocarla.")

df_top = get_top_criticas(10)
if not df_top.empty:
    ALERTA_EMOJI = {"normal": "🟢", "atencion": "🟡", "urgente": "🟠", "critica": "🔴"}
    PRIO_EMOJI = {"ALTA": "🔴", "MEDIA": "🟡", "BAJA": "🟢"}

    df_show = df_top.copy()
    df_show["Alerta"] = df_show["alerta_antiguedad"].map(lambda x: f"{ALERTA_EMOJI.get(x,'⚪')} {x or '—'}")
    df_show["Prioridad"] = df_show["prioridad_final"].map(lambda x: f"{PRIO_EMOJI.get(x,'⚪')} {x or '—'}")
    df_show["Comentario"] = df_show["comments_original"].fillna("").str.slice(0, 80)

    table = df_show[["leak_id", "address", "leak_type", "dias_sin_reparar",
                     "Prioridad", "Alerta", "score_prioridad", "ot_estado", "Comentario"]].rename(columns={
        "leak_id": "Leak ID", "address": "Dirección", "leak_type": "Tipo",
        "dias_sin_reparar": "Días", "score_prioridad": "Score", "ot_estado": "Estado OT",
    })

    # Selección para acciones rápidas
    sel = st.dataframe(
        table,
        use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
        key="top10_table",
    )

    sel_rows = sel.selection.rows if hasattr(sel, "selection") else []
    if sel_rows:
        sel_leak_id = int(df_show.iloc[sel_rows[0]]["leak_id"])
        col_s1, col_s2, col_s3 = st.columns([2, 2, 4])
        with col_s1:
            if st.button(f"🔍 Ver detalle de Leak #{sel_leak_id}", use_container_width=True, type="primary"):
                st.session_state["ver_detalle"] = sel_leak_id
                st.switch_page("pages/2_Fugas.py")
        with col_s2:
            if st.button("📧 Pre-cargar para correo OT", use_container_width=True):
                st.session_state["leak_ids_correo"] = [sel_leak_id]
                st.session_state["accion_correo"] = "OT"
                st.switch_page("pages/6_Correos.py")

    # Exportar top 10
    import io
    buf = io.BytesIO()
    df_top.to_excel(buf, index=False)
    st.download_button(
        "📥 Exportar Top 10 a Excel",
        data=buf.getvalue(),
        file_name="top10_fugas_criticas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    empty_state("✅", "Sin fugas críticas", "Excelente, no hay fugas pendientes en estado crítico.")

# ───── REPORTE EJECUTIVO ────────────────────────────────────────────────
if descargar_pdf:
    with st.spinner("Generando reporte ejecutivo..."):
        try:
            from src.reports import generar_reporte_ejecutivo
            pdf_bytes = generar_reporte_ejecutivo(kpis, df_top)
            st.download_button(
                "⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"reporte_ejecutivo_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                type="primary",
            )
            st.toast("✅ Reporte generado", icon="📄")
        except Exception as e:
            st.error(f"❌ Error generando PDF: {e}")
