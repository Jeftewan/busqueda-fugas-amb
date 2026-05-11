import streamlit as st
import sys, os
import tempfile
from datetime import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.importer import importar_excel
from src.models import get_import_log
from src.ui import (
    inject_global_css, render_sidebar_header, empty_state,
    section_header, kpi_card,
)

st.set_page_config(page_title="Cargar Excel", page_icon="📥", layout="wide")
inject_global_css()

with st.sidebar:
    render_sidebar_header(active_page="cargar")

st.markdown("# 📥 Cargar Excel")
st.caption("Importa el archivo `AMB_1.xlsx` actualizado por el contratista")

# ───── CHECK ÚLTIMA CARGA ──────────────────────────────────────────────
log_df = get_import_log()
if not log_df.empty:
    ultima = log_df.iloc[0]
    fecha_ult = ultima["fecha_carga"]
    try:
        dt_ult = datetime.fromisoformat(fecha_ult)
        horas = (datetime.now() - dt_ult).total_seconds() / 3600
        if horas > 24:
            dias = int(horas / 24)
            st.warning(f"⏰ Hace **{dias} día(s)** que no actualizas los datos. "
                        f"Considera cargar el Excel más reciente.")
    except Exception:
        pass

# ───── UPLOADER ────────────────────────────────────────────────────────
st.markdown("##### 📂 Selecciona el archivo")
uploaded = st.file_uploader(
    "Arrastra el archivo `AMB_1.xlsx` aquí o haz click para seleccionar",
    type=["xlsx"],
    help="El archivo debe contener las hojas: Collected Data, Crew Performance, Remaining Pois.",
)

