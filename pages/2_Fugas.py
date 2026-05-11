import streamlit as st
import sys, os
import pandas as pd
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models import (
    get_all_leaks, get_leak_by_id, get_status_history,
    update_leak_internal,
)
from src.utils import load_config
from src.ui import (
    inject_global_css, render_sidebar_header, empty_state,
    section_header, detail_header, priority_badge, alert_pill, ot_pill,
    COLOR,
)

st.set_page_config(page_title="Fugas", page_icon="💧", layout="wide")
inject_global_css()

ALERTA_EMOJI = {"normal": "🟢", "atencion": "🟡", "urgente": "🟠", "critica": "🔴"}
PRIO_EMOJI = {"ALTA": "🔴", "MEDIA": "🟡", "BAJA": "🟢"}


# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR FILTROS
# ═══════════════════════════════════════════════════════════════════════
def render_filters():
    """Sidebar con filtros más usados arriba + 'Más filtros' en expander."""
    filtros = {}

    # Aplicar preset si viene del Home u otra página
    preset = st.session_state.pop("preset_filtro", None)

    with st.sidebar:
        render_sidebar_header(active_page="fugas")

        st.markdown("### 🔍 Filtros")

        # Filtro global venido del search del sidebar
        busqueda_global = st.session_state.pop("filtro_global", "")
        if busqueda_global:
            filtros["busqueda"] = busqueda_global
            st.info(f"🔍 Filtrando por: **{busqueda_global}**")

        # Botón limpiar
        if st.button("🔄 Limpiar todos los filtros", use_container_width=True):
            for k in list(st.session_state.keys()):
                if k.startswith(("flt_", "preset_filtro")):
                    del st.session_state[k]
            st.rerun()

        st.markdown("---")

        # Toggle principal
        default_no_rep = preset.get("solo_no_reparadas", True) if preset else True
        filtros["solo_no_reparadas"] = st.toggle(
            "Solo no reparadas", value=default_no_rep, key="flt_no_rep",
            help="Excluye las fugas que ya tienen Repaired=Yes en el Excel.",
        )

        # Datos para opciones
        df_all = get_all_leaks()
        if df_all.empty:
            return filtros

        # Filtros principales
        prioridades = sorted([p for p in df_all["prioridad_final"].dropna().unique()])
        default_prio = preset.get("prioridad", []) if preset else []
        sel_prio = st.multiselect(
            f"Prioridad ({len(prioridades)})", prioridades,
            default=default_prio, key="flt_prio",
        )
        if sel_prio:
            filtros["prioridad"] = sel_prio

        alertas_opts = ["critica", "urgente", "atencion", "normal"]
        default_al = preset.get("alerta", []) if preset else []
        sel_alerta = st.multiselect(
            "Alerta antigüedad", alertas_opts,
            default=default_al, key="flt_alerta",
            format_func=lambda x: {"critica": "🔴 Crítica", "urgente": "🟠 Urgente",
                                    "atencion": "🟡 Atención", "normal": "🟢 Normal"}.get(x, x),
        )
        if sel_alerta:
            filtros["alerta"] = sel_alerta

        ot_estados = sorted([o for o in df_all["ot_estado"].dropna().unique()])
        sel_ot = st.multiselect("Estado OT", ot_estados, key="flt_ot")
        if sel_ot:
            filtros["ot_estado"] = sel_ot

        # Más filtros (avanzados)
        with st.expander("➕ Más filtros"):
            cuadrillas = sorted([c for c in df_all["crew"].dropna().unique()])
            sel_crew = st.multiselect("Cuadrilla", cuadrillas, key="flt_crew")
            if sel_crew:
                filtros["cuadrilla"] = sel_crew

            leak_types = sorted([t for t in df_all["leak_type"].dropna().unique()])
            sel_lt = st.multiselect("Tipo de fuga", leak_types, key="flt_lt")
            if sel_lt:
                filtros["leak_type"] = sel_lt

            max_dias = int(df_all["dias_sin_reparar"].max() or 200)
            top = max(max_dias, 200)
            dias_range = st.slider("Días sin reparar", 0, top, (0, top), key="flt_dias")
            filtros["dias_min"] = dias_range[0]
            filtros["dias_max"] = dias_range[1]

            busqueda = st.text_input("Buscar (ID, dirección)", key="flt_busq",
                                      value=filtros.get("busqueda", ""))
            if busqueda:
                filtros["busqueda"] = busqueda

    return filtros


