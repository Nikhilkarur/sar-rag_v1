"""
Build the Meridian Bank AML/CFT policy PDF (the TEN-0005 tenant's policy) from source.

The original Meridian policy was a static, source-less PDF. This script makes it
REGENERABLE and versionable: edit the CONTENT below, run this, then re-index with
    python scripts/seed_policy.py TEN-0005 backend/storage/clients/TEN-0005/policy.pdf

Design goals (why the content is shaped this way):
  * The typology sections 4.1-4.8 keep the EXACT thresholds implemented by the rule
    engine (compliance_analyzer.py), so retrieval + citations stay aligned.
  * Each typology adds a "Red-flag indicators" bullet list + an "Illustrative example"
    + its goAML indicator code (goaml_builder.INDICATOR_MAP) — richer, more citable
    retrieval surface for the RAG SAR generator.
  * Numbered headings (e.g. "4.1 Structuring and Smurfing") are rendered larger than
    body text so document_ingestion_service's heading detection picks them up.
  * A running header/footer repeats on every page so the generic running-line remover
    strips it out of the chunks (same as the original document).

Amounts use "Rs." (not the rupee glyph) because the core PDF fonts lack a rupee glyph
— that mismatch is what produced mojibake in the previous document.

Run from repo root:  python scripts/build_meridian_policy.py [output_path]
"""
import os
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle, PageBreak,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "backend", "storage", "clients", "TEN-0005", "policy.pdf")

DOC_RUNNING = "Meridian Bank Limited - AML/CFT Policy v4.0 (Internal)"

# ── Styles ──────────────────────────────────────────────────────────────────
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=15,
                      spaceAfter=7, alignment=4)  # justified
H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=14, leading=18,
                    spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#0e2a47"))
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                    spaceBefore=12, spaceAfter=5, textColor=colors.HexColor("#12395f"))
LABEL = ParagraphStyle("label", fontName="Helvetica-BoldOblique", fontSize=9.5,
                       leading=13, spaceBefore=3, spaceAfter=2, textColor=colors.HexColor("#333333"))
BULLET = ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5, leading=13.5)
TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, leading=24,
                       spaceAfter=6, textColor=colors.HexColor("#0e2a47"))
SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=11, leading=15, spaceAfter=4,
                     textColor=colors.HexColor("#444444"))
SMALL = ParagraphStyle("small", fontName="Helvetica-Oblique", fontSize=8.5, leading=12,
                       textColor=colors.HexColor("#666666"))


def h1(n, t): return Paragraph(f"{n} {t}", H1)
def h2(n, t): return Paragraph(f"{n} {t}", H2)
def p(t): return Paragraph(t, BODY)
def label(t): return Paragraph(t, LABEL)


def bullets(items):
    # Render as one paragraph with an ASCII marker + hanging indent. reportlab's bullet
    # glyph ("•") embeds without a ToUnicode map, so it extracts as a mojibake box and
    # pollutes the RAG chunks — an en-dash marker stays clean through PDF text extraction.
    style = ParagraphStyle("bl", parent=BULLET, leftIndent=20, firstLineIndent=-10,
                           spaceBefore=1, spaceAfter=6, leading=14)
    txt = "<br/><br/>".join(f"-&nbsp;&nbsp;{it}" for it in items)
    return Paragraph(txt, style)


def typology(num, title, definition, red_flags, threshold, example, goaml):
    """One 4.x typology block: definition + red-flags + threshold + example + goAML code."""
    out = [h2(num, title), p(definition), label("Red-flag indicators:"), bullets(red_flags)]
    out.append(p(f"<b>Detection threshold.</b> {threshold}"))
    out.append(p(f"<b>Illustrative example.</b> {example}"))
    out.append(p(f"<b>goAML indicator code.</b> This typology is reported to FIU-IND under "
                 f"indicator <b>{goaml}</b>."))
    return out


