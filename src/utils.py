import os
import yaml
from datetime import datetime, date
import pandas as pd

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
_config_cache = None


def load_config():
    global _config_cache
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Aplicar overrides de app_config en BD
    try:
        from src.db import get_connection
        conn = get_connection()
        rows = conn.execute("SELECT clave, valor FROM app_config").fetchall()
        conn.close()
        for row in rows:
            keys = row["clave"].split(".")
            d = config
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            # Intentar parsear como yaml (para números, listas, etc.)
            try:
                d[keys[-1]] = yaml.safe_load(row["valor"])
            except Exception:
                d[keys[-1]] = row["valor"]
    except Exception:
        pass

    _config_cache = config
    return config


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def parse_excel_date(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date)):
        return value if isinstance(value, datetime) else datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.split(".")[0], fmt)
            except ValueError:
                continue
    return None


def dias_desde(fecha):
    if fecha is None:
        return 0
    if isinstance(fecha, str):
        fecha = parse_excel_date(fecha)
    if fecha is None:
        return 0
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    return (date.today() - fecha).days


def safe_str(x):
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()
