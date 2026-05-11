import streamlit as st
import sys, os
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.db import get_connection
from src.utils import load_config, now_iso
from src.ui import (
    inject_global_css, render_sidebar_header, section_header,
)

st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
inject_global_css()

with st.sidebar:
    render_sidebar_header(active_page="config")

st.markdown("# ⚙️ Configuración del Sistema")
st.caption("Ajustes de SMTP, prioridades y palabras clave")

config = load_config()


def save_config_key(clave: str, valor):
    conn = get_connection()
    conn.execute("REPLACE INTO app_config (clave, valor) VALUES (?,?)",
                 (clave, yaml.dump(valor, allow_unicode=True)))
    conn.commit()
    conn.close()


# Banner onboarding si SMTP no está configurado
smtp_cfg = config.get("smtp", {})
dest_cfg = config.get("destinatarios", {})
if not smtp_cfg.get("user") or not dest_cfg.get("fijo"):
    with st.container(border=True):
        st.markdown("##### 🎯 Primer arranque · Configuración pendiente")
        st.markdown(
            "Para enviar correos al contratista necesitas:\n\n"
            "1. **Activar la verificación en 2 pasos** en tu cuenta de Gmail.\n"
            "2. **Generar una App Password** en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).\n"
            "3. **Pegar las credenciales** en la pestaña SMTP/Correo de abajo.\n"
            "4. **Definir el destinatario fijo** (correo del contratista).\n"
            "5. **Probar el envío** con el botón 'Enviar correo de prueba'."
        )

tab_smtp, tab_prioridad, tab_palabras = st.tabs([
    "📧 SMTP / Correo", "🎯 Prioridad", "🔤 Palabras clave",
])