# ═══════════════════════════════════════════════════════════════════════
# DETALLE
# ═══════════════════════════════════════════════════════════════════════
def render_detalle(leak_id: int):
    leak = get_leak_by_id(leak_id)
    if not leak:
        st.error(f"❌ Fuga #{leak_id} no encontrada.")
        if st.button("← Volver a la tabla"):
            st.session_state.pop("ver_detalle", None)
            st.rerun()
        return

    # Sidebar minimal en detalle
    with st.sidebar:
        render_sidebar_header(active_page="fugas")
        st.markdown("### Acciones")
        if st.button("← Volver a la tabla", use_container_width=True, type="primary"):
            st.session_state.pop("ver_detalle", None)
            st.rerun()

    # Header con badges
    detail_header(
        leak_id=leak_id,
        address=leak.get("address"),
        prioridad=leak.get("prioridad_final"),
        alerta=leak.get("alerta_antiguedad"),
        ot_estado=leak.get("ot_estado"),
        fecha_det=leak.get("date_detected"),
        crew=leak.get("crew"),
        leak_type=leak.get("leak_type"),
        dias=leak.get("dias_sin_reparar"),
    )

    # Tabs
    t_resumen, t_ot, t_notas, t_hist, t_mapa = st.tabs(
        ["📋 Resumen", "🔧 Orden de Trabajo", "📝 Notas internas", "📜 Historial", "🗺️ Mapa"]
    )

    # ── TAB RESUMEN ─────────────────────────────────────────────────────
    with t_resumen:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 📄 Datos del Excel")
            st.markdown(f"""
            - **Dirección:** {leak.get('address') or '—'}
            - **Tipo:** {leak.get('leak_type') or '—'} / {leak.get('leak_sub_type') or '—'}
            - **Fecha detección:** {leak.get('date_detected') or '—'}
            - **Cuadrilla:** {leak.get('crew') or '—'}
            - **Reparada:** {leak.get('repaired') or '—'}
            - **Visible:** {leak.get('visible') or '—'}
            - **Días sin reparar:** {leak.get('dias_sin_reparar', 0)}
            """)
            if leak.get("actual_x") and leak.get("actual_y"):
                st.markdown(f"- **Coordenadas:** ({leak['actual_y']:.5f}, {leak['actual_x']:.5f})")
            st.markdown("**Comentarios del Excel:**")
            st.info(leak.get("comments_original") or "_(sin comentarios)_")

        with col2:
            st.markdown("##### ✏️ Datos internos")

            prio_opts = ["Auto", "ALTA", "MEDIA", "BAJA"]
            actual_manual = leak.get("prioridad_manual")
            idx_prio = prio_opts.index(actual_manual) if actual_manual in prio_opts[1:] else 0
            prioridad_manual = st.selectbox(
                "Prioridad manual", prio_opts, index=idx_prio,
                help="'Auto' deja que el sistema calcule la prioridad. Cualquier otra opción la fuerza.",
                key="det_prio_manual",
            )

            est_opts = ["Detectada", "OT generada", "Reparada", "Verificada", "Descartada"]
            actual_est = leak.get("estado_interno")
            idx_est = est_opts.index(actual_est) if actual_est in est_opts else 0
            estado_interno = st.selectbox(
                "Estado interno", est_opts, index=idx_est,
                help="El estado interno refleja el seguimiento operativo, distinto del estado de OT.",
                key="det_estado",
            )

            st.markdown(f"**Prioridad calculada:** {priority_badge(leak.get('prioridad_auto'))}",
                        unsafe_allow_html=True)
            st.caption(f"_{leak.get('motivo_prioridad') or 'Sin justificación calculada'}_")

            if st.button("💾 Guardar cambios", type="primary", use_container_width=True, key="save_internos"):
                manual_val = None if prioridad_manual == "Auto" else prioridad_manual
                prioridad_final = manual_val if manual_val else leak.get("prioridad_auto", "BAJA")
                update_leak_internal(leak_id, {
                    "prioridad_manual": manual_val,
                    "prioridad_final": prioridad_final,
                    "estado_interno": estado_interno,
                })
                st.toast("✅ Cambios guardados", icon="✅")
                st.rerun()

    # ── TAB OT ──────────────────────────────────────────────────────────
    with t_ot:
        st.markdown("##### 📋 Estado de la Orden de Trabajo")

        ot_estados_opts = ["Pendiente por generar", "Solicitada", "Generada", "Finalizada"]
        ot_idx = ot_estados_opts.index(leak.get("ot_estado")) if leak.get("ot_estado") in ot_estados_opts else 0
        ot_estado = st.radio("Estado OT", ot_estados_opts, index=ot_idx, horizontal=True, key="det_ot_estado")

        if leak.get("ot_estado") == "Solicitada" and leak.get("ot_fecha_solicitud"):
            st.caption(f"✉️ Solicitada por correo el {str(leak['ot_fecha_solicitud'])[:10]}")

        ot_numero = st.text_input(
            "Número de OT", value=leak.get("ot_numero") or "",
            placeholder="Ej. OT-2026-1234", key="det_ot_num",
            disabled=(ot_estado in ("Pendiente por generar", "Solicitada")),
        )

        col_f1, col_f2 = st.columns(2)
        ot_fecha_gen = None
        ot_fecha_fin = None
        with col_f1:
            if ot_estado in ("Generada", "Finalizada"):
                default_gen = pd.to_datetime(leak["ot_fecha_generacion"]).date() if leak.get("ot_fecha_generacion") else None
                ot_fecha_gen = st.date_input("Fecha de generación", value=default_gen, key="det_ot_fgen")
        with col_f2:
            if ot_estado == "Finalizada":
                default_fin = pd.to_datetime(leak["ot_fecha_finalizacion"]).date() if leak.get("ot_fecha_finalizacion") else None
                ot_fecha_fin = st.date_input("Fecha de finalización", value=default_fin, key="det_ot_ffin")

        if st.button("💾 Guardar OT", type="primary", use_container_width=True, key="save_ot"):
            if ot_estado == "Generada" and not ot_numero.strip():
                st.error("❌ Debes ingresar el número de OT para marcarla como Generada.")
            elif ot_estado == "Finalizada" and not ot_fecha_fin:
                st.error("❌ Debes ingresar la fecha de finalización.")
            else:
                campos_ot = {"ot_estado": ot_estado, "ot_numero": ot_numero or None}
                if ot_fecha_gen:
                    campos_ot["ot_fecha_generacion"] = str(ot_fecha_gen)
                if ot_fecha_fin:
                    campos_ot["ot_fecha_finalizacion"] = str(ot_fecha_fin)
                if ot_estado == "Generada":
                    campos_ot["estado_interno"] = "OT generada"
                update_leak_internal(leak_id, campos_ot)
                st.toast("✅ OT actualizada", icon="📋")
                st.rerun()

    # ── TAB NOTAS ───────────────────────────────────────────────────────
    with t_notas:
        st.markdown("##### 📝 Notas internas del operador")
        notas = st.text_area(
            "Notas (no afectan al Excel)",
            value=leak.get("notas_internas") or "",
            height=200, key="det_notas",
            placeholder="Ej. Se contactó al usuario el 02/05. Pendiente de validación con cuadrilla...",
        )
        if st.button("💾 Guardar notas", type="primary", key="save_notas"):
            update_leak_internal(leak_id, {"notas_internas": notas})
            st.toast("✅ Notas guardadas", icon="📝")
            st.rerun()

    # ── TAB HISTORIAL ──────────────────────────────────────────────────
    with t_hist:
        st.markdown("##### 📜 Historial de cambios")
        hist = get_status_history(leak_id)
        if hist.empty:
            empty_state("📋", "Sin cambios registrados", "Las modificaciones aparecerán aquí cuando edites campos internos.")
        else:
            st.dataframe(
                hist[["fecha", "campo_modificado", "valor_anterior", "valor_nuevo", "origen"]].rename(columns={
                    "fecha": "Fecha", "campo_modificado": "Campo",
                    "valor_anterior": "Antes", "valor_nuevo": "Después", "origen": "Origen",
                }),
                use_container_width=True, hide_index=True,
            )

    # ── TAB MAPA ───────────────────────────────────────────────────────
    with t_mapa:
        if leak.get("actual_x") and leak.get("actual_y"):
            try:
                import folium
                from streamlit_folium import st_folium
                m = folium.Map(location=[leak["actual_y"], leak["actual_x"]],
                               zoom_start=17, tiles="CartoDB positron")
                color_marker = {"ALTA": "red", "MEDIA": "orange", "BAJA": "green"}.get(
                    leak.get("prioridad_final"), "gray")
                folium.CircleMarker(
                    location=[leak["actual_y"], leak["actual_x"]],
                    radius=12, color=color_marker, fill=True,
                    fill_color=color_marker, fill_opacity=0.85,
                    popup=f"Leak #{leak_id}",
                    tooltip=leak.get("address", ""),
                ).add_to(m)
                st_folium(m, use_container_width=True, height=420, key=f"map_det_{leak_id}")
            except Exception as e:
                st.warning(f"No se pudo cargar el mapa: {e}")
        else:
            empty_state("📍", "Sin coordenadas", "Esta fuga no tiene coordenadas registradas en el Excel.")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
