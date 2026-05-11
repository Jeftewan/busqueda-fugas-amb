import unicodedata
import re
from src.utils import safe_str, load_config


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def clasificar_palabras(comments: str, palabras_clave: dict) -> str:
    if not comments:
        return "NEUTRA"
    texto = _normalizar(safe_str(comments))
    for palabra in palabras_clave.get("alta", []):
        if _normalizar(str(palabra)) in texto:
            return "ALTA"
    for palabra in palabras_clave.get("media", []):
        if _normalizar(str(palabra)) in texto:
            return "MEDIA"
    for palabra in palabras_clave.get("baja", []):
        if _normalizar(str(palabra)) in texto:
            return "BAJA"
    return "NEUTRA"


def calcular_score(leak_dict: dict, config: dict) -> int:
    pesos = config["prioridad"]["pesos"]
    palabras_clave = config["palabras_clave"]

    # Override manual
    manual = safe_str(leak_dict.get("prioridad_manual", ""))
    if manual in ("ALTA", "MEDIA", "BAJA"):
        return {"ALTA": 100, "MEDIA": 50, "BAJA": 10}[manual]

    score = 0

    # Palabras clave en comments
    comments = safe_str(leak_dict.get("comments_original") or leak_dict.get("Comments", ""))
    cat_palabras = clasificar_palabras(comments, palabras_clave)
    if cat_palabras == "ALTA":
        score += pesos["palabra_alta"]
    elif cat_palabras == "MEDIA":
        score += pesos["palabra_media"]
    elif cat_palabras == "BAJA":
        score += pesos["palabra_baja"]

    # Leak type
    leak_type = _normalizar(safe_str(leak_dict.get("leak_type") or leak_dict.get("Leak Type", "")))
    if "main" in leak_type or "hidrante" in leak_type or "valvula principal" in leak_type:
        score += pesos["main"]
    elif "service" in leak_type or "acometida" in leak_type:
        score += pesos["service"]
    elif "customer" in leak_type or "interna" in leak_type:
        score += pesos["customer_side"]
    else:
        score += pesos["other"]

    # Visible
    visible = safe_str(leak_dict.get("visible") or leak_dict.get("Visible", "")).lower()
    if visible == "yes":
        score += pesos["visible"]

    # Días sin reparar
    dias = int(leak_dict.get("dias_sin_reparar") or 0)
    score += min(dias, pesos["cap_dias"]) * pesos["dia_pendiente"]

    return score


def score_a_categoria(score: int, umbrales: dict) -> str:
    if score >= umbrales["alta"]:
        return "ALTA"
    elif score >= umbrales["media"]:
        return "MEDIA"
    else:
        return "BAJA"


def motivo_prioridad(leak_dict: dict, config: dict) -> str:
    pesos = config["prioridad"]["pesos"]
    palabras_clave = config["palabras_clave"]
    umbrales = config["prioridad"]["umbrales"]

    manual = safe_str(leak_dict.get("prioridad_manual", ""))
    if manual in ("ALTA", "MEDIA", "BAJA"):
        return f"{manual} (override manual del usuario)"

    partes = []
    comments = safe_str(leak_dict.get("comments_original") or leak_dict.get("Comments", ""))
    cat = clasificar_palabras(comments, palabras_clave)
    texto_norm = _normalizar(comments)

    palabra_encontrada = None
    lista = palabras_clave.get(cat.lower(), []) if cat != "NEUTRA" else []
    for p in lista:
        if _normalizar(str(p)) in texto_norm:
            palabra_encontrada = p
            break

    if cat == "ALTA":
        partes.append(f"'{palabra_encontrada}' (+{pesos['palabra_alta']})")
    elif cat == "MEDIA":
        partes.append(f"'{palabra_encontrada}' (+{pesos['palabra_media']})")
    elif cat == "BAJA":
        partes.append(f"'{palabra_encontrada}' ({pesos['palabra_baja']})")

    leak_type = _normalizar(safe_str(leak_dict.get("leak_type") or leak_dict.get("Leak Type", "")))
    if "main" in leak_type:
        partes.append(f"Main (+{pesos['main']})")
    elif "service" in leak_type:
        partes.append(f"Service (+{pesos['service']})")
    elif "customer" in leak_type:
        partes.append(f"Customer-side ({pesos['customer_side']})")

    dias = int(leak_dict.get("dias_sin_reparar") or 0)
    dias_score = min(dias, pesos["cap_dias"]) * pesos["dia_pendiente"]
    if dias_score > 0:
        partes.append(f"{dias} días (+{dias_score})")

    score = calcular_score(leak_dict, config)
    cat_final = score_a_categoria(score, umbrales)
    return f"{cat_final}: {' + '.join(partes)} = {score}" if partes else f"{cat_final}: score={score}"


def recalcular_todas(config=None):
    from src.db import get_connection
    from src.alerts import categoria_alerta, tipo_red
    from src.utils import dias_desde

    if config is None:
        config = load_config()

    conn = get_connection()
    leaks = conn.execute("SELECT l.*, p.date_detected, p.visible FROM leaks l LEFT JOIN pois p ON l.poi_id = p.id").fetchall()
    updated = 0
    for row in leaks:
        d = dict(row)
        dias = dias_desde(d.get("date_detected"))
        d["dias_sin_reparar"] = dias
        score = calcular_score(d, config)
        cat = score_a_categoria(score, config["prioridad"]["umbrales"])
        motivo = motivo_prioridad(d, config)
        prioridad_final = d.get("prioridad_manual") if d.get("prioridad_manual") in ("ALTA", "MEDIA", "BAJA") else cat
        tipo = tipo_red(safe_str(d.get("leak_type", "")))
        alerta = categoria_alerta(tipo, dias, config["umbrales_antiguedad"])
        conn.execute(
            """UPDATE leaks SET prioridad_auto=?, score_prioridad=?, motivo_prioridad=?,
               prioridad_final=?, alerta_antiguedad=?, dias_sin_reparar=? WHERE leak_id=?""",
            (cat, score, motivo, prioridad_final, alerta, dias, d["leak_id"]),
        )
        updated += 1
    conn.commit()
    conn.close()
    return updated
