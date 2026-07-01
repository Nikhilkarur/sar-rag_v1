"""
================================================================================
 AEGIS AML — FULL PIPELINE DEMO  (single file, run end-to-end)
================================================================================
Simulates the ENTIRE flow on fake data, including officer approval, and produces
the FINAL artifacts you would send to the bank / FIU-IND:

  outputs/final/sar_approved_<txn>.pdf      <- the approved, human-readable STR
  outputs/final/goaml_str_<txn>.json        <- goAML-aligned STR filing structure
  outputs/final/webhook_payload_<txn>.json  <- what we POST to the bank on approval

Stages:
  1. Ingest a mock alert      (normalize -> mask PII -> typology rules -> score)
  2. RAG index the policy PDF (chunk -> embed -> Chroma)
  3. RAG retrieve             (rules -> sub-queries -> cosine top-8)
  4. Generate SAR draft       (Groq, cites the retrieved policy sections)
  5. >>> OFFICER APPROVES <<< (simulated) -> rehydrate PII + normalize structure
  6. Build goAML STR filing + webhook envelope + approved PDF

Run from repo root:  python scripts/demo_full_pipeline.py
Requires backend/.env with GROQ_API_KEY.
================================================================================
"""
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)  # so backend/.env (Groq key) loads

os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp(prefix="chroma_demo_"))
import app.services.chroma_client as cc  # noqa: E402
cc._PERSIST_DIR = os.environ["CHROMA_PERSIST_DIR"]

from app.config import settings                                       # noqa: E402
from app.services.schema_normalizer import normalize_payload          # noqa: E402
from app.services.pii_masker import mask_payload                      # noqa: E402
from app.services.compliance_analyzer import analyze                  # noqa: E402
from app.data.schema_presets import SCHEMA_PRESETS                    # noqa: E402
from app.services import document_ingestion_service as dis            # noqa: E402
from app.services.rag_retrieval_service import retrieve_regulatory_context  # noqa: E402
from app.services.llm_agent import generate_sar_core                  # noqa: E402
from app.services import client_storage                               # noqa: E402

# Single fixed input + single fixed policy doc for the demo (avoids confusion).
POLICY_PDF = os.path.join(ROOT, "backend", "storage", "clients", "client_0", "policy.pdf")
MOCK = os.path.join(ROOT, "backend", "storage", "clients", "client_0", "alerts", "01_structuring_intlwire.json")
OUTDIR = os.path.join(ROOT, "outputs", "final")
TENANT = "client_0"   # dummy/test client (real clients start at client_1)

# --- fake but realistic reference data for the demo ------------------------
REPORTING_ENTITY = {
    "rentity_id": "FIU-RE-0042",            # FIU-assigned reporting-entity id (fake)
    "rentity_name": "Aegis Bank Limited",
    "rentity_branch": "Mumbai - Fort",
}
PRINCIPAL_OFFICER = {
    "name": "Priya Nair",
    "designation": "Principal Officer, Financial Crime Compliance",
    "email": "principal.officer@aegisbank.example",
}
# rule_name -> goAML-style suspicion indicator label
INDICATOR_MAP = {
    "Structuring / Smurfing": "STRUCTURING_BELOW_THRESHOLD",
    "Rapid Movement of Funds": "RAPID_PASS_THROUGH",
    "Large Round Number": "ROUND_AMOUNT",
    "Dormant Account Activation": "DORMANT_REACTIVATION",
    "High Risk Transaction Type": "HIGH_RISK_INSTRUMENT",
    "High Velocity": "HIGH_VELOCITY",
    "High Risk Counterparty": "HIGH_RISK_COUNTERPARTY",
    "Risk Score Threshold Exceeded": "HIGH_COMPOSITE_RISK_SCORE",
}
# transaction_type -> goAML transmode_code (representative)
TRANSMODE = {"INTERNATIONAL_WIRE": "TT", "FOREX_TRANSFER": "FX",
             "CRYPTO_PURCHASE": "VA", "HAWALA": "IVTS", "REVERSAL": "RV", "REFUND": "RF"}