if "ver_detalle" in st.session_state:
    render_detalle(st.session_state["ver_detalle"])
    st.stop()

# Header de página
st.markdown("# 💧 Gestión de Fugas")
st.caption("Tabla operativa con filtros, prioridades y órdenes de trabajo")

filtros = render_filters()
df = get_all_leaks(filtros)

if df.empty:
    empty_state(
        "🔍", "Sin resultados",
        "No hay fugas que coincidan con los filtros seleccionados. Prueba a relajar los criterios.",
    )
    st.stop()

# Tabs principales
tab_tabla, tab_ot = st.tabs(["📋 Tabla general", "🔧 Por estado de OT"])

with tab_tabla:
    # ─── BARRA SUPERIOR ─────────────────────────────────────────────────
    col_info, col_edit = st.columns([3, 2])
    with col_info:
        st.markdown(f"**{len(df)} fugas encontradas** · Selecciona filas para acciones masivas")
    with col_edit:
        modo_edicion = st.toggle(
            "✏️ Modo edición (prioridad manual)", value=False,
            help="Activa para modificar la prioridad manual de fugas. Desactivado: vista de solo lectura segura.",
        )

    # ─── PREPARAR DF VISUAL ─────────────────────────────────────────────
    df_display = df.copy()
    df_display["Prioridad"] = df_display["prioridad_final"].map(
        lambda x: f"{PRIO_EMOJI.get(x,'⚪')} {x or '—'}")
    df_display["Alerta"] = df_display["alerta_antiguedad"].map(
        lambda x: f"{ALERTA_EMOJI.get(x,'⚪')} {x or '—'}")
    df_display["Comentarios"] = df_display["comments_original"].fillna("").str.slice(0, 60)

    cols_basic = ["leak_id", "address", "leak_type", "leak_sub_type",
                  "dias_sin_reparar", "Prioridad", "Alerta", "ot_estado", "ot_numero",
                  "crew", "Comentarios"]
    rename_map = {
        "leak_id": "Leak ID", "address": "Dirección", "leak_type": "Tipo",
        "leak_sub_type": "Sub-tipo", "dias_sin_reparar": "Días",
        "ot_estado": "OT Estado", "ot_numero": "OT N°", "crew": "Cuadrilla",
    }

    if not modo_edicion:
        # ─── MODO LECTURA: dataframe con selección nativa ──────────────
        sel = st.dataframe(
            df_display[cols_basic].rename(columns=rename_map),
            use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="multi-row",
            key="tabla_fugas",
            column_config={
                "Leak ID": st.column_config.NumberColumn(format="%d"),
                "Días": st.column_config.NumberColumn(format="%d"),
            },
            height=500,
        )

        sel_indices = sel.selection.rows if hasattr(sel, "selection") else []
        sel_leak_ids = [int(df_display.iloc[i]["leak_id"]) for i in sel_indices]

        # ─── BARRA DE ACCIONES PARA SELECCIÓN ──────────────────────────
        if sel_leak_ids:
            st.markdown(
                f'<div class="sticky-actionbar">'
                f'<strong>✓ {len(sel_leak_ids)} fuga{"s" if len(sel_leak_ids)>1 else ""} seleccionada{"s" if len(sel_leak_ids)>1 else ""}</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )

            cb1, cb2, cb3, cb4 = st.columns(4)
            with cb1:
                if len(sel_leak_ids) == 1:
                    if st.button(f"🔍 Ver detalle de #{sel_leak_ids[0]}",
                                 use_container_width=True, type="primary"):
                        st.session_state["ver_detalle"] = sel_leak_ids[0]
                        st.rerun()
                else:
                    st.button("🔍 Ver detalle",
                              use_container_width=True, disabled=True,
                              help="Selecciona solo 1 fila para ver el detalle.")
            with cb2:
                if st.button("📧 Solicitar OT", use_container_width=True):
                    st.session_state["leak_ids_correo"] = sel_leak_ids
                    st.session_state["accion_correo"] = "OT"
                    st.switch_page("pages/6_Correos.py")
            with cb3:
                if st.button("🔔 Recordatorio", use_container_width=True):
                    st.session_state["leak_ids_correo"] = sel_leak_ids
                    st.session_state["accion_correo"] = "Recordatorio"
                    st.switch_page("pages/6_Correos.py")
            with cb4:
                sel_df = df[df["leak_id"].isin(sel_leak_ids)]
                buf = io.BytesIO()
                sel_df.to_excel(buf, index=False)
                st.download_button(
                    "📥 Exportar selección",
                    data=buf.getvalue(),
                    file_name=f"fugas_seleccionadas_{len(sel_leak_ids)}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        else:
            st.caption("💡 Tip: marca la casilla a la izquierda de cada fila para seleccionar fugas y aplicar acciones masivas.")
    else:
        # ─── MODO EDICIÓN: solo prioridad manual ───────────────────────
        st.warning("✏️ **Modo edición activo.** Solo la columna 'Prioridad Manual' es editable. Los cambios se guardan automáticamente.")

        df_edit = df_display[cols_basic + ["prioridad_manual"]].copy().rename(columns=rename_map)
        df_edit = df_edit.rename(columns={"prioridad_manual": "Prioridad Manual"})

        edited = st.data_editor(
            df_edit,
            use_container_width=True, hide_index=True,
            disabled=cols_basic,  # todo readonly menos prioridad_manual
            column_config={
                "Prioridad Manual": st.column_config.SelectboxColumn(
                    "Prioridad Manual",
                    options=["", "ALTA", "MEDIA", "BAJA"],
                    help="Override manual de la prioridad calculada.",
                ),
            },
            height=500,
            key="editor_fugas_manual",
        )

        # Aplicar cambios
        original_ids = df_display["leak_id"].tolist()
        n_changes = 0
        for i, row in edited.iterrows():
            if i < len(original_ids):
                lid = original_ids[i]
                nueva_prio = row.get("Prioridad Manual", "") or ""
                orig_row = df[df["leak_id"] == lid]
                if not orig_row.empty:
                    orig_prio = orig_row.iloc[0].get("prioridad_manual") or ""
                    if str(nueva_prio) != str(orig_prio):
                        manual_val = nueva_prio if nueva_prio in ("ALTA", "MEDIA", "BAJA") else None
                        prio_final = manual_val if manual_val else orig_row.iloc[0].get("prioridad_auto", "BAJA")
                        update_leak_internal(lid, {
                            "prioridad_manual": manual_val,
                            "prioridad_final": prio_final,
                        })
                        n_changes += 1
        if n_changes > 0:
            st.toast(f"✅ {n_changes} prioridad(es) actualizada(s)", icon="✏️")

    # ─── EXPORTAR TODA LA VISTA FILTRADA ───────────────────────────────
    st.markdown("---")
    col_e1, col_e2 = st.columns([3, 1])
    with col_e1:
        st.caption(f"💾 Exporta las {len(df)} fugas que cumplen los filtros actuales.")
    with col_e2:
        buf_all = io.BytesIO()
        df.to_excel(buf_all, index=False)
        st.download_button(
            "📥 Exportar vista filtrada",
            data=buf_all.getvalue(),
            file_name=f"fugas_filtradas_{len(df)}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ═══════════════════════════════════════════════════════════════════════
# TAB POR ESTADO DE OT
# ═══════════════════════════════════════════════════════════════════════
with tab_ot:
    df_all_ot = get_all_leaks()

    ot_pendiente = df_all_ot[df_all_ot["ot_estado"] == "Pendiente por generar"]
    ot_solicitada = df_all_ot[df_all_ot["ot_estado"] == "Solicitada"]
    ot_generada = df_all_ot[df_all_ot["ot_estado"] == "Generada"]
    ot_finalizada = df_all_ot[df_all_ot["ot_estado"] == "Finalizada"]

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    from src.ui import kpi_card
    with k1:
        kpi_card("Pendientes por generar", len(ot_pendiente), color="warning", icon="⏳")
    with k2:
        kpi_card("Solicitadas por correo", len(ot_solicitada), color="warning", icon="✉️")
    with k3:
        kpi_card("Generadas (en curso)", len(ot_generada), color="primary", icon="📋")
    with k4:
        kpi_card("Finalizadas", len(ot_finalizada), color="success", icon="✅")

    st.markdown("<br>", unsafe_allow_html=True)

    tab_p, tab_s, tab_g, tab_f = st.tabs([
        f"⏳ Pendientes ({len(ot_pendiente)})",
        f"✉️ Solicitadas ({len(ot_solicitada)})",
        f"📋 Generadas ({len(ot_generada)})",
        f"✅ Finalizadas ({len(ot_finalizada)})",
    ])

    cols_show = ["leak_id", "address", "leak_type", "dias_sin_reparar",
                 "prioridad_final", "alerta_antiguedad", "crew"]

    with tab_p:
        if ot_pendiente.empty:
            empty_state("✅", "Sin OTs pendientes", "Todas las fugas tienen OT asignada.")
        else:
            st.dataframe(ot_pendiente[cols_show], use_container_width=True, hide_index=True)
    with tab_s:
        if ot_solicitada.empty:
            empty_state("✉️", "Sin OTs solicitadas", "No hay fugas pendientes de respuesta del contratista.")
        else:
            st.dataframe(ot_solicitada[cols_show + ["ot_fecha_solicitud"]],
                          use_container_width=True, hide_index=True)
    with tab_g:
        if ot_generada.empty:
            empty_state("📋", "Sin OTs en curso", "No hay OTs generadas pendientes de finalizar.")
        else:
            st.dataframe(ot_generada[cols_show + ["ot_numero", "ot_fecha_generacion"]],
                          use_container_width=True, hide_index=True)
    with tab_f:
        if ot_finalizada.empty:
            empty_state("⏰", "Sin OTs finalizadas", "Aún no hay OTs marcadas como finalizadas.")
        else:
            st.dataframe(ot_finalizada[cols_show + ["ot_numero", "ot_fecha_generacion", "ot_fecha_finalizacion"]],
                          use_container_width=True, hide_index=True)
