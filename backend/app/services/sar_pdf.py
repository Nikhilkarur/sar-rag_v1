"""
Render an approved SAR to a human-readable PDF (the bank-facing report).

The PDF carries REHYDRATED (real) PII — it is the actual FIU filing — so we deliberately do NOT
persist it to Aegis's disk. It is rendered in memory: the bytes are base64'd into the approval
webhook (the bank keeps its own copy) and re-rendered on demand for the officer's own download.
Cells are wrapped in Paragraph so long text wraps instead of clipping.
"""
from io import BytesIO
from typing import Any, Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)
from reportlab.lib import colors


def _normalize_indicators(structured: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for ind in (structured or {}).get("key_indicators", []) or []:
        if isinstance(ind, dict):
            out.append({"indicator": str(ind.get("indicator", "")),
                        "regulation": str(ind.get("regulation", "")),
                        "description": str(ind.get("description", ""))})
        else:
            out.append({"indicator": str(ind), "regulation": "", "description": ""})
    return out


def render_sar_pdf(sar_id: str, alert, draft, goaml: Dict[str, Any],
                   officer_name: str, approved_at: str) -> bytes:
    """Render the SAR to PDF and return the bytes. Never touches disk (real-PII filing)."""
    buffer = BytesIO()

    s = getSampleStyleSheet()
    H = ParagraphStyle("H", parent=s["Heading2"], fontName="Helvetica-Bold", fontSize=12,
                       textColor=colors.HexColor("#0B2E4F"), spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("B", parent=s["BodyText"], fontSize=10, leading=15, alignment=TA_JUSTIFY)
    cell = ParagraphStyle("C", parent=s["BodyText"], fontSize=8.5, leading=11)
    cellh = ParagraphStyle("CH", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)

    structured = draft.draft_structured if isinstance(draft.draft_structured, dict) else {}
    narrative = draft.approved_text or draft.rehydrated_text or draft.draft_text or ""
    report = goaml.get("report", {})
    tx = report.get("transaction", {})

    story = [
        Paragraph("SUSPICIOUS TRANSACTION REPORT (STR)",
                  ParagraphStyle("T", parent=s["Title"], fontSize=18, textColor=colors.HexColor("#0B2E4F"))),
        Paragraph(f"{report.get('rentity_name') or 'Aegis tenant'} &nbsp;|&nbsp; goAML filing", s["Normal"]),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#14507F"), spaceBefore=6, spaceAfter=8),
    ]
    meta = Table([
        ["SAR ID", str(sar_id)], ["Report Code", "STR (goAML)"],
        ["Reporting Entity", str(report.get("rentity_id"))],
        ["Transaction ID", str(tx.get("transactionnumber"))],
        ["Risk Score", str(alert.risk_score)],
        ["Status", "APPROVED & FILED"],
        ["Approved By", f"{officer_name} - {approved_at}"],
    ], colWidths=[42 * mm, 128 * mm])
    meta.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5), ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F4F7FA"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta)

    story.append(Paragraph("1. Ground of Suspicion (Narrative)", H))
    for para in narrative.split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), body)); story.append(Spacer(1, 4))

    indicators = _normalize_indicators(structured)
    if indicators:
        story.append(Paragraph("2. Suspicion Indicators &amp; Regulatory Basis", H))
        # cells wrapped in Paragraph -> text wraps instead of clipping
        rows = [[Paragraph("Indicator", cellh), Paragraph("Regulation", cellh), Paragraph("Description", cellh)]]
        for ind in indicators:
            rows.append([Paragraph(ind["indicator"], cell), Paragraph(ind["regulation"], cell),
                         Paragraph(ind["description"], cell)])
        t = Table(rows, colWidths=[42 * mm, 38 * mm, 90 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2E4F")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    action = structured.get("recommended_action") if isinstance(structured, dict) else None
    if action:
        story.append(Paragraph("3. Recommended Action", H))
        story.append(Paragraph(str(action), body))

    story.append(Paragraph("4. Transaction (goAML bi-party)", H))
    frm = tx.get("t_from_my_client", {}); to = tx.get("t_to", {})
    pt = Table([
        ["Amount (local)", f"{report.get('currency_code_local','INR')} {tx.get('value_local')}"],
        ["Mode (transmode_code)", str(tx.get("transmode_code"))],
        ["From (my client)", f"{(frm.get('from_person') or {}).get('name')} / {(frm.get('from_account') or {}).get('account')}"],
        ["To (receiver)", f"{(to.get('to_person') or {}).get('name')} @ {(to.get('to_account') or {}).get('institution_name')}"],
        ["Indicators", ", ".join(report.get("report_indicators", []))],
    ], colWidths=[42 * mm, 128 * mm])
    pt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9), ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(pt)

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D6DEE6")))
    story.append(Paragraph(f"Filed to FIU-IND via goAML by {officer_name}.",
                           ParagraphStyle("F", parent=s["Normal"], fontSize=8, textColor=colors.grey)))

    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm).build(story)
    return buffer.getvalue()