def banner(n, title):
    print("\n" + "=" * 74)
    print(f"  STAGE {n}: {title}")
    print("=" * 74)


def normalize_structured(structured: dict) -> dict:
    """The 'restructure at approval' step: coerce the LLM's variable output into a
    fixed schema so the goAML mapping is deterministic regardless of the model's
    chosen shape (list-of-strings vs list-of-objects)."""
    out = {"key_indicators": [], "recommended_action": ""}
    if not isinstance(structured, dict):
        return out
    out["recommended_action"] = str(structured.get("recommended_action", "")).strip()
    for ind in structured.get("key_indicators", []) or []:
        if isinstance(ind, dict):
            out["key_indicators"].append({
                "indicator": str(ind.get("indicator", "")).strip(),
                "regulation": str(ind.get("regulation", "")).strip(),
                "description": str(ind.get("description", "")).strip(),
            })
        else:
            out["key_indicators"].append({"indicator": str(ind).strip(),
                                          "regulation": "", "description": ""})
    return out


def build_goaml_str(record, norm, triggered, structured):
    """Assemble a goAML-aligned STR filing (representative JSON, not validated XML)."""
    txn_type = norm.get("transaction_type", "")
    return {
        "report": {
            "rentity_id": REPORTING_ENTITY["rentity_id"],
            "rentity_branch": REPORTING_ENTITY["rentity_branch"],
            "submission_code": "E",                 # E = electronic
            "report_code": "STR",
            "entity_reference": record["sar_id"],
            "submission_date": record["approved_at"],
            "currency_code_local": "INR",
            "reporting_person": PRINCIPAL_OFFICER,
            "report_indicators": [INDICATOR_MAP.get(r, r) for r in triggered],
            "reason": record["narrative"],           # ground of suspicion (rehydrated)
            "action": structured["recommended_action"],
            "transaction": {
                "transactionnumber": norm.get("transaction_id"),
                "date_transaction": norm.get("transaction_timestamp"),
                "value_local": norm.get("transaction_amount"),
                "transmode_code": TRANSMODE.get(str(txn_type).upper(), "OT"),
                "transaction_description": f"{txn_type} {norm.get('transaction_direction', '')}".strip(),
                # bi-party: from = our client (payer), to = external receiver
                "t_from_my_client": {
                    "from_funds_code": "K",          # K = account
                    "from_account": {
                        "institution_name": REPORTING_ENTITY["rentity_name"],
                        "account": norm.get("account_id"),
                    },
                    "from_person": {"name": norm.get("customer_name"),
                                    "client_ref": norm.get("customer_id")},
                },
                "t_to": {
                    "to_funds_code": "K",
                    "to_account": {
                        "institution_name": norm.get("counterparty_institution"),
                        "account": norm.get("counterparty_account"),
                    },
                    "to_person": {"name": norm.get("counterparty_name")},
                },
            },
        }
    }


