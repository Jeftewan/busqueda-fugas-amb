import pandas as pd
from src.db import get_connection
from src.utils import now_iso


def get_all_leaks(filtros: dict = None) -> pd.DataFrame:
    conn = get_connection()
    sql = """
        SELECT l.leak_id, l.poi_id, p.address, p.actual_x, p.actual_y,
               p.date_detected, p.crew, l.leak_type, l.leak_sub_type,
               l.repaired, l.repair_date_excel, l.comments_original,
               l.prioridad_auto, l.prioridad_manual, l.prioridad_final,
               l.score_prioridad, l.motivo_prioridad, l.estado_interno,
               l.ot_estado, l.ot_numero, l.ot_fecha_generacion,
               l.ot_fecha_finalizacion, l.ot_fecha_solicitud, l.ot_email_id,
               l.notas_internas,
               l.alerta_antiguedad, l.dias_sin_reparar, l.discrepancia_excel,
               p.investigation_result, p.visible
        FROM leaks l
        LEFT JOIN pois p ON l.poi_id = p.id
    """
    conditions = []
    params = []

    if filtros:
        if filtros.get("solo_no_reparadas"):
            conditions.append("l.repaired != 'Yes'")
        if filtros.get("prioridad"):
            placeholders = ",".join("?" * len(filtros["prioridad"]))
            conditions.append(f"l.prioridad_final IN ({placeholders})")
            params.extend(filtros["prioridad"])
        if filtros.get("estado_interno"):
            placeholders = ",".join("?" * len(filtros["estado_interno"]))
            conditions.append(f"l.estado_interno IN ({placeholders})")
            params.extend(filtros["estado_interno"])
        if filtros.get("cuadrilla"):
            placeholders = ",".join("?" * len(filtros["cuadrilla"]))
            conditions.append(f"p.crew IN ({placeholders})")
            params.extend(filtros["cuadrilla"])
        if filtros.get("leak_type"):
            placeholders = ",".join("?" * len(filtros["leak_type"]))
            conditions.append(f"l.leak_type IN ({placeholders})")
            params.extend(filtros["leak_type"])
        if filtros.get("alerta"):
            placeholders = ",".join("?" * len(filtros["alerta"]))
            conditions.append(f"l.alerta_antiguedad IN ({placeholders})")
            params.extend(filtros["alerta"])
        if filtros.get("ot_estado"):
            placeholders = ",".join("?" * len(filtros["ot_estado"]))
            conditions.append(f"l.ot_estado IN ({placeholders})")
            params.extend(filtros["ot_estado"])
        if filtros.get("dias_min") is not None:
            conditions.append("l.dias_sin_reparar >= ?")
            params.append(filtros["dias_min"])
        if filtros.get("dias_max") is not None:
            conditions.append("l.dias_sin_reparar <= ?")
            params.append(filtros["dias_max"])
        if filtros.get("busqueda"):
            conditions.append("(p.address LIKE ? OR CAST(l.leak_id AS TEXT) LIKE ? OR CAST(l.poi_id AS TEXT) LIKE ?)")
            b = f"%{filtros['busqueda']}%"
            params.extend([b, b, b])

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY l.score_prioridad DESC, l.dias_sin_reparar DESC"
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def get_kpis() -> dict:
    conn = get_connection()
    total_pois = conn.execute("SELECT COUNT(*) FROM pois").fetchone()[0]
    total_leaks = conn.execute("SELECT COUNT(*) FROM leaks").fetchone()[0]
    reparadas = conn.execute("SELECT COUNT(*) FROM leaks WHERE repaired='Yes'").fetchone()[0]
    pendientes = total_leaks - reparadas
    pct = round(reparadas / total_leaks * 100, 1) if total_leaks else 0

    # Tiempo promedio reparación
    avg_dias_row = conn.execute(
        "SELECT AVG(dias_sin_reparar) FROM leaks WHERE repaired!='Yes'"
    ).fetchone()[0]
    avg_dias = round(avg_dias_row, 1) if avg_dias_row else 0

    # Velocidad últimos 30 días
    desde_30 = conn.execute(
        "SELECT COUNT(*) FROM leaks WHERE repair_date_excel >= date('now','-30 days')"
    ).fetchone()[0]

    conn.close()
    return {
        "total_pois": total_pois,
        "total_leaks": total_leaks,
        "reparadas": reparadas,
        "pendientes": pendientes,
        "pct_reparacion": pct,
        "avg_dias_pendiente": avg_dias,
        "reparadas_30d": desde_30,
    }


def get_distribucion_por_prioridad() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT prioridad_final as prioridad, COUNT(*) as total FROM leaks GROUP BY prioridad_final",
        conn
    )
    conn.close()
    return df