# ═══════════════════════════════════════════════════════════════════════
# SMTP
# ═══════════════════════════════════════════════════════════════════════
with tab_smtp:
    section_header("Configuración SMTP (Gmail)")

    smtp = config.get("smtp", {})

    col1, col2 = st.columns(2)
    with col1:
        smtp_user = st.text_input(
            "Usuario Gmail",
            value=smtp.get("user", ""),
            placeholder="tu_correo@gmail.com",
            help="Tu cuenta de Gmail (la misma con la que creaste el App Password).",
        )
        smtp_pass = st.text_input(
            "App Password (16 caracteres)",
            value=smtp.get("password", ""),
            type="password",
            placeholder="abcd efgh ijkl mnop",
            help="No es tu contraseña de Gmail. Es un App Password de 16 caracteres generado en myaccount.google.com/apppasswords.",
        )
        smtp_nombre = st.text_input(
            "Nombre del remitente",
            value=smtp.get("remitente_nombre", "Seguimiento Fugas - Acueducto"),
            help="Nombre que verá el contratista en el campo 'De:' del correo.",
        )
    with col2:
        dest_fijo = st.text_input(
            "Destinatario fijo (contratista)",
            value=config.get("destinatarios", {}).get("fijo", ""),
            placeholder="contratista@empresa.com",
            help="Correo al que se enviarán todas las solicitudes y recordatorios.",
        )
        st.info("💡 **Tip:** para obtener el App Password necesitas tener activada la verificación en 2 pasos en tu cuenta de Gmail.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("💾 Guardar configuración", type="primary", use_container_width=True):
            save_config_key("smtp.user", smtp_user)
            save_config_key("smtp.password", smtp_pass)
            save_config_key("smtp.remitente_nombre", smtp_nombre)
            save_config_key("destinatarios.fijo", dest_fijo)
            st.toast("✅ Configuración SMTP guardada", icon="⚙️")
            st.rerun()

    with col_b2:
        if st.button("📧 Enviar correo de prueba", use_container_width=True):
            # Validaciones previas
            if not smtp_user.strip():
                st.error("❌ Falta el usuario de Gmail.")
            elif not smtp_pass.strip():
                st.error("❌ Falta el App Password.")
            elif not dest_fijo.strip():
                st.error("❌ Falta el destinatario fijo.")
            else:
                with st.spinner("🔌 Conectando a smtp.gmail.com..."):
                    from src.mailer import enviar_correo
                    cuerpo = """
                    <p>Hola,</p>
                    <p>Este es un correo de prueba del sistema <b>Seguimiento de Fugas - Acueducto</b>.</p>
                    <p>Si lo recibes correctamente, la configuración SMTP funciona.</p>
                    <p style="color:#5C7184;font-size:12px">Enviado automáticamente.</p>
                    """
                    ok, msg = enviar_correo(
                        "✅ Prueba — Seguimiento de Fugas", cuerpo,
                    )
                    if ok:
                        st.toast("✅ Correo de prueba enviado", icon="📧")
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
                        # Mensajes específicos según el tipo de error
                        msg_low = msg.lower()
                        if "auth" in msg_low or "username" in msg_low or "password" in msg_low:
                            st.info("💡 Verifica que el App Password sea correcto (16 caracteres, sin espacios).")
                        elif "connect" in msg_low or "network" in msg_low or "timeout" in msg_low:
                            st.info("💡 Verifica tu conexión a internet o que el firewall no bloquee el puerto 587.")
                        else:
                            st.info("💡 Asegúrate de tener activada la verificación en 2 pasos en Gmail.")


# ═══════════════════════════════════════════════════════════════════════
# PRIORIDAD
# ═══════════════════════════════════════════════════════════════════════
with tab_prioridad:
    section_header("Pesos del algoritmo de prioridad",
                    subtitle="Modifica cómo se calcula automáticamente la prioridad de cada fuga")

    pesos = config["prioridad"]["pesos"]
    umbrales = config["prioridad"]["umbrales"]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 🔤 Pesos por categoría de palabra")
        p_alta = st.slider("Palabra ALTA detectada en comentario", 0, 100, pesos.get("palabra_alta", 50),
                            help="Puntos sumados si el comentario contiene una palabra de la lista ALTA (ej. 'urgente', 'visible').")
        p_media = st.slider("Palabra MEDIA", 0, 50, pesos.get("palabra_media", 20),
                             help="Puntos por palabras de la lista MEDIA (ej. 'acometida', 'válvula').")
        p_baja = st.slider("Palabra BAJA", -50, 0, pesos.get("palabra_baja", -10),
                            help="Puntos negativos por palabras BAJA (ej. 'fuga interna', 'usuario').")

        st.markdown("##### 🔧 Pesos por tipo de red")
        p_main = st.slider("Main / Hidrante / Red principal", 0, 50, pesos.get("main", 30),
                            help="Las fugas en red principal son más críticas.")
        p_service = st.slider("Service / Acometida", 0, 30, pesos.get("service", 10))
        p_customer = st.slider("Customer-side / Internas", -30, 0, pesos.get("customer_side", -10),
                                help="Fugas en propiedad del usuario son menos prioritarias.")

    with col2:
        st.markdown("##### ➕ Otros pesos")
        p_visible = st.slider("Bonus si Visible='Yes'", 0, 30, pesos.get("visible", 15),
                                help="Las fugas visibles a simple vista son más urgentes.")
        p_dia = st.slider("Puntos por día pendiente", 0, 5, pesos.get("dia_pendiente", 1),
                           help="Cada día sin reparar suma N puntos al score.")
        p_cap = st.slider("Cap máximo de días", 10, 120, pesos.get("cap_dias", 60),
                           help="A partir de este número de días, ya no suma más puntos por antigüedad.")

        st.markdown("##### 📊 Umbrales de categoría")
        u_alta = st.slider("Score mínimo para ALTA", 50, 150, umbrales.get("alta", 70),
                            help="Si score >= este valor → prioridad ALTA.")
        u_media = st.slider("Score mínimo para MEDIA", 10, 80, umbrales.get("media", 30),
                             help="Si score >= este valor (y < umbral ALTA) → prioridad MEDIA.")

    col_pb1, col_pb2 = st.columns(2)
    with col_pb1:
        if st.button("💾 Guardar pesos", type="primary", use_container_width=True):
            nuevos_pesos = {
                "palabra_alta": p_alta, "palabra_media": p_media, "palabra_baja": p_baja,
                "main": p_main, "service": p_service, "customer_side": p_customer,
                "visible": p_visible, "dia_pendiente": p_dia, "cap_dias": p_cap,
            }
            save_config_key("prioridad.pesos", nuevos_pesos)
            save_config_key("prioridad.umbrales", {"alta": u_alta, "media": u_media})
            st.toast("✅ Pesos guardados", icon="⚙️")

    with col_pb2:
        if st.button("🔄 Recalcular prioridades de TODAS las fugas", use_container_width=True):
            with st.spinner("Recalculando prioridades..."):
                from src.priority import recalcular_todas
                n = recalcular_todas()
                st.toast(f"✅ {n} fugas recalculadas", icon="🔄")
                st.success(f"✅ {n} fugas recalculadas con la nueva configuración.")


# ═══════════════════════════════════════════════════════════════════════
# PALABRAS CLAVE
# ═══════════════════════════════════════════════════════════════════════
with tab_palabras:
    section_header("Diccionario de palabras clave",
                    subtitle="Palabras que el sistema busca en los comentarios para clasificar fugas")

    palabras = config.get("palabras_clave", {})

    st.info("💡 Una palabra por línea. El sistema usa coincidencia parcial (case insensitive).")

    col_pk1, col_pk2, col_pk3 = st.columns(3)
    with col_pk1:
        palabras_alta = st.text_area(
            "🔴 Palabras ALTA",
            value="\n".join(str(p) for p in palabras.get("alta", [])),
            height=320,
        )
    with col_pk2:
        palabras_media = st.text_area(
            "🟡 Palabras MEDIA",
            value="\n".join(str(p) for p in palabras.get("media", [])),
            height=320,
        )
    with col_pk3:
        palabras_baja = st.text_area(
            "🟢 Palabras BAJA",
            value="\n".join(str(p) for p in palabras.get("baja", [])),
            height=320,
        )

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if st.button("💾 Guardar palabras clave", type="primary", use_container_width=True):
            nuevas = {
                "alta": [p.strip() for p in palabras_alta.splitlines() if p.strip()],
                "media": [p.strip() for p in palabras_media.splitlines() if p.strip()],
                "baja": [p.strip() for p in palabras_baja.splitlines() if p.strip()],
            }
            save_config_key("palabras_clave", nuevas)
            st.toast("✅ Palabras clave guardadas", icon="🔤")
            st.info("💡 Recuerda **recalcular las prioridades** en la pestaña Prioridad para aplicar los cambios.")
    with col_w2:
        if st.button("🔄 Recalcular ahora", use_container_width=True):
            # Guardar antes de recalcular
            nuevas = {
                "alta": [p.strip() for p in palabras_alta.splitlines() if p.strip()],
                "media": [p.strip() for p in palabras_media.splitlines() if p.strip()],
                "baja": [p.strip() for p in palabras_baja.splitlines() if p.strip()],
            }
            save_config_key("palabras_clave", nuevas)
            with st.spinner("Recalculando..."):
                from src.priority import recalcular_todas
                n = recalcular_todas()
                st.toast(f"✅ Guardado y {n} fugas recalculadas", icon="✏️")