def render_pdf(path, record, structured, goaml):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, HRFlowable)
    from reportlab.lib import colors

    s = getSampleStyleSheet()
    H = ParagraphStyle("H", parent=s["Heading2"], fontName="Helvetica-Bold", fontSize=12,
                       textColor=colors.HexColor("#0B2E4F"), spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("B", parent=s["BodyText"], fontSize=10, leading=15, alignment=TA_JUSTIFY)
    story = [
        Paragraph("SUSPICIOUS TRANSACTION REPORT (STR)",
                  ParagraphStyle("T", parent=s["Title"], fontSize=18, textColor=colors.HexColor("#0B2E4F"))),
        Paragraph("Aegis Bank Limited &nbsp;|&nbsp; goAML filing (representative)", s["Normal"]),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#14507F"), spaceBefore=6, spaceAfter=8),
    ]
    meta = Table([
        ["SAR ID", record["sar_id"]], ["Report Code", "STR (goAML)"],
        ["Reporting Entity", f'{REPORTING_ENTITY["rentity_name"]} ({REPORTING_ENTITY["rentity_id"]})'],
        ["Transaction ID", record["transaction_id"]], ["Composite Risk Score", str(record["risk_score"])],
        ["Status", "APPROVED & FILED"],
        ["Approved By", f'{PRINCIPAL_OFFICER["name"]} — {record["approved_at"]}'],
    ], colWidths=[45 * mm, 125 * mm])
    meta.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5), ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F4F7FA"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta)

    story.append(Paragraph("1. Ground of Suspicion (Narrative)", H))
    for para in record["narrative"].split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), body)); story.append(Spacer(1, 4))

    if structured["key_indicators"]:
        story.append(Paragraph("2. Suspicion Indicators &amp; Regulatory Basis", H))
        rows = [["Indicator", "Regulation", "Description"]]
        for ind in structured["key_indicators"]:
            rows.append([ind["indicator"], ind["regulation"], ind["description"]])
        t = Table(rows, colWidths=[42 * mm, 38 * mm, 90 * mm])
        t.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2E4F")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    if structured["recommended_action"]:
        story.append(Paragraph("3. Recommended Action", H))
        story.append(Paragraph(structured["recommended_action"], body))

    tx = goaml["report"]["transaction"]
    story.append(Paragraph("4. Transaction (goAML bi-party)", H))
    pt = Table([
        ["Amount (local)", f'INR {tx["value_local"]:,}'], ["Mode (transmode_code)", tx["transmode_code"]],
        ["From (my client)", f'{tx["t_from_my_client"]["from_person"]["name"]} / {tx["t_from_my_client"]["from_account"]["account"]}'],
        ["To (receiver)", f'{tx["t_to"]["to_person"]["name"]} @ {tx["t_to"]["to_account"]["institution_name"]}'],
        ["Indicators", ", ".join(goaml["report"]["report_indicators"])],
    ], colWidths=[45 * mm, 125 * mm])
    pt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9), ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(pt)

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D6DEE6")))
    story.append(Paragraph(f'Filed to FIU-IND via goAML by {PRINCIPAL_OFFICER["name"]}. '
                           "Representative demo artifact on synthetic data.",
                           ParagraphStyle("F", parent=s["Normal"], fontSize=8, textColor=colors.grey)))
    SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm).build(story)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    print("\n" + "#" * 74 + "\n#  AEGIS AML — FULL PIPELINE DEMO (synthetic data)\n" + "#" * 74)

    # ---- STAGE 1: ingest ----
    banner(1, "Ingest mock alert (normalize -> mask PII -> rules -> score)")
    _rec = json.load(open(MOCK, encoding="utf-8"))
    raw = _rec.get("raw_payload", _rec)
    preset = SCHEMA_PRESETS["STANDARD_FINTECH"]
    norm = normalize_payload(raw, preset["field_map"])
    masked, token_map = mask_payload(norm, preset["pii_fields"])
    triggered = [r for r in analyze(norm) if r["triggered"]]
    base = max(0, min(100, int(float(norm.get("risk_score") or 0))))
    score = min(100, base + sum(20 if r["confidence"] == "HIGH" else 10 for r in triggered))
    print("Transaction:", norm.get("transaction_type"), "INR", f'{int(norm.get("transaction_amount")):,}')
    print("Triggered rules:", ", ".join(r["rule_name"] for r in triggered))
    print("Composite risk score:", score, "->", "SAR REQUIRED" if score >= 75 else "clean")
    print("PII masked for LLM. Example:", list(token_map.items())[0])

    # ---- STAGE 2: index ----
    banner(2, "RAG index the policy PDF (chunk -> embed -> Chroma)")
    chunks = dis.build_chunks(POLICY_PDF, "Aegis Bank AML/CFT Policy",
                              "aegis_bank_aml_policy.pdf", "aegis-policy-1")
    dis.index_document(TENANT, chunks)
    print(f"Indexed {len(chunks)} chunks from {os.path.basename(POLICY_PDF)} (encoder: {settings.LOCAL_EMBEDDING_MODEL}).")

    # ---- STAGE 3: retrieve ----
    banner(3, "RAG retrieve (rules -> sub-queries -> cosine top-8)")
    compliance_results = [{"rule_name": r["rule_name"], "triggered": True} for r in triggered]
    hits = retrieve_regulatory_context(TENANT, masked, compliance_results)
    for i, h in enumerate(hits, 1):
        print(f"  {i}. [{h['metadata']['section_heading']}]  dist={h['distance']:.3f}")

    # ---- STAGE 4: generate ----
    banner(4, f"Generate SAR draft (Groq {settings.GROQ_MODEL}, cites policy)")
    out = generate_sar_core(masked, score, settings.GROQ_MODEL, retrieved_chunks=hits)
    print(f"Draft generated. tokens: prompt={out['prompt_tokens']} completion={out['completion_tokens']} "
          f"latency={out['latency_ms']}ms")
    print("Cited sections:", ", ".join(c["section"] for c in out["used_chunks"][:4]), "...")

    # ---- STAGE 5: OFFICER APPROVES (simulated) ----
    banner(5, ">>> OFFICER APPROVES <<<  (rehydrate PII + normalize structure)")
    rehydrated = out["narrative"]
    for token, original in token_map.items():
        rehydrated = rehydrated.replace(token, str(original))
    structured = normalize_structured(out["structured"])  # the 'restructure on approve' step
    print(f"Approved by: {PRINCIPAL_OFFICER['name']} ({PRINCIPAL_OFFICER['designation']})")
    print("PII rehydrated to real values for the bank-facing filing.")
    print(f"Structure normalized -> {len(structured['key_indicators'])} indicators in fixed schema.")

    record = {
        "sar_id": "SAR-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
        "transaction_id": norm.get("transaction_id"),
        "risk_score": score,
        "approved_by": PRINCIPAL_OFFICER["name"],
        "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "narrative": rehydrated,
    }

    # ---- STAGE 6: final artifacts ----
    banner(6, "Build goAML STR filing + webhook envelope + approved PDF")
    goaml = build_goaml_str(record, norm, [r["rule_name"] for r in triggered], structured)
    txn = norm.get("transaction_id")
    # approved SAR PDF -> client_0's unified folder (same place the live path writes);
    # the goAML + webhook JSON stay in outputs/final/ as demo artifacts.
    pdf_path = client_storage.sar_path(TENANT, record["sar_id"])
    render_pdf(pdf_path, record, structured, goaml)
    pdf_sha = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest()

    webhook = {
        "event": "sar.approved",
        "sar_id": record["sar_id"],
        "tenant": REPORTING_ENTITY["rentity_name"],
        "approved_by": record["approved_by"],
        "approved_at": record["approved_at"],
        "goaml_str": goaml,
        "pdf_url": f"https://files.aegis.example/sar/{record['sar_id']}.pdf?token=DEMO&expires=...",
        "pdf_sha256": pdf_sha,
    }

    goaml_path = os.path.join(OUTDIR, f"goaml_str_{txn}.json")
    wh_path = os.path.join(OUTDIR, f"webhook_payload_{txn}.json")
    json.dump(goaml, open(goaml_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(webhook, open(wh_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print("FINAL ARTIFACTS:")
    print("  approved PDF :", pdf_path, "(client_0 unified folder)")
    print("  goAML STR    :", goaml_path)
    print("  webhook body :", wh_path, f"(pdf sha256={pdf_sha[:16]}...)")
    print("\n----- FINAL goAML STR STRUCTURE (what gets filed) -----\n")
    print(json.dumps(goaml, indent=2, ensure_ascii=False))
    print("\nDEMO COMPLETE.")


if __name__ == "__main__":
    main()
