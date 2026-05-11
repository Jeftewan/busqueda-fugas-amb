import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fugas.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS pois (
        id TEXT PRIMARY KEY,
        address TEXT,
        actual_x REAL,
        actual_y REAL,
        date_detected TEXT,
        investigation_result TEXT,
        crew TEXT,
        comments TEXT,
        pipe_type TEXT,
        visible TEXT,
        first_seen_at TEXT,
        last_updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS leaks (
        leak_id INTEGER PRIMARY KEY,
        poi_id TEXT REFERENCES pois(id),
        leak_type TEXT,
        leak_sub_type TEXT,
        repaired TEXT,
        repair_date_excel TEXT,
        comments_original TEXT,
        prioridad_auto TEXT,
        prioridad_manual TEXT,
        prioridad_final TEXT,
        score_prioridad INTEGER,
        motivo_prioridad TEXT,
        estado_interno TEXT DEFAULT 'Detectada',
        ot_estado TEXT DEFAULT 'Pendiente por generar',
        ot_numero TEXT,
        ot_fecha_generacion TEXT,
        ot_fecha_finalizacion TEXT,
        notas_internas TEXT,
        alerta_antiguedad TEXT,
        dias_sin_reparar INTEGER,
        discrepancia_excel INTEGER DEFAULT 0,
        first_seen_at TEXT,
        last_updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS crew_performance (
        date TEXT,
        crew TEXT,
        work_hours REAL,
        pois_investigated INTEGER,
        leaks INTEGER,
        suspected INTEGER,
        quiet INTEGER,
        unverifiable INTEGER,
        pipe_length_km REAL,
        PRIMARY KEY (date, crew)
    );

    CREATE TABLE IF NOT EXISTS remaining_pois (
        id TEXT PRIMARY KEY,
        release_date TEXT,
        poi_address TEXT,
        type_of_poi TEXT,
        x REAL,
        y REAL
    );

    CREATE TABLE IF NOT EXISTS status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        leak_id INTEGER REFERENCES leaks(leak_id),
        campo_modificado TEXT,
        valor_anterior TEXT,
        valor_nuevo TEXT,
        fecha TEXT,
        origen TEXT
    );

    CREATE TABLE IF NOT EXISTS emails_sent (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_envio TEXT,
        destinatario TEXT,
        asunto TEXT,
        tipo TEXT,
        leak_ids TEXT,
        cuerpo_html TEXT,
        pdf_adjunto BLOB,
        enviado_ok INTEGER,
        error_mensaje TEXT
    );

    CREATE TABLE IF NOT EXISTS email_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        tipo TEXT,
        asunto TEXT,
        cuerpo_html TEXT,
        es_default INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS import_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_carga TEXT,
        archivo TEXT,
        registros_nuevos INTEGER,
        registros_modificados INTEGER,
        reparados_nuevos INTEGER,
        discrepancias INTEGER,
        resumen_json TEXT
    );

    CREATE TABLE IF NOT EXISTS app_config (
        clave TEXT PRIMARY KEY,
        valor TEXT
    );
    """)

    # Migración: columnas para seguimiento de solicitud OT por correo
    c.execute("PRAGMA table_info(leaks)")
    cols = {r[1] for r in c.fetchall()}
    if "ot_fecha_solicitud" not in cols:
        c.execute("ALTER TABLE leaks ADD COLUMN ot_fecha_solicitud TEXT")
    if "ot_email_id" not in cols:
        c.execute("ALTER TABLE leaks ADD COLUMN ot_email_id INTEGER")

    # Pre-cargar plantillas de correo si no existen
    c.execute("SELECT COUNT(*) FROM email_templates")
    if c.fetchone()[0] == 0:
        plantillas = [
            (
                "Solicitud de OT",
                "OT",
                "Solicitud de Orden de Trabajo — {n_fugas} fugas pendientes ({fecha})",
                """<html><body>
<p>Estimado equipo,</p>
<p>Se solicita la generación de <strong>{n_fugas} órdenes de trabajo</strong> para las siguientes fugas detectadas:</p>
{lista_fugas}
<p>Se adjunta informe detallado en PDF.</p>
<p>Fecha: {fecha}</p>
<p>Sistema de Seguimiento de Fugas — Acueducto</p>
</body></html>""",
                1,
            ),
            (
                "Recordatorio de pendientes",
                "Recordatorio",
                "Recordatorio — {n_fugas} fugas sin reparar ({fecha})",
                """<html><body>
<p>Estimado equipo,</p>
<p>Le recordamos que hay <strong>{n_fugas} fugas</strong> pendientes de reparación:</p>
{lista_fugas}
<p>Se adjunta informe detallado en PDF.</p>
<p>Fecha: {fecha}</p>
<p>Sistema de Seguimiento de Fugas — Acueducto</p>
</body></html>""",
                0,
            ),
        ]
        c.executemany(
            "INSERT OR IGNORE INTO email_templates (nombre, tipo, asunto, cuerpo_html, es_default) VALUES (?,?,?,?,?)",
            plantillas,
        )

    conn.commit()
    conn.close()
