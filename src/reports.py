import io
from datetime import date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                 Spacer, HRFlowable, PageBreak)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm


def _encabezado(elements, styles, titulo: str):
    elements.append(Paragraph("💧 Seguimiento de Fugas — Acueducto", styles["titulo_doc"]))
    elements.append(Paragraph(titulo, styles["subtitulo_doc"]))
    elements.append(Paragraph(f"Generado el {date.today().strftime('%d/%m/%Y')}", styles["Normal"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0d6efd")))
    elements.append(Spacer(1, 0.4 * cm))


def _make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("titulo_doc", fontSize=16, fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#0d6efd"), spaceAfter=4))
    styles.add(ParagraphStyle("subtitulo_doc", fontSize=12, fontName="Helvetica",
                               textColor=colors.HexColor("#495057"), spaceAfter=4))
    styles.add(ParagraphStyle("cell", fontSize=7, fontName="Helvetica", leading=9))
    return styles


def generar_pdf_fugas(leak_ids: list, tipo: str) -> bytes:
    from src.models import get_leak_by_id

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                             leftMargin=MARGIN, rightMargin=MARGIN,
                             topMargin=MARGIN, bottomMargin=MARGIN)
    styles = _make_styles()
    elements = []

    titulo = f"Solicitud de Orden de Trabajo" if tipo == "OT" else "Recordatorio de Fugas Pendientes"
    _encabezado(elements, styles, titulo)

    # Tabla de fugas
    headers = ["Leak ID", "Dirección", "Coords", "Tipo", "Sub-tipo",
               "Días", "Prioridad", "Alerta", "Comentarios"]
    data = [headers]
    for lid in leak_ids:
        leak = get_leak_by_id(int(lid))
        if not leak:
            continue
        coords = f"({leak.get('actual_y', ''):.4f}, {leak.get('actual_x', ''):.4f})" if leak.get("actual_y") else ""
        comentario = str(leak.get("comments_original") or "")[:80]
        notas = str(leak.get("notas_internas") or "")
        texto_completo = comentario + (f" | Notas: {notas}" if notas else "")
        data.append([
            str(leak.get("leak_id", "")),
            Paragraph(str(leak.get("address", ""))[:60], styles["cell"]),
            coords,
            str(leak.get("leak_type", "")),
            str(leak.get("leak_sub_type", "")),
            str(leak.get("dias_sin_reparar", "")),
            str(leak.get("prioridad_final", "")),
            str(leak.get("alerta_antiguedad", "")),
            Paragraph(texto_completo[:100], styles["cell"]),
        ])

    col_widths = [1.5*cm, 5*cm, 3*cm, 2.5*cm, 2.5*cm, 1.2*cm, 1.8*cm, 1.8*cm, 5*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dee2e6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (5, 0), (5, -1), "CENTER"),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5 * cm))

    # Pie
    total = len(leak_ids)
    elements.append(Paragraph(f"Total de fugas: {total}", styles["Normal"]))

    doc.build(elements)
    return buf.getvalue()


def generar_reporte_ejecutivo(kpis: dict, df_top) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=MARGIN, rightMargin=MARGIN,
                             topMargin=MARGIN, bottomMargin=MARGIN)
    styles = _make_styles()
    elements = []

    _encabezado(elements, styles, "Reporte Ejecutivo de Fugas")

    # KPIs
    kpi_data = [
        ["Indicador", "Valor"],
        ["Total POIs investigados", kpis["total_pois"]],
        ["Total fugas detectadas", kpis["total_leaks"]],
        ["Fugas reparadas", kpis["reparadas"]],
        ["Fugas pendientes", kpis["pendientes"]],
        ["% de reparación", f"{kpis['pct_reparacion']}%"],
        ["Días promedio pendiente", kpis["avg_dias_pendiente"]],
        ["Reparadas en últimos 30 días", kpis["reparadas_30d"]],
    ]
    t_kpi = Table(kpi_data, colWidths=[10*cm, 5*cm])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#e9ecef")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ]))
    elements.append(t_kpi)
    elements.append(PageBreak())

    # Top criticas
    _encabezado(elements, styles, "Top Fugas Críticas Pendientes")
    if not df_top.empty:
        top_data = [["Leak ID", "Dirección", "Tipo", "Días", "Prioridad", "Alerta", "Score"]]
        for _, r in df_top.iterrows():
            top_data.append([
                str(r.get("leak_id", "")),
                Paragraph(str(r.get("address", ""))[:50], styles["cell"]),
                str(r.get("leak_type", "")),
                str(r.get("dias_sin_reparar", "")),
                str(r.get("prioridad_final", "")),
                str(r.get("alerta_antiguedad", "")),
                str(r.get("score_prioridad", "")),
            ])
        t_top = Table(top_data, colWidths=[1.5*cm, 6*cm, 2.5*cm, 1.2*cm, 2*cm, 1.8*cm, 1.5*cm])
        t_top.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dc3545")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dee2e6")),
        ]))
        elements.append(t_top)

    doc.build(elements)
    return buf.getvalue()