def _page_furniture(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#8a8a8a"))
    canvas.drawString(20 * mm, 287 * mm, DOC_RUNNING)
    canvas.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
    canvas.drawString(20 * mm, 10 * mm, "CONFIDENTIAL - Internal Compliance")
    canvas.restoreState()


def build(out_path):
    story = []

    # ── Cover / control block (front matter — dropped before the first numbered heading) ──
    story += [
        Spacer(1, 30), Paragraph("MERIDIAN BANK LIMITED", TITLE),
        Paragraph("Anti-Money Laundering and Counter-Financing of Terrorism (AML/CFT) Policy", SUB),
        Spacer(1, 12),
    ]
    control = [
        ["Document Title", "Group AML/CFT Policy"],
        ["Version", "4.0"],
        ["Effective Date", "01 July 2026"],
        ["Policy Owner", "Principal Officer, Financial Crime Compliance"],
        ["Approved By", "Board Risk & Compliance Committee"],
        ["Classification", "Internal - Compliance"],
        ["Next Review", "30 June 2027"],
    ]
    t = Table(control, colWidths=[45 * mm, 120 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.5),
        ("FONT", (1, 0), (1, -1), "Helvetica", 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#12395f")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f4f6f9"), colors.white]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dfe4ea")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [t, Spacer(1, 14), Paragraph(
        "CONFIDENTIAL - This document is the property of Meridian Bank Limited and is issued for "
        "internal compliance use only. It is a fictional document created for software testing and "
        "does not constitute legal advice.", SMALL), PageBreak()]

    # ── 1. Introduction and Regulatory Framework ──
    story += [h1("1.", "Introduction and Regulatory Framework")]
    story += [h2("1.1", "Purpose and Scope"), p(
        "This Policy establishes the framework through which Meridian Bank Limited (the \"Bank\") "
        "prevents, detects and reports money laundering and the financing of terrorism. It applies to "
        "all branches, business units, employees, contractors and agents of the Bank, and to every "
        "product, account and channel through which the Bank accepts funds or executes transactions, "
        "including digital and UPI-based payment rails. The objective is to ensure the Bank is not "
        "used, intentionally or otherwise, as a conduit for the laundering of proceeds of crime, and "
        "that it discharges its statutory obligations as a reporting entity in full and on time.")]
    story += [h2("1.2", "Legal and Regulatory Basis"), p(
        "This Policy gives effect to the Bank's obligations as a reporting entity under:"), bullets([
        "The Prevention of Money-Laundering Act, 2002 (PMLA) and the PML (Maintenance of Records) "
        "Rules, 2005 - in particular the Section 12 obligations to verify client identity, maintain "
        "records and furnish information to the Financial Intelligence Unit - India (FIU-IND).",
        "The Reserve Bank of India Master Direction - Know Your Customer (KYC) Direction, 2016, as "
        "amended, prescribing Customer Acceptance, Customer Identification, risk categorisation and "
        "ongoing monitoring.",
        "The SEBI Master Circular on AML/CFT, where the Bank acts as or for a registered market "
        "intermediary.",
        "Red-flag indicators and typologies issued from time to time by FIU-IND.",
    ])]
    story += [h2("1.3", "Key Definitions"), p(
        "<b>Money laundering</b> is the process of concealing the origin of proceeds of crime through "
        "the stages of placement, layering and integration. <b>Reporting entity</b> means the Bank in "
        "its capacity as a banking company obliged to report under the PMLA. A <b>Suspicious "
        "Transaction Report (STR)</b>, used interchangeably with Suspicious Activity Report (SAR), is a "
        "report furnished to FIU-IND in respect of a transaction giving rise to a reasonable ground of "
        "suspicion. A <b>beneficial owner</b> is the natural person who ultimately owns or controls a "
        "client or on whose behalf a transaction is conducted.")]

    # ── 2. Governance ──
    story += [h1("2.", "Governance, Roles and Responsibilities")]
    story += [h2("2.1", "Principal Officer and Designated Director"), p(
        "The Bank shall appoint a Principal Officer of sufficient seniority responsible for monitoring "
        "transactions, ensuring compliance with this Policy and furnishing STRs to FIU-IND. The Bank "
        "shall also nominate a Designated Director bearing overall responsibility for compliance under "
        "the PMLA. The names, designations and contact details of both officers shall be communicated "
        "to FIU-IND.")]
    story += [h2("2.2", "Three Lines of Defence"), p(
        "The first line comprises business and operations staff who perform customer due diligence and "
        "raise internal alerts. The second line is the Financial Crime Compliance function, which "
        "calibrates monitoring rules, reviews alerts and determines whether an STR is warranted. The "
        "third line is Internal Audit, which independently tests the adequacy and effectiveness of the "
        "AML/CFT framework.")]
    story += [h2("2.3", "Independent Assurance and Model Governance"), p(
        "The automated monitoring system, its typology rules and its risk-scoring model are subject to "
        "periodic independent validation. Rule thresholds, false-positive rates and coverage are "
        "reviewed at least annually, and any change to a threshold or scoring weight is documented, "
        "approved by the Principal Officer and version-controlled so that every alert can be "
        "reconstructed against the rules in force at the time it was raised.")]

    # ── 3. Customer Due Diligence ──
    story += [h1("3.", "Customer Due Diligence")]
    story += [h2("3.1", "Customer Acceptance Policy"), p(
        "The Bank shall not open an account in an anonymous or fictitious name, nor where it is unable "
        "to apply appropriate customer due diligence, nor where the identity of the customer matches a "
        "person or entity on a designated sanctions or terrorist list.")]
    story += [h2("3.2", "Customer Identification Procedures"), p(
        "The Bank shall identify each customer and verify that identity using reliable, independent "
        "source documents, data or information, and shall identify and verify any beneficial owner "
        "where the customer acts on another's behalf.")]
    story += [h2("3.3", "Risk-Based Categorisation"), p(
        "Each customer is assigned a money-laundering risk category of low, medium or high on the basis "
        "of identity, financial status, nature of business and geography. The category determines the "
        "intensity and frequency of ongoing monitoring; a customer whose behaviour deviates materially "
        "from the expected profile is re-categorised and subjected to enhanced scrutiny.")]
    story += [h2("3.4", "Enhanced Due Diligence and Politically Exposed Persons"), p(
        "Enhanced due diligence applies to high-risk customers, to Politically Exposed Persons (PEPs) "
        "and their close associates, and to relationships involving jurisdictions with weak AML "
        "controls. Enhanced measures include senior-management approval to establish the relationship, "
        "establishing source of funds and source of wealth, and more frequent ongoing review.")]
    story += [h2("3.5", "Ongoing Monitoring of Transactions"), p(
        "The Bank continuously monitors transactions for consistency with its knowledge of the customer "
        "and their risk profile. Monitoring is performed by an automated transaction monitoring system "
        "that applies the typology rules in Section 4 and escalates exceptions for human review.")]
    story += [h2("3.6", "Sanctions and Watchlist Screening"), p(
        "Every customer, counterparty and payment is screened in real time against United Nations "
        "Security Council consolidated lists, lists notified by the competent Indian authority, and the "
        "Bank's internal watchlist. A positive or near match blocks the transaction pending review, and "
        "a confirmed match against a designated person is escalated immediately and reported "
        "irrespective of amount.")]

    # ── 4. Typologies ──
    story += [h1("4.", "Transaction Monitoring and Red-Flag Typologies")]
    story += [p(
        "The following typologies define the principal patterns the Bank treats as red flags. Each is "
        "implemented as an automated monitoring rule. Detection of one or more patterns generates an "
        "internal alert and, where the composite assessment warrants it, an STR under Section 5. Each "
        "typology below states its detection threshold and the goAML indicator under which it is "
        "reported.")]

    story += typology(
        "4.1", "Structuring and Smurfing",
        "Structuring (smurfing) is the deliberate fragmentation of what is in substance a single large "
        "transaction into several smaller transactions, each kept just below an applicable reporting "
        "threshold, to evade detection.",
        ["A single credit or debit approaching but below the Rs. 10,00,000 reporting threshold.",
         "Multiple payments split across UPI identifiers, prepaid instruments or wallets that in "
         "aggregate approach the threshold.",
         "Amounts repeatedly landing in the Rs. 8,00,000-9,99,999 band.",
         "A customer who asks how large a transfer can be 'without paperwork'."],
        "The Bank treats a single credit or debit in the range Rs. 8,00,000 to Rs. 9,99,999 as a "
        "structuring indicator; amounts in the upper band Rs. 9,00,000 to Rs. 9,99,999 are a "
        "high-confidence indicator.",
        "A customer transfers Rs. 9,45,000 by international wire - just below the Rs. 10,00,000 "
        "threshold - with no commercial rationale on file.",
        "STRUCTURING_BELOW_THRESHOLD")

    story += typology(
        "4.2", "Rapid Movement of Funds",
        "Funds that enter an account and are moved out again after only a brief interval may indicate "
        "layering, in which the account is used as a pass-through to obscure the audit trail.",
        ["Large-value reversals or refunds shortly after credit.",
         "Funds received and forwarded within a short window with no economic purpose.",
         "An account balance that repeatedly returns to near zero after large in-and-out flows."],
        "A transaction of type REVERSAL or REFUND for an amount exceeding Rs. 1,00,000 is flagged, on "
        "the basis that funds may have rested only briefly before being returned or redirected.",
        "Rs. 4,00,000 is credited and a REVERSAL of Rs. 3,90,000 is issued to a different counterparty "
        "within hours.",
        "RAPID_PASS_THROUGH")

    story += typology(
        "4.3", "Large Round-Number Transactions",
        "Genuine commercial transactions usually carry odd amounts reflecting prices, taxes and fees. "
        "Exact round figures are statistically unusual and may indicate movement of value unconnected "
        "to genuine trade.",
        ["Amounts that are exact multiples of Rs. 1,00,000 with no fractional component.",
         "Round-sum transfers inconsistent with the customer's usual invoice pattern.",
         "Round amounts of Rs. 5,00,000 and above."],
        "The Bank flags any transaction that is an exact multiple of Rs. 1,00,000, and treats round "
        "amounts of Rs. 5,00,000 and above with heightened attention.",
        "A payment of exactly Rs. 5,00,000 with the description field left blank.",
        "ROUND_AMOUNT")

    story += typology(
        "4.4", "Dormant Account Activation",
        "An account with no customer-initiated activity for an extended period that is then suddenly "
        "used for significant transactions presents elevated risk, as dormant accounts are a known "
        "laundering vehicle, including abuse of basic-savings and government-scheme (Jan-Dhan) accounts.",
        ["Sudden high-value activity on an account long marked dormant.",
         "Reactivation shortly followed by outbound transfers to new counterparties.",
         "A change of contact details immediately preceding reactivation."],
        "Where the monitoring system marks an account as dormant prior to the activity under review, "
        "the resulting alert is treated as a high-confidence suspicious indicator and escalated for "
        "enhanced review of source of funds.",
        "An account dormant for 26 months suddenly receives and forwards Rs. 6,00,000 the same day.",
        "DORMANT_REACTIVATION")

    story += typology(
        "4.5", "High-Risk Transaction Types",
        "Certain transaction types carry inherently elevated risk because they facilitate rapid, "
        "cross-border or pseudonymous movement of value, and are subject to enhanced scrutiny in every "
        "case.",
        ["Cryptocurrency / virtual-asset purchases (CRYPTO_PURCHASE).",
         "International wire transfers (INTERNATIONAL_WIRE).",
         "Foreign-exchange transfers (FOREX_TRANSFER).",
         "Transactions bearing the characteristics of informal value transfer or hawala (HAWALA)."],
        "The Bank classifies CRYPTO_PURCHASE, INTERNATIONAL_WIRE, FOREX_TRANSFER and HAWALA as "
        "high-risk and reviews each against the customer's profile and the stated purpose of the "
        "transaction.",
        "A retail customer with a domestic salary profile initiates a CRYPTO_PURCHASE to an offshore "
        "exchange.",
        "HIGH_RISK_INSTRUMENT")

    story += typology(
        "4.6", "High-Velocity Transaction Patterns",
        "Velocity refers to the number of transactions conducted within a short window. A sudden burst "
        "of many transactions, disproportionate to the customer's established profile, may indicate "
        "layering or use of the account as a mule.",
        ["A spike in transaction count far above the customer's baseline.",
         "Many transfers to distinct counterparties in a compressed period.",
         "Structured bursts timed to avoid periodic review."],
        "The Bank flags accounts exhibiting a high-velocity pattern; any alert whose composite risk "
        "score reaches or exceeds 90 is treated as a high-confidence velocity indicator warranting "
        "immediate review.",
        "An account executes 40 outbound transfers within one hour, against a monthly baseline of five.",
        "HIGH_VELOCITY")

    story += typology(
        "4.7", "High-Risk Counterparties and Institutions",
        "The risk of a transaction is materially affected by the institution on the other side of it. "
        "Dealings with counterparties that cannot be reliably identified, with shell banks, or with "
        "entities in opaque offshore jurisdictions are treated as high-risk.",
        ["Counterparty institution unknown or unverifiable.",
         "Shell banks with no physical presence.",
         "Offshore companies in opaque jurisdictions.",
         "Otherwise anonymous institutions."],
        "The Bank flags counterparties whose institution is unknown, a shell bank, an offshore company "
        "or otherwise anonymous, and applies enhanced due diligence before proceeding.",
        "An outbound wire is directed to an account at an institution recorded only as 'Unknown Bank'.",
        "HIGH_RISK_COUNTERPARTY")

    story += typology(
        "4.8", "Composite Risk Scoring",
        "Each alert is assigned a composite risk score on a scale of 0 to 100, combining the base risk "
        "supplied by the originating system with increments for each typology triggered.",
        ["A score at or above 75 requires escalation and, ordinarily, the filing of an STR.",
         "A score at or above 85 denotes a high-confidence determination.",
         "The score is an aid to, not a substitute for, the judgement of the Principal Officer."],
        "A composite score at or above 75 denotes a transaction sufficiently suspicious to require "
        "escalation; at or above 85, a high-confidence determination.",
        "Structuring, an international wire and a risk score of 88 combine to a composite score of 100, "
        "escalated for immediate filing.",
        "HIGH_COMPOSITE_RISK_SCORE")

    story += [h2("4.9", "Mule Accounts and Third-Party Layering"), p(
        "Accounts opened or rented for the purpose of receiving and forwarding the proceeds of others "
        "- 'money mules' - are a recurring layering vehicle, frequently recruited through fraudulent "
        "job or investment offers. Indicators include an account whose inflows and outflows are "
        "inconsistent with the holder's stated occupation, rapid onward transfer of received funds, "
        "and clusters of accounts sharing a device, IP address or beneficiary. Such patterns are "
        "escalated for enhanced review even where no single Section 4 threshold is met.")]

    # ── 5. Reporting ──
    story += [h1("5.", "Suspicious Transaction Reporting")]
    story += [h2("5.1", "Obligation to Report"), p(
        "The Bank shall furnish an STR to FIU-IND whenever it has reasonable grounds to believe that a "
        "transaction, or a series of transactions, involves the proceeds of crime, regardless of amount "
        "and irrespective of whether the transaction was completed or merely attempted. There is no "
        "monetary threshold for an STR: suspicion alone is sufficient and necessary.")]
    story += [h2("5.2", "Internal Escalation Workflow"), p(
        "Alerts are reviewed by the Financial Crime Compliance team. Where an alert is assessed as a "
        "genuine suspicion it is escalated to the Principal Officer, who determines whether an STR is "
        "filed. The reasoning, evidence and decision for every escalated alert are documented and "
        "retained, whether or not a report is ultimately made.")]
    story += [h2("5.3", "goAML Filing Format and Required Content"), p(
        "STRs are submitted to FIU-IND electronically through the goAML portal in the prescribed "
        "format. Each report shall, at a minimum, identify the reporting entity and the Principal "
        "Officer; describe the account holder and any beneficial owner; set out the transaction details "
        "including date, amount, type and counterparty; state the ground of suspicion with reference to "
        "the specific typology or red flag observed and its indicator code; and attach the supporting "
        "analysis. The narrative must be clear, factual and self-contained.")]
    story += [h2("5.4", "Timeliness"), p(
        "An STR shall be furnished to FIU-IND not later than seven working days after the Bank forms "
        "the suspicion. Delay defeats the purpose of the report and may itself attract regulatory "
        "consequence.")]
    story += [h2("5.5", "Prohibition on Tipping-Off"), p(
        "No officer or employee shall disclose to the customer or any third party, directly or "
        "indirectly, that an STR has been or is being filed or that the customer's transactions are "
        "under examination. Tipping-off is strictly prohibited and is itself a serious compliance "
        "breach.")]

    # ── 6-9 ──
    story += [h1("6.", "Record-Keeping and Retention"), p(
        "The Bank shall maintain records of all transactions, of the identity of its clients, and of "
        "all STRs filed, in a manner allowing the reconstruction of individual transactions. Identity "
        "records are retained for the period prescribed under the PMLA after the business relationship "
        "ends, and transaction records for the prescribed period after the transaction date. Records "
        "are made available to competent authorities on demand.")]
    story += [h1("7.", "Employee Training and Awareness"), p(
        "The Bank shall implement an ongoing training programme so that staff understand their "
        "obligations, can recognise the red-flag typologies in Section 4, and understand the escalation "
        "procedure and the prohibition on tipping-off. Training is tailored to role and refreshed at "
        "regular intervals.")]
    story += [h1("8.", "Consequences of Non-Compliance"), p(
        "Failure to comply with the PMLA may expose the Bank to monetary penalties imposed by the "
        "Director, FIU-IND, ranging from Rs. 10,000 to Rs. 1,00,000 for each failure, and to further "
        "supervisory action by the Reserve Bank of India. An employee who wilfully disregards this "
        "Policy is subject to disciplinary action up to and including termination, in addition to any "
        "personal liability under law.")]
    story += [h1("9.", "Policy Governance and Review"), p(
        "This Policy shall be reviewed at least annually, and additionally whenever there is a material "
        "change in the law, in regulatory guidance, or in the Bank's products and risk profile. "
        "Amendments require the approval of the Board Risk and Compliance Committee. The Principal "
        "Officer maintains the current version and communicates changes to all affected staff.")]

    # ── Appendix A: typology -> goAML indicator reference ──
    story += [PageBreak(), h1("Appendix A.", "Typology to goAML Indicator Reference")]
    rows = [["Section", "Typology", "Detection threshold", "goAML indicator"],
            ["4.1", "Structuring / Smurfing", "Rs. 8,00,000-9,99,999", "STRUCTURING_BELOW_THRESHOLD"],
            ["4.2", "Rapid Movement of Funds", "REVERSAL/REFUND > Rs. 1,00,000", "RAPID_PASS_THROUGH"],
            ["4.3", "Large Round-Number", "Exact multiple of Rs. 1,00,000", "ROUND_AMOUNT"],
            ["4.4", "Dormant Account Activation", "Activity on a dormant account", "DORMANT_REACTIVATION"],
            ["4.5", "High-Risk Transaction Type", "CRYPTO/WIRE/FOREX/HAWALA", "HIGH_RISK_INSTRUMENT"],
            ["4.6", "High-Velocity Pattern", "Score >= 90 high-confidence", "HIGH_VELOCITY"],
            ["4.7", "High-Risk Counterparty", "Unknown/shell/offshore", "HIGH_RISK_COUNTERPARTY"],
            ["4.8", "Composite Risk Scoring", "Score >= 75 (>= 85 high)", "HIGH_COMPOSITE_RISK_SCORE"]]
    at = Table(rows, colWidths=[16 * mm, 44 * mm, 52 * mm, 58 * mm])
    at.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e2a47")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f9")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dfe4ea")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [Spacer(1, 6), at, Spacer(1, 10),
              Paragraph("End of document - Meridian Bank Limited AML/CFT Policy v4.0 "
                        "(synthetic test data).", SMALL)]

    doc = SimpleDocTemplate(out_path, pagesize=A4, topMargin=22 * mm, bottomMargin=18 * mm,
                            leftMargin=20 * mm, rightMargin=20 * mm, title="Meridian Bank AML/CFT Policy")
    doc.build(story, onFirstPage=_page_furniture, onLaterPages=_page_furniture)
    return out_path


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    path = build(out)
    size = os.path.getsize(path)
    print(f"Wrote {path} ({size:,} bytes)")
