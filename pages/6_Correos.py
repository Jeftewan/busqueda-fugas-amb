import streamlit as st
import sys, os
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models import get_email_templates, get_emails_sent, get_all_leaks
from src.mailer import enviar_correo
from src.reports import generar_pdf_fugas
from src.db import get_connection
from src.utils import now_iso, load_config
from src.ui import (
    inject_global_css, render_sidebar_header, empty_state,
    section_header, kpi_card,
)

st.set_page_config(page_title="Correos", page_icon="📧", layout="wide")
inject_global_css()

with st.sidebar:
    render_sidebar_header(active_page="correos")

st.markdown("# 📧 Gestión de Correos")
st.caption("Envía solicitudes de OT y recordatorios al contratista")

tab_envio, tab_plantillas, tab_historial = st.tabs([
    "📤 Enviar correo (Wizard)", "✏️ Plantillas", "📋 Historial",
])

# ═══════════════════════════════════════════════════════════════════════
# TAB ENVIAR — WIZARD 3 PASOS
# ═══════════════════════════════════════════════════════════════════════
with tab_envio:
    config = load_config()

    # Verificar configuración SMTP
    if not config.get("smtp", {}).get("user") or not config.get("destinatarios", {}).get("fijo"):
        st.warning(
            "⚙️ **SMTP no configurado.** Antes de enviar correos, configura las credenciales "
            "de Gmail y el destinatario fijo."
        )
        if st.button("⚙️ Ir a Configuración", type="primary"):
            st.switch_page("pages/7_Configuracion.py")

    # Inicializar wizard step
    if "paso_correo" not in st.session_state:
        st.session_state["paso_correo"] = 1

    # Si vienen leaks pre-seleccionadas, saltar al paso 2 directo
    leaks_pre = st.session_state.get("leak_ids_correo", [])
    accion_pre = st.session_state.get("accion_correo", "")
    if leaks_pre and st.session_state["paso_correo"] == 1:
        # Auto-set paso 1 (tipo) y avanzar a 2
        if accion_pre == "OT":
            st.session_state["wiz_tipo"] = "Solicitud de OT"
        elif accion_pre == "Recordatorio":
            st.session_state["wiz_tipo"] = "Recordatorio de pendientes"
        st.session_state["wiz_leak_ids"] = leaks_pre
        st.session_state["paso_correo"] = 3  # ir directo a confirmar
        st.session_state.pop("leak_ids_correo", None)
        st.session_state.pop("accion_correo", None)

    paso = st.session_state["paso_correo"]

    # Indicador visual de pasos
    pasos_html = """
    <div style="display:flex;gap:8px;align-items:center;margin:18px 0 24px 0">
    """
    for i, label in enumerate(["1. Tipo y plantilla", "2. Seleccionar fugas", "3. Confirmar y enviar"], start=1):
        if i < paso:
            color, bg = "#FFFFFF", "#2EB872"
            badge = "✓"
        elif i == paso:
            color, bg = "#FFFFFF", "#0B6E99"
            badge = str(i)
        else:
            color, bg = "#A0AEC0", "#F0F4F8"
            badge = str(i)
        pasos_html += f"""
        <div style="display:flex;align-items:center;gap:8px;flex:1">
            <div style="width:32px;height:32px;border-radius:50%;background:{bg};color:{color};
                        display:flex;align-items:center;justify-content:center;font-weight:700;
                        font-size:0.9rem;flex-shrink:0">{badge}</div>
            <div style="font-weight:{'600' if i==paso else '400'};color:{'#0F2A3E' if i<=paso else '#A0AEC0'};font-size:0.88rem">
                {label}
            </div>
        </div>
        """
        if i < 3:
            pasos_html += '<div style="height:2px;background:#E1E8EE;flex:0.5"></div>'
    pasos_html += "</div>"
    st.markdown(pasos_html, unsafe_allow_html=True)

    # ─── PASO 1 ────────────────────────────────────────────────────────
    if paso == 1:
        st.markdown("##### Paso 1 · Elige el tipo de correo")
        tipo = st.radio(
            "Tipo de correo",
            ["Solicitud de OT", "Recordatorio de pendientes"],
            horizontal=True,
            key="wiz_tipo",
            help="Solicitud de OT: pide al contratista generar nuevas órdenes. Recordatorio: lista las fugas que ya tienen OT pero llevan tiempo sin reparar.",
        )
        st.caption(
            "📋 **Solicitud de OT:** se usa para pedir nuevas órdenes al contratista cuando hay fugas críticas sin atender."
            if "OT" in tipo else
            "🔔 **Recordatorio:** lista de fugas pendientes ya conocidas para apurar su atención."
        )

        col_b1, col_b2 = st.columns([4, 1])
        with col_b2:
            if st.button("Siguiente →", type="primary", use_container_width=True):
                st.session_state["paso_correo"] = 2
                st.rerun()

    # ─── PASO 2 ────────────────────────────────────────────────────────
    elif paso == 2:
        tipo = st.session_state.get("wiz_tipo", "Solicitud de OT")
        st.markdown(f"##### Paso 2 · Selecciona las fugas a incluir ({tipo})")

        df_fugas = get_all_leaks({"solo_no_reparadas": True})
        if df_fugas.empty:
            empty_state("🔍", "Sin fugas pendientes", "No hay fugas sin reparar para incluir en el correo.")
        else:
            df_fugas["Comentario"] = df_fugas["comments_original"].fillna("").str.slice(0, 60)
            sel = st.dataframe(
                df_fugas[["leak_id", "address", "leak_type", "dias_sin_reparar", "prioridad_final", "Comentario"]].rename(columns={
                    "leak_id": "Leak ID", "address": "Dirección", "leak_type": "Tipo",
                    "dias_sin_reparar": "Días", "prioridad_final": "Prioridad",
                }),
                use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="multi-row",
                key="wiz_table_fugas", height=400,
            )
            sel_idx = sel.selection.rows if hasattr(sel, "selection") else []
            sel_ids = [int(df_fugas.iloc[i]["leak_id"]) for i in sel_idx]
            st.session_state["wiz_leak_ids"] = sel_ids

            if sel_ids:
                st.success(f"✓ **{len(sel_ids)} fuga(s) seleccionada(s)**")
            else:
                st.info("💡 Marca las casillas para seleccionar las fugas a incluir en el correo.")

        col_b1, col_b2, col_b3 = st.columns([1, 3, 1])
        with col_b1:
            if st.button("← Atrás", use_container_width=True):
                st.session_state["paso_correo"] = 1
                st.rerun()
        with col_b3:
            sel_count = len(st.session_state.get("wiz_leak_ids", []))
            if st.button("Siguiente →", type="primary", use_container_width=True,
                          disabled=sel_count == 0):
                st.session_state["paso_correo"] = 3
                st.rerun()

    # ─── PASO 3 ────────────────────────────────────────────────────────
    elif paso == 3:
        tipo = st.session_state.get("wiz_tipo", "Solicitud de OT")
        leak_ids = st.session_state.get("wiz_leak_ids", [])
        st.markdown(f"##### Paso 3 · Confirma y envía ({len(leak_ids)} fugas)")

        # Plantilla
        plantillas_df = get_email_templates()
        plantilla_nombre = "Solicitud de OT" if "OT" in tipo else "Recordatorio de pendientes"
        plantilla_row = plantillas_df[plantillas_df["nombre"] == plantilla_nombre]
        asunto_base = plantilla_row.iloc[0]["asunto"] if not plantilla_row.empty else "{n_fugas} fugas — {fecha}"
        cuerpo_base = plantilla_row.iloc[0]["cuerpo_html"] if not plantilla_row.empty else ""

        n_fugas = len(leak_ids)
        lista_fugas_html = "".join(f"<li>Leak {lid}</li>" for lid in leak_ids) if leak_ids else "<li>Sin fugas</li>"
        fecha_str = date.today().strftime("%d/%m/%Y")

        try:
            asunto = asunto_base.format(n_fugas=n_fugas, fecha=fecha_str)
            cuerpo = cuerpo_base.format(n_fugas=n_fugas, lista_fugas=f"<ul>{lista_fugas_html}</ul>", fecha=fecha_str)
        except KeyError:
            asunto = asunto_base
            cuerpo = cuerpo_base

        destinatario = config.get("destinatarios", {}).get("fijo", "(no configurado)")

        # Resumen
        col_dest1, col_dest2 = st.columns(2)
        with col_dest1:
            st.markdown(f"**📧 Para:** `{destinatario}`")
            st.markdown(f"**📋 Tipo:** {tipo}")
        with col_dest2:
            st.markdown(f"**💧 Fugas:** {n_fugas}")
            st.markdown(f"**📎 Adjunto:** PDF auto-generado")

        st.markdown("---")

        asunto_edit = st.text_input("Asunto", value=asunto, key="wiz_asunto")

        sub_edit, sub_prev = st.tabs(["✏️ Editar HTML", "👁️ Previsualizar"])
        with sub_edit:
            cuerpo_edit = st.text_area("Cuerpo HTML", value=cuerpo, height=240, key="wiz_cuerpo")
        with sub_prev:
            cuerpo_actual = st.session_state.get("wiz_cuerpo", cuerpo)
            st.components.v1.html(
                f'<div style="font-family:Arial,sans-serif;padding:20px;background:#fff;border:1px solid #E1E8EE;border-radius:8px">{cuerpo_actual}</div>',
                height=300, scrolling=True,
            )

        st.markdown("---")

        col_b1, col_b2, col_b3 = st.columns([1, 2, 2])
        with col_b1:
            if st.button("← Atrás", use_container_width=True):
                st.session_state["paso_correo"] = 2
                st.rerun()
        with col_b2:
            try:
                pdf_preview = generar_pdf_fugas(leak_ids, "OT" if "OT" in tipo else "Recordatorio")
                st.download_button(
                    "📥 Descargar solo PDF",
                    data=pdf_preview,
                    file_name=f"fugas_{date.today().isoformat()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.warning(f"No se pudo generar PDF: {e}")
        with col_b3:
            if st.button("📤 Enviar correo", type="primary", use_container_width=True):
                with st.spinner("Generando PDF y enviando..."):
                    tipo_pdf = "OT" if "OT" in tipo else "Recordatorio"
                    try:
                        pdf_bytes = generar_pdf_fugas(leak_ids, tipo_pdf)
                        pdf_nombre = f"fugas_{tipo_pdf.lower()}_{date.today().isoformat()}.pdf"

                        cuerpo_final = st.session_state.get("wiz_cuerpo", cuerpo)
                        ok, mensaje = enviar_correo(asunto_edit, cuerpo_final, pdf_bytes, pdf_nombre)

                        conn = get_connection()
                        conn.execute(
                            """INSERT INTO emails_sent (fecha_envio, destinatario, asunto, tipo,
                               leak_ids, cuerpo_html, pdf_adjunto, enviado_ok, error_mensaje)
                               VALUES (?,?,?,?,?,?,?,?,?)""",
                            (now_iso(), destinatario, asunto_edit, tipo_pdf,
                             json.dumps(leak_ids), cuerpo_final,
                             pdf_bytes if ok else None,
                             1 if ok else 0, "" if ok else mensaje)
                        )
                        conn.commit()
                        conn.close()

                        if ok:
                            st.toast(f"✅ Correo enviado a {destinatario}", icon="📧")
                            st.success(mensaje)
                            # Reset wizard
                            for k in ["paso_correo", "wiz_tipo", "wiz_leak_ids",
                                       "wiz_asunto", "wiz_cuerpo"]:
                                st.session_state.pop(k, None)
                        else:
                            st.error(f"❌ {mensaje}")
                            st.info("💡 Verifica las credenciales SMTP en Configuración.")
                    except Exception as e:
                        st.error(f"❌ Error al enviar: {e}")

        # Botón resetear wizard
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Empezar de nuevo (resetear wizard)"):
            for k in ["paso_correo", "wiz_tipo", "wiz_leak_ids", "wiz_asunto", "wiz_cuerpo"]:
                st.session_state.pop(k, None)
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# TAB PLANTILLAS
# ═══════════════════════════════════════════════════════════════════════
with tab_plantillas:
    section_header("Plantillas de correo", subtitle="Edita los textos base usados en los envíos")
    df_p = get_email_templates()

    if df_p.empty:
        empty_state("✏️", "Sin plantillas", "Las plantillas se cargan automáticamente al inicializar la BD.")
    else:
        for _, p in df_p.iterrows():
            with st.expander(f"📝 {p['nombre']}", expanded=False):
                st.caption("**Placeholders disponibles:** `{n_fugas}`, `{lista_fugas}`, `{fecha}`")

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    nuevo_asunto = st.text_input("Asunto", value=p["asunto"], key=f"asunto_{p['id']}")
                    nuevo_cuerpo = st.text_area(
                        "Cuerpo HTML", value=p["cuerpo_html"],
                        height=240, key=f"cuerpo_{p['id']}",
                    )
                with col_p2:
                    st.markdown("**Vista previa:**")
                    preview_cuerpo = nuevo_cuerpo.replace("{n_fugas}", "5") \
                                                  .replace("{fecha}", date.today().strftime("%d/%m/%Y")) \
                                                  .replace("{lista_fugas}", "<ul><li>Leak 12345</li><li>Leak 12346</li></ul>")
                    st.components.v1.html(
                        f'<div style="font-family:Arial,sans-serif;padding:14px;background:#fff;border:1px solid #E1E8EE;border-radius:6px;font-size:13px">{preview_cuerpo}</div>',
                        height=240, scrolling=True,
                    )

                if st.button("💾 Guardar cambios", key=f"save_{p['id']}", type="primary"):
                    conn = get_connection()
                    conn.execute("UPDATE email_templates SET asunto=?, cuerpo_html=? WHERE id=?",
                                  (nuevo_asunto, nuevo_cuerpo, p["id"]))
                    conn.commit()
                    conn.close()
                    st.toast("✅ Plantilla actualizada", icon="✏️")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# TAB HISTORIAL
# ═══════════════════════════════════════════════════════════════════════
with tab_historial:
    section_header("Historial de envíos")
    df_hist = get_emails_sent()
    if df_hist.empty:
        empty_state("📨", "Sin envíos registrados", "Los correos enviados aparecerán aquí con su detalle.")
    else:
        df_hist["Estado"] = df_hist["enviado_ok"].map({1: "✅ OK", 0: "❌ Falló"})

        # KPIs
        k1, k2, k3 = st.columns(3)
        with k1: kpi_card("Total envíos", len(df_hist), color="primary", icon="📨")
        with k2: kpi_card("Exitosos", int((df_hist["enviado_ok"]==1).sum()), color="success", icon="✅")
        with k3: kpi_card("Fallidos", int((df_hist["enviado_ok"]==0).sum()),
                            color="danger" if (df_hist["enviado_ok"]==0).any() else "success", icon="❌")

        st.markdown("<br>", unsafe_allow_html=True)

        sel = st.dataframe(
            df_hist[["id", "fecha_envio", "destinatario", "asunto", "tipo", "Estado"]].rename(columns={
                "id": "ID", "fecha_envio": "Fecha", "destinatario": "Destinatario",
                "asunto": "Asunto", "tipo": "Tipo",
            }),
            use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row", key="hist_table",
        )

        sel_idx = sel.selection.rows if hasattr(sel, "selection") else []
        if sel_idx:
            sel_id = int(df_hist.iloc[sel_idx[0]]["id"])
            with st.expander(f"📨 Detalle del envío #{sel_id}", expanded=True):
                conn = get_connection()
                row = conn.execute("SELECT * FROM emails_sent WHERE id=?", (sel_id,)).fetchone()
                conn.close()
                if row:
                    st.markdown(f"**Asunto:** {row['asunto']}")
                    st.markdown(f"**A:** {row['destinatario']}")
                    if row.get("error_mensaje"):
                        st.error(f"❌ {row['error_mensaje']}")

                    st.markdown("**Cuerpo enviado (preview):**")
                    st.components.v1.html(
                        f'<div style="font-family:Arial,sans-serif;padding:14px;background:#fff;border:1px solid #E1E8EE;border-radius:6px">{row["cuerpo_html"]}</div>',
                        height=240, scrolling=True,
                    )

                    if row["pdf_adjunto"]:
                        st.download_button(
                            "📥 Re-descargar PDF adjunto",
                            data=row["pdf_adjunto"],
                            file_name=f"envio_{sel_id}.pdf",
                            mime="application/pdf",
                        )
