import unicodedata


def tipo_red(leak_type: str) -> str:
    lt = leak_type.lower()
    lt = unicodedata.normalize("NFD", lt)
    lt = "".join(c for c in lt if unicodedata.category(c) != "Mn")
    if any(k in lt for k in ("main", "hidrante", "valvula principal", "matriz")):
        return "red_principal"
    elif any(k in lt for k in ("service", "acometida", "collarin")):
        return "red_secundaria"
    elif any(k in lt for k in ("customer", "interna", "medidor", "predio")):
        return "customer_side"
    else:
        return "red_secundaria"  # default conservador


def categoria_alerta(tipo: str, dias: int, umbrales: dict) -> str:
    u = umbrales.get(tipo, umbrales.get("red_secundaria", {}))
    if dias >= u.get("critica", 9999):
        return "critica"
    elif dias >= u.get("urgente", 9999):
        return "urgente"
    elif dias >= u.get("atencion", 9999):
        return "atencion"
    else:
        return "normal"


COLORES_ALERTA = {
    "normal": ("🟢", "#28a745"),
    "atencion": ("🟡", "#ffc107"),
    "urgente": ("🟠", "#fd7e14"),
    "critica": ("🔴", "#dc3545"),
}


def color_alerta(categoria: str) -> tuple:
    return COLORES_ALERTA.get(categoria, ("⚪", "#6c757d"))