def get_distribucion_por_alerta() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT alerta_antiguedad as alerta, COUNT(*) as total FROM leaks WHERE repaired!='Yes' GROUP BY alerta_antiguedad",
        conn
    )
    conn.close()
    return df


def get_distribucion_por_cuadrilla() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT p.crew as cuadrilla, COUNT(l.leak_id) as fugas
           FROM leaks l JOIN pois p ON l.poi_id=p.id
           GROUP BY p.crew""",
        conn
    )
    conn.close()
    return df


def get_tendencia_mensual() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT strftime('%Y-%m', p.date_detected) as mes,
                  COUNT(l.leak_id) as detectadas,
                  SUM(CASE WHEN l.repaired='Yes' THEN 1 ELSE 0 END) as reparadas
           FROM leaks l JOIN pois p ON l.poi_id=p.id
           WHERE p.date_detected IS NOT NULL
           GROUP BY mes ORDER BY mes""",
        conn
    )
    conn.close()
    return df


def get_top_criticas(n: int = 10) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        f"""SELECT l.leak_id, p.address, l.leak_type, l.dias_sin_reparar,
                   l.prioridad_final, l.alerta_antiguedad, l.score_prioridad,
                   l.ot_estado, l.comments_original
            FROM leaks l LEFT JOIN pois p ON l.poi_id=p.id
            WHERE l.repaired!='Yes'
            ORDER BY l.score_prioridad DESC, l.dias_sin_reparar DESC
            LIMIT {n}""",
        conn
    )
    conn.close()
    return df


def get_crew_performance() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM crew_performance ORDER BY date DESC", conn)
    conn.close()
    return df


def get_remaining_pois() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM remaining_pois", conn)
    conn.close()
    return df


def get_import_log() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM import_log ORDER BY id DESC LIMIT 20", conn)
    conn.close()
    return df


def get_leak_by_id(leak_id: int) -> dict:
    conn = get_connection()
    row = conn.execute(
        """SELECT l.*, p.address, p.actual_x, p.actual_y, p.date_detected,
                  p.crew, p.visible, p.investigation_result, p.comments as poi_comments
           FROM leaks l LEFT JOIN pois p ON l.poi_id=p.id
           WHERE l.leak_id=?""",
        (leak_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_status_history(leak_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM status_history WHERE leak_id=? ORDER BY fecha DESC",
        conn, params=(leak_id,)
    )
    conn.close()
    return df


def update_leak_internal(leak_id: int, campos: dict, origen: str = "usuario"):
    conn = get_connection()
    existing = conn.execute("SELECT * FROM leaks WHERE leak_id=?", (leak_id,)).fetchone()
    if not existing:
        conn.close()
        return

    for campo, nuevo_val in campos.items():
        anterior = existing[campo] if campo in existing.keys() else None
        conn.execute(
            """INSERT INTO status_history (leak_id, campo_modificado, valor_anterior,
               valor_nuevo, fecha, origen) VALUES (?,?,?,?,?,?)""",
            (leak_id, campo, str(anterior), str(nuevo_val), now_iso(), origen)
        )

    set_clause = ", ".join(f"{k}=?" for k in campos)
    vals = list(campos.values()) + [now_iso(), leak_id]
    conn.execute(f"UPDATE leaks SET {set_clause}, last_updated_at=? WHERE leak_id=?", vals)
    conn.commit()
    conn.close()


def mark_leaks_solicitadas(leak_ids: list, email_id: int) -> int:
    """Marca las fugas como 'Solicitada' tras envío exitoso de correo OT.

    Solo actualiza fugas cuyo ot_estado actual es 'Pendiente por generar' o NULL,
    para no degradar las que ya están 'Generada' o 'Finalizada'. Registra cada
    cambio en status_history vía update_leak_internal.

    Retorna cuántas fugas fueron efectivamente actualizadas.
    """
    if not leak_ids:
        return 0
    actualizadas = 0
    for lid in leak_ids:
        leak = get_leak_by_id(int(lid))
        if not leak:
            continue
        estado_actual = leak.get("ot_estado")
        if estado_actual not in (None, "", "Pendiente por generar"):
            continue
        update_leak_internal(
            int(lid),
            {
                "ot_estado": "Solicitada",
                "ot_fecha_solicitud": now_iso(),
                "ot_email_id": int(email_id),
            },
            origen="correo_ot",
        )
        actualizadas += 1
    return actualizadas


def get_email_templates() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM email_templates", conn)
    conn.close()
    return df


def get_emails_sent() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, fecha_envio, destinatario, asunto, tipo, leak_ids, enviado_ok FROM emails_sent ORDER BY id DESC", conn)
    conn.close()
    return df
