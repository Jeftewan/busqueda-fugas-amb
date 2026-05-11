import os
import shutil
import json
import pandas as pd
from datetime import datetime

from src.db import get_connection
from src.utils import load_config, now_iso, parse_excel_date, safe_str, dias_desde
from src.priority import calcular_score, score_a_categoria, motivo_prioridad
from src.alerts import categoria_alerta, tipo_red


REQUIRED_SHEETS = ["Collected Data", "Crew Performance", "Remaining Pois"]

ARCHIVE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "excel_archive"
)


def _archivar(ruta_excel: str) -> str:
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"AMB_1__{ts}.xlsx"
    dest = os.path.join(ARCHIVE_DIR, nombre)
    shutil.copy2(ruta_excel, dest)
    return dest


def importar_excel(ruta_excel: str) -> dict:
    config = load_config()
    xl = pd.ExcelFile(ruta_excel)

    for sheet in REQUIRED_SHEETS:
        if sheet not in xl.sheet_names:
            raise ValueError(f"Hoja requerida no encontrada: '{sheet}'")

    archivo_archivado = _archivar(ruta_excel)
    conn = get_connection()

    resumen = {
        "nuevos_pois": 0,
        "modificados_pois": 0,
        "nuevas_leaks": 0,
        "modificadas_leaks": 0,
        "reparados_nuevos": 0,
        "discrepancias": 0,
        "archivo": os.path.basename(archivo_archivado),
    }

    # ── Hoja Collected Data ──────────────────────────────────────────────────
    df = xl.parse("Collected Data", dtype={"ID": str, "Leak ID": str})
    df.columns = [c.strip() for c in df.columns]

    for _, row in df.iterrows():
        poi_id = safe_str(row.get("ID"))
        leak_id_raw = safe_str(row.get("Leak ID"))
        if not poi_id:
            continue

        fecha_det = parse_excel_date(row.get("Date"))
        fecha_str = fecha_det.isoformat() if fecha_det else None
        visible_poi = safe_str(row.get("Visible"))
        address = safe_str(row.get("Address"))
        comments = safe_str(row.get("Comments"))
        crew = safe_str(row.get("Crew"))
        pipe_type = safe_str(row.get("Pipe Type"))
        actual_x = row.get("Actual X")
        actual_y = row.get("Actual Y")
        inv_result = safe_str(row.get("Investigation Results"))
        try:
            actual_x = float(actual_x)
        except (TypeError, ValueError):
            actual_x = None
        try:
            actual_y = float(actual_y)
        except (TypeError, ValueError):
            actual_y = None

        # POI
        existing_poi = conn.execute("SELECT id FROM pois WHERE id=?", (poi_id,)).fetchone()
        if existing_poi:
            conn.execute(
                """UPDATE pois SET address=?, actual_x=?, actual_y=?, date_detected=?,
                   investigation_result=?, crew=?, comments=?, pipe_type=?, visible=?,
                   last_updated_at=? WHERE id=?""",
                (address, actual_x, actual_y, fecha_str, inv_result, crew, comments,
                 pipe_type, visible_poi, now_iso(), poi_id),
            )
            resumen["modificados_pois"] += 1
        else:
            conn.execute(
                """INSERT INTO pois (id, address, actual_x, actual_y, date_detected,
                   investigation_result, crew, comments, pipe_type, visible,
                   first_seen_at, last_updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (poi_id, address, actual_x, actual_y, fecha_str, inv_result, crew,
                 comments, pipe_type, visible_poi, now_iso(), now_iso()),
            )
            resumen["nuevos_pois"] += 1

        # Solo procesar leaks reales
        if inv_result not in ("Leak", "Suspected"):
            continue
        if not leak_id_raw or leak_id_raw in ("nan", ""):
            continue

        try:
            leak_id = int(float(leak_id_raw))
        except (ValueError, TypeError):
            continue

        leak_type = safe_str(row.get("Leak Type"))
        leak_sub_type = safe_str(row.get("Leak Sub Type"))
        repaired = safe_str(row.get("Repaired"))
        repair_date = parse_excel_date(row.get("Repair Date"))
        repair_date_str = repair_date.isoformat() if repair_date else None

        dias = dias_desde(fecha_det)

        leak_dict = {
            "comments_original": comments,
            "leak_type": leak_type,
            "Visible": visible_poi,
            "dias_sin_reparar": dias,
        }
        score = calcular_score(leak_dict, config)
        cat = score_a_categoria(score, config["prioridad"]["umbrales"])
        motivo = motivo_prioridad(leak_dict, config)
        tipo = tipo_red(leak_type)
        alerta = categoria_alerta(tipo, dias, config["umbrales_antiguedad"])

        existing_leak = conn.execute(
            "SELECT leak_id, repaired, estado_interno, prioridad_manual, ot_estado, ot_numero, "
            "ot_fecha_generacion, ot_fecha_finalizacion, notas_internas FROM leaks WHERE leak_id=?",
            (leak_id,)
        ).fetchone()

        if existing_leak:
            # Detectar si se reparó
            if existing_leak["repaired"] != "Yes" and repaired == "Yes":
                resumen["reparados_nuevos"] += 1

            # Detectar discrepancia: cerrada internamente pero reaparece como no reparada
            discrepancia = 0
            if existing_leak["estado_interno"] in ("Reparada", "Verificada") and repaired == "No":
                discrepancia = 1
                resumen["discrepancias"] += 1
                conn.execute(
                    """INSERT INTO status_history (leak_id, campo_modificado, valor_anterior,
                       valor_nuevo, fecha, origen) VALUES (?,?,?,?,?,?)""",
                    (leak_id, "discrepancia_excel",
                     existing_leak["estado_interno"], "Repaired=No en Excel",
                     now_iso(), "import"),
                )

            # Preservar campos internos — solo actualizar campos del Excel
            prioridad_final = existing_leak["prioridad_manual"] if existing_leak["prioridad_manual"] in ("ALTA", "MEDIA", "BAJA") else cat

            conn.execute(
                """UPDATE leaks SET poi_id=?, leak_type=?, leak_sub_type=?, repaired=?,
                   repair_date_excel=?, comments_original=?, prioridad_auto=?,
                   prioridad_final=?, score_prioridad=?, motivo_prioridad=?,
                   alerta_antiguedad=?, dias_sin_reparar=?, discrepancia_excel=?,
                   last_updated_at=? WHERE leak_id=?""",
                (poi_id, leak_type, leak_sub_type, repaired, repair_date_str,
                 comments, cat, prioridad_final, score, motivo,
                 alerta, dias, discrepancia, now_iso(), leak_id),
            )
            resumen["modificadas_leaks"] += 1
        else:
            prioridad_final = cat
            conn.execute(
                """INSERT INTO leaks (leak_id, poi_id, leak_type, leak_sub_type, repaired,
                   repair_date_excel, comments_original, prioridad_auto, prioridad_final,
                   score_prioridad, motivo_prioridad, alerta_antiguedad, dias_sin_reparar,
                   discrepancia_excel, estado_interno, ot_estado, first_seen_at, last_updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (leak_id, poi_id, leak_type, leak_sub_type, repaired, repair_date_str,
                 comments, cat, prioridad_final, score, motivo,
                 alerta, dias, 0, "Detectada", "Pendiente por generar",
                 now_iso(), now_iso()),
            )
            resumen["nuevas_leaks"] += 1

    # ── Hoja Crew Performance ────────────────────────────────────────────────
    df_crew = xl.parse("Crew Performance")
    df_crew.columns = [c.strip() for c in df_crew.columns]
    for _, row in df_crew.iterrows():
        fecha_crew = safe_str(row.get("Date"))
        crew = safe_str(row.get("Crew"))
        if not fecha_crew or not crew:
            continue
        conn.execute(
            """REPLACE INTO crew_performance
               (date, crew, work_hours, pois_investigated, leaks, suspected,
                quiet, unverifiable, pipe_length_km)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (fecha_crew, crew,
             row.get("Estimated Work Hours In Field"),
             row.get("Number of POIs Investigated"),
             row.get("Number Of Leaks"),
             row.get("Number Of Suspected"),
             row.get("Number Of Quiet"),
             row.get("Number Of Unverifiable"),
             row.get("Investigated Pipe Length (KM)")),
        )

    # ── Hoja Remaining Pois ──────────────────────────────────────────────────
    df_rem = xl.parse("Remaining Pois", dtype={"ID": str})
    df_rem.columns = [c.strip() for c in df_rem.columns]
    for _, row in df_rem.iterrows():
        poi_id = safe_str(row.get("ID"))
        if not poi_id:
            continue
        conn.execute(
            """REPLACE INTO remaining_pois (id, release_date, poi_address, type_of_poi, x, y)
               VALUES (?,?,?,?,?,?)""",
            (poi_id,
             safe_str(row.get("Release Date")),
             safe_str(row.get("POI Address")),
             safe_str(row.get("Type of POI")),
             row.get("X"), row.get("Y")),
        )

    # ── Import log ───────────────────────────────────────────────────────────
    conn.execute(
        """INSERT INTO import_log
           (fecha_carga, archivo, registros_nuevos, registros_modificados,
            reparados_nuevos, discrepancias, resumen_json)
           VALUES (?,?,?,?,?,?,?)""",
        (now_iso(),
         resumen["archivo"],
         resumen["nuevos_pois"] + resumen["nuevas_leaks"],
         resumen["modificados_pois"] + resumen["modificadas_leaks"],
         resumen["reparados_nuevos"],
         resumen["discrepancias"],
         json.dumps(resumen, ensure_ascii=False)),
    )

    conn.commit()
    conn.close()
    return resumen