if uploaded:
    st.success(f"✅ Archivo cargado: **{uploaded.name}** ({uploaded.size/1024:.1f} KB)")

    # ───── PREVIEW DE HOJAS ────────────────────────────────────────────
    section_header("Vista previa", subtitle="Revisa el contenido antes de importar")

    HOJAS_REQUERIDAS = ["Collected Data", "Crew Performance", "Remaining Pois"]

    try:
        # Leer el archivo en memoria
        bytes_data = uploaded.read()
        excel_file = pd.ExcelFile(__import__("io").BytesIO(bytes_data))
        hojas_encontradas = excel_file.sheet_names

        # Validación
        faltantes = [h for h in HOJAS_REQUERIDAS if h not in hojas_encontradas]
        if faltantes:
            st.error(f"❌ El Excel no tiene las hojas requeridas. Faltan: **{', '.join(faltantes)}**")
            st.info(f"💡 Hojas encontradas: {', '.join(hojas_encontradas)}")
            st.stop()
        else:
            st.success(f"✅ Las 3 hojas requeridas están presentes")

        # Tabs de preview
        tab_cd, tab_cp, tab_rp = st.tabs([
            f"📋 Collected Data", f"👷 Crew Performance", f"📍 Remaining Pois"
        ])

        with tab_cd:
            df_cd = pd.read_excel(excel_file, sheet_name="Collected Data")
            st.caption(f"**{len(df_cd)} filas** · {len(df_cd.columns)} columnas")
            st.dataframe(df_cd.head(20), use_container_width=True, hide_index=True, height=320)

        with tab_cp:
            df_cp = pd.read_excel(excel_file, sheet_name="Crew Performance")
            st.caption(f"**{len(df_cp)} filas** · {len(df_cp.columns)} columnas")
            st.dataframe(df_cp.head(20), use_container_width=True, hide_index=True, height=320)

        with tab_rp:
            df_rp = pd.read_excel(excel_file, sheet_name="Remaining Pois")
            st.caption(f"**{len(df_rp)} filas** · {len(df_rp.columns)} columnas")
            st.dataframe(df_rp.head(20), use_container_width=True, hide_index=True, height=320)

        # ───── BOTÓN IMPORTAR ──────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        col_imp1, col_imp2 = st.columns([3, 1])
        with col_imp2:
            importar_btn = st.button("🚀 Importar al sistema", type="primary",
                                       use_container_width=True)
        with col_imp1:
            st.caption(f"📦 Total a importar: **{len(df_cd)} POIs**, "
                       f"**{len(df_cp)} días de productividad**, "
                       f"**{len(df_rp)} POIs por inspeccionar**")

        if importar_btn:
            with st.spinner("Importando datos al sistema..."):
                try:
                    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                        tmp.write(bytes_data)
                        tmp_path = tmp.name

                    resumen = importar_excel(tmp_path)
                    os.unlink(tmp_path)

                    st.toast("✅ Importación completada", icon="📥")

                    # ───── RESUMEN VISUAL ──────────────────────────────
                    section_header("Resumen de cambios",
                                    subtitle="Lo que cambió respecto a la última importación")

                    r1, r2, r3, r4 = st.columns(4)
                    with r1:
                        kpi_card("POIs nuevos", resumen["nuevos_pois"],
                                 color="success" if resumen["nuevos_pois"] > 0 else "primary",
                                 icon="🆕")
                    with r2:
                        kpi_card("Fugas nuevas", resumen["nuevas_leaks"],
                                 color="success" if resumen["nuevas_leaks"] > 0 else "primary",
                                 icon="💧")
                    with r3:
                        kpi_card("Reparadas", resumen["reparados_nuevos"],
                                 color="success" if resumen["reparados_nuevos"] > 0 else "primary",
                                 icon="✅")
                    with r4:
                        kpi_card("Discrepancias", resumen["discrepancias"],
                                 color="danger" if resumen["discrepancias"] > 0 else "success",
                                 icon="⚠️")

                    r5, r6 = st.columns(2)
                    with r5:
                        kpi_card("POIs actualizados", resumen["modificados_pois"],
                                 color="primary", icon="🔄")
                    with r6:
                        kpi_card("Fugas actualizadas", resumen["modificadas_leaks"],
                                 color="primary", icon="🔄")

                    # Discrepancias detalladas
                    if resumen["discrepancias"] > 0:
                        st.warning(
                            f"⚠️ **{resumen['discrepancias']} discrepancia(s) detectada(s):** "
                            "fugas marcadas internamente como cerradas que reaparecen como no reparadas en el Excel. "
                            "Revisa la tabla de Fugas para investigarlas."
                        )

                    # CTA siguiente paso
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_cta1, col_cta2 = st.columns(2)
                    with col_cta1:
                        if st.button("📊 Ir al Dashboard", use_container_width=True, type="primary"):
                            st.switch_page("pages/1_Dashboard.py")
                    with col_cta2:
                        if st.button("💧 Ver tabla de fugas", use_container_width=True):
                            st.switch_page("pages/2_Fugas.py")

                except ValueError as e:
                    st.error(f"❌ El Excel no tiene el formato esperado: {e}")
                    st.info("💡 Verifica que las hojas tengan los nombres exactos: "
                            "**Collected Data**, **Crew Performance**, **Remaining Pois**.")
                except FileNotFoundError:
                    st.error("❌ El archivo no se encuentra. Inténtalo de nuevo.")
                except Exception as e:
                    st.error(f"❌ Error inesperado al importar: {e}")
                    st.info("💡 Si el problema persiste, verifica que el Excel no esté abierto en otra aplicación.")

    except Exception as e:
        st.error(f"❌ No se puede leer el archivo: {e}")
        st.info("💡 Asegúrate de que sea un .xlsx válido y no esté corrupto.")

# ───── HISTORIAL ───────────────────────────────────────────────────────
st.markdown("---")
section_header("📋 Historial de importaciones")

if log_df.empty:
    empty_state("📥", "Sin importaciones aún", "Cuando importes el primer Excel aparecerá aquí el historial.")
else:
    display_df = log_df[["fecha_carga", "archivo", "registros_nuevos",
                          "registros_modificados", "reparados_nuevos", "discrepancias"]].copy()
    display_df["fecha_carga"] = pd.to_datetime(display_df["fecha_carga"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")
    display_df.columns = ["Fecha", "Archivo", "Nuevos", "Modificados", "Reparados nuevos", "Discrepancias"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
