"""
Builds the synthetic *Aegis Bank Ltd.* AML/CFT Policy PDF used as RAG test data.

The document is fictional but its structure and language are distilled from real
Indian regulatory sources (PMLA 2002, RBI KYC Master Direction 2016, SEBI AML
master circular, FIU-India STR guidance). Section 4 (typologies) deliberately
uses the SAME thresholds as backend/app/services/compliance_analyzer.py so that a
mock alert which trips a rule should retrieve the matching policy section.

Run:  python testing/build_policy.py   (or via: python scripts/seed_testing.py)
Out:  testing/corpus/aegis_bank_aml_policy.pdf

Note: reportlab's built-in fonts have no Indian Rupee glyph (U+20B9), so amounts
are written as "Rs." to avoid missing-glyph boxes.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, HRFlowable
)
from reportlab.lib import colors

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "corpus", "aegis_bank_aml_policy.pdf"))

# --- Styles -----------------------------------------------------------------
styles = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                    fontSize=15, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#0B2E4F"))
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=12, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#14507F"))
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontName="Helvetica",
                      fontSize=10.2, leading=15, alignment=TA_JUSTIFY, spaceAfter=7)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=14, bulletIndent=4, spaceAfter=3)
TITLE = ParagraphStyle("TITLE", parent=styles["Title"], fontName="Helvetica-Bold",
                       fontSize=22, leading=26, alignment=TA_CENTER, textColor=colors.HexColor("#0B2E4F"))
SUB = ParagraphStyle("SUB", parent=styles["Normal"], fontSize=12, alignment=TA_CENTER,
                     textColor=colors.HexColor("#14507F"), spaceBefore=6)
SMALL = ParagraphStyle("SMALL", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER,
                       textColor=colors.grey)

story = []


def h1(text):
    story.append(Paragraph(text, H1))


def h2(text):
    story.append(Paragraph(text, H2))


def p(text):
    story.append(Paragraph(text, BODY))


def bullet(text):
    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{text}", BULLET))


def gap(h=6):
    story.append(Spacer(1, h))


# --- Cover ------------------------------------------------------------------
gap(60)
story.append(Paragraph("AEGIS BANK LIMITED", TITLE))
gap(6)
story.append(Paragraph("Anti-Money Laundering and Counter-Financing of Terrorism "
                       "(AML/CFT) Policy", SUB))
gap(30)
story.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor("#14507F"),
                        spaceBefore=4, spaceAfter=10, hAlign="CENTER"))
meta = Table([
    ["Document Title", "Group AML/CFT Policy"],
    ["Version", "3.2"],
    ["Effective Date", "01 April 2026"],
    ["Policy Owner", "Principal Officer, Financial Crime Compliance"],
    ["Approved By", "Board Risk & Compliance Committee"],
    ["Classification", "Internal - Compliance"],
    ["Next Review", "31 March 2027"],
], colWidths=[55 * mm, 95 * mm])
meta.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
    ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.5),
    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0B2E4F")),
    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F4F7FA"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DEE6")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
meta.hAlign = "CENTER"
story.append(meta)
gap(40)
story.append(Paragraph("CONFIDENTIAL - This document is the property of Aegis Bank "
                       "Limited and is issued for internal compliance use only. It is a "
                       "fictional document created for software testing and does not "
                       "constitute legal advice.", SMALL))
story.append(PageBreak())

# --- 1. Introduction --------------------------------------------------------
h1("1. Introduction and Regulatory Framework")

h2("1.1 Purpose and Scope")
p("This Policy establishes the framework through which Aegis Bank Limited (the "
  "\"Bank\") prevents, detects and reports money laundering and the financing of "
  "terrorism. It applies to all branches, business units, employees, contractors "
  "and agents of the Bank, and to every product, account and channel through which "
  "the Bank accepts funds or executes transactions, including digital and UPI-based "
  "payment rails.")
p("The objective of the Policy is to ensure that the Bank is not used, intentionally "
  "or unintentionally, as a conduit for the laundering of proceeds of crime, and that "
  "the Bank discharges its statutory obligations as a reporting entity in full and on "
  "time.")

h2("1.2 Legal and Regulatory Basis")
p("This Policy gives effect to the obligations imposed on the Bank as a reporting "
  "entity under the following instruments:")
bullet("The Prevention of Money-Laundering Act, 2002 (PMLA) and the Prevention of "
       "Money-Laundering (Maintenance of Records) Rules, 2005, in particular the "
       "obligations under Section 12 to verify client identity, maintain records and "
       "furnish information to the Financial Intelligence Unit - India (FIU-IND).")
bullet("The Reserve Bank of India Master Direction - Know Your Customer (KYC) "
       "Direction, 2016, as amended, which prescribes Customer Acceptance Policy, "
       "Customer Identification Procedures, risk categorisation and ongoing "
       "monitoring of transactions.")
bullet("The Securities and Exchange Board of India (SEBI) Master Circular on "
       "Anti-Money Laundering and Counter-Financing of Terrorism, where the Bank "
       "acts as or for a registered market intermediary.")
bullet("Guidance and red-flag indicators issued from time to time by FIU-IND "
       "regarding the identification and reporting of suspicious transactions.")

h2("1.3 Key Definitions")
p("<b>Money laundering</b> is the process of concealing the origin of proceeds of "
  "crime so that they appear to derive from a legitimate source, classically through "
  "the stages of placement, layering and integration. <b>Reporting entity</b> means "
  "the Bank in its capacity as a banking company obliged to report under the PMLA. "
  "<b>Suspicious Transaction Report (STR)</b>, used interchangeably in this Policy "
  "with Suspicious Activity Report (SAR), means a report furnished to FIU-IND in "
  "respect of a transaction that gives rise to a reasonable ground of suspicion. "
  "<b>Beneficial owner</b> means the natural person who ultimately owns or controls "
  "a client or on whose behalf a transaction is conducted.")

# --- 2. Governance ----------------------------------------------------------
h1("2. Governance, Roles and Responsibilities")

h2("2.1 Principal Officer and Designated Director")
p("The Bank shall appoint a Principal Officer of sufficient seniority who is "
  "responsible for monitoring transactions, ensuring compliance with this Policy and "
  "furnishing STRs and other prescribed reports to FIU-IND. The Bank shall also "
  "nominate a Designated Director who bears overall responsibility for compliance "
  "with the obligations under the PMLA and the Rules. The names, designations and "
  "contact details of both officers shall be communicated to FIU-IND.")

h2("2.2 Three Lines of Defence")
p("The first line of defence comprises business and operations staff who perform "
  "customer due diligence and raise internal alerts. The second line comprises the "
  "Financial Crime Compliance function, which calibrates monitoring rules, reviews "
  "alerts and determines whether an STR is warranted. The third line is Internal "
  "Audit, which independently tests the adequacy and effectiveness of the AML/CFT "
  "framework.")

# --- 3. CDD -----------------------------------------------------------------
h1("3. Customer Due Diligence")

h2("3.1 Customer Acceptance Policy")
p("The Bank shall not open an account in an anonymous or fictitious name, nor where "
  "the Bank is unable to apply appropriate customer due diligence measures, nor where "
  "the identity of the customer matches a person or entity on a designated sanctions "
  "or terrorist list. No account shall be opened or continued where the Bank is "
  "unable to verify the identity of the customer or the beneficial owner.")

h2("3.2 Customer Identification Procedures")
p("The Bank shall identify each customer and verify that identity using reliable, "
  "independent source documents, data or information. Where the customer is acting on "
  "behalf of another person, the Bank shall identify the beneficial owner and take "
  "reasonable steps to verify that person's identity.")

h2("3.3 Risk-Based Categorisation")
p("Each customer shall be assigned a money-laundering risk category of low, medium "
  "or high on the basis of the customer's identity, social and financial status, the "
  "nature of business activity, and information about the customer's clients' "
  "business and their location. The category determines the intensity and frequency "
  "of ongoing monitoring. A customer whose behaviour deviates materially from the "
  "expected profile shall be re-categorised and subjected to enhanced scrutiny.")

h2("3.4 Enhanced Due Diligence and Politically Exposed Persons")
p("Enhanced due diligence shall apply to high-risk customers, to Politically Exposed "
  "Persons (PEPs) and their close associates, and to relationships involving "
  "jurisdictions known for weak AML controls. Enhanced measures include obtaining "
  "senior management approval to establish the relationship, establishing the source "
  "of funds and source of wealth, and conducting more frequent ongoing review.")

h2("3.5 Ongoing Monitoring of Transactions")
p("The Bank shall continuously monitor transactions to ensure that they are "
  "consistent with the Bank's knowledge of the customer, the customer's business and "
  "risk profile and, where necessary, the source of funds. Monitoring is performed by "
  "an automated transaction monitoring system that applies the typology rules set out "
  "in Section 4 and escalates exceptions for human review.")

# --- 4. Typologies (THE RAG-CRITICAL SECTION) -------------------------------
h1("4. Transaction Monitoring and Red-Flag Typologies")
p("The following typologies define the principal patterns the Bank treats as red "
  "flags. Each is implemented as an automated monitoring rule. The detection of one "
  "or more of these patterns shall cause an internal alert to be generated and, where "
  "the composite assessment warrants it, an STR to be filed in accordance with "
  "Section 5.")

h2("4.1 Structuring and Smurfing")
p("Structuring, also called smurfing, is the deliberate fragmentation of what is in "
  "substance a single large transaction into several smaller transactions, each kept "
  "just below an applicable reporting or monitoring threshold, in order to evade "
  "detection. The Bank treats a single credit or debit in the range of Rs. 8,00,000 "
  "to Rs. 9,99,999 - that is, an amount approaching but remaining below the "
  "Rs. 10,00,000 reporting threshold - as a structuring indicator. Amounts in the "
  "upper part of that band, from Rs. 9,00,000 to Rs. 9,99,999, are treated as a "
  "high-confidence indicator. Particular attention is paid to payments split across "
  "multiple UPI identifiers, prepaid instruments or wallets that, in aggregate, "
  "approach the threshold, a pattern flagged by FIU-IND as an emerging vector.")

h2("4.2 Rapid Movement of Funds")
p("Funds that enter an account and are moved out again after only a brief interval "
  "may indicate layering, in which the account is used as a pass-through to obscure "
  "the audit trail. The Bank treats reversals and refunds of large value as an "
  "indicator of rapid movement: a transaction of type REVERSAL or REFUND for an "
  "amount exceeding Rs. 1,00,000 shall be flagged, on the basis that funds may have "
  "rested in the account only briefly before being returned or redirected.")

h2("4.3 Large Round-Number Transactions")
p("Genuine commercial transactions usually carry odd amounts reflecting prices, "
  "taxes and fees. Transactions in exact round figures - amounts that are exact "
  "multiples of Rs. 1,00,000 with no fractional component - are statistically "
  "unusual and may indicate the movement of value unconnected to genuine trade. The "
  "Bank flags any transaction that is an exact multiple of Rs. 1,00,000, and treats "
  "round amounts of Rs. 5,00,000 and above with heightened attention.")

h2("4.4 Dormant Account Activation")
p("An account that has shown no customer-initiated activity for an extended period "
  "and is then suddenly used for significant transactions presents elevated risk, "
  "because dormant accounts are a known vehicle for laundering, including the abuse "
  "of basic savings and government-scheme (Jan-Dhan) accounts. Where the monitoring "
  "system marks an account as dormant prior to the activity under review, the "
  "resulting alert shall be treated as a high-confidence suspicious indicator and "
  "escalated for enhanced review of the source of funds.")

h2("4.5 High-Risk Transaction Types")
p("Certain transaction types carry an inherently elevated money-laundering risk "
  "because they facilitate the rapid, cross-border or pseudonymous movement of value. "
  "The Bank classifies the following transaction types as high-risk and subjects "
  "them to enhanced scrutiny in every case: cryptocurrency and virtual-asset "
  "purchases (CRYPTO_PURCHASE), international wire transfers (INTERNATIONAL_WIRE), "
  "foreign-exchange transfers (FOREX_TRANSFER) and any transaction bearing the "
  "characteristics of an informal value-transfer or hawala arrangement (HAWALA). "
  "Transactions of these types shall be reviewed against the customer's profile and "
  "the stated purpose of the transaction.")

h2("4.6 High-Velocity Transaction Patterns")
p("Velocity refers to the number of transactions conducted within a short window. A "
  "sudden burst of many transactions in a compressed period - disproportionate to the "
  "customer's established profile - may indicate the layering of funds or the use of "
  "the account as a mule. The Bank flags accounts exhibiting a high-velocity pattern, "
  "and any alert whose composite risk score reaches or exceeds 90 is treated as a "
  "high-confidence velocity indicator warranting immediate review.")

h2("4.7 High-Risk Counterparties and Institutions")
p("The risk of a transaction is materially affected by the institution on the other "
  "side of it. Dealings with counterparties that cannot be reliably identified, with "
  "shell banks that have no physical presence, or with entities established in opaque "
  "offshore jurisdictions, are treated as high-risk. The Bank specifically flags "
  "counterparties whose institution is unknown or unverifiable, shell banks, "
  "offshore companies, and otherwise anonymous institutions, and applies enhanced due "
  "diligence to establish the legitimacy of the relationship before proceeding.")

h2("4.8 Composite Risk Scoring")
p("Each alert is assigned a composite risk score on a scale of 0 to 100, combining "
  "the base risk supplied by the originating system with increments for each typology "
  "triggered. A score at or above 75 denotes a transaction sufficiently suspicious to "
  "require escalation and, ordinarily, the filing of an STR; a score at or above 85 "
  "denotes a high-confidence determination. The score is an aid to, and not a "
  "substitute for, the judgement of the Principal Officer.")

# --- 5. STR -----------------------------------------------------------------
h1("5. Suspicious Transaction Reporting")

h2("5.1 Obligation to Report")
p("The Bank shall furnish a Suspicious Transaction Report to FIU-IND whenever it has "
  "reasonable grounds to believe that a transaction, or a series of transactions, "
  "involves the proceeds of crime, regardless of the amount and irrespective of "
  "whether the transaction was completed or merely attempted. There is no monetary "
  "threshold for an STR: suspicion alone is sufficient and necessary.")

h2("5.2 Internal Escalation Workflow")
p("Alerts generated by the monitoring system are reviewed by the Financial Crime "
  "Compliance team. Where an alert is assessed as a genuine suspicion, it is escalated "
  "to the Principal Officer, who determines whether an STR is to be filed. The "
  "reasoning, evidence and decision for every escalated alert are documented and "
  "retained, whether or not a report is ultimately made.")

h2("5.3 goAML Filing Format and Required Content")
p("STRs are submitted to FIU-IND electronically through the goAML portal in the "
  "prescribed format. Each report shall, at a minimum, identify the reporting entity "
  "and the Principal Officer; describe the account holder and any beneficial owner; "
  "set out the transaction details including date, amount, type and counterparty; "
  "state the ground of suspicion with reference to the specific typology or red flag "
  "observed; and attach the supporting analysis. The narrative must be clear, "
  "factual and self-contained, so that a reader at FIU-IND can understand the basis "
  "of the suspicion without reference to other documents.")

h2("5.4 Timeliness")
p("An STR shall be furnished to FIU-IND not later than seven working days after the "
  "Bank forms the suspicion. Delay in filing defeats the purpose of the report and "
  "may itself attract regulatory consequence.")

h2("5.5 Prohibition on Tipping-Off")
p("No officer or employee of the Bank shall disclose to the customer or to any third "
  "party, directly or indirectly, that an STR has been or is being filed, or that the "
  "customer's transactions are under examination. Tipping-off is strictly prohibited "
  "and may prejudice an investigation; it is itself a serious compliance breach.")

# --- 6. Records -------------------------------------------------------------
h1("6. Record-Keeping and Retention")
p("The Bank shall maintain records of all transactions, the records of the identity "
  "of its clients, and records of all STRs filed, in a manner that allows the "
  "reconstruction of individual transactions. Records of identity shall be maintained "
  "for the period prescribed under the PMLA and the Rules after the business "
  "relationship has ended, and transaction records for the prescribed period after "
  "the date of the transaction. Records shall be made available to competent "
  "authorities on demand.")

# --- 7. Training ------------------------------------------------------------
h1("7. Employee Training and Awareness")
p("The Bank shall implement an ongoing programme of employee training so that staff "
  "are aware of their obligations under this Policy, are able to recognise the red-"
  "flag typologies set out in Section 4, and understand the internal escalation "
  "procedure and the prohibition on tipping-off. Training shall be tailored to the "
  "roles of the staff concerned and refreshed at regular intervals.")

# --- 8. Penalties -----------------------------------------------------------
h1("8. Consequences of Non-Compliance")
p("Failure to comply with the obligations under the PMLA may expose the Bank to "
  "monetary penalties imposed by the Director, FIU-IND, ranging from Rs. 10,000 to "
  "Rs. 1,00,000 for each failure, and may attract further supervisory action by the "
  "Reserve Bank of India including censure and restriction of business. An employee "
  "who wilfully disregards this Policy is subject to internal disciplinary action up "
  "to and including termination, in addition to any personal liability under law.")

# --- 9. Review --------------------------------------------------------------
h1("9. Policy Governance and Review")
p("This Policy shall be reviewed at least annually, and additionally whenever there "
  "is a material change in the law, in regulatory guidance, or in the Bank's products "
  "and risk profile. Amendments require the approval of the Board Risk and Compliance "
  "Committee. The Principal Officer is responsible for maintaining the current version "
  "and for communicating changes to all affected staff.")

gap(10)
story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D6DEE6")))
gap(4)
story.append(Paragraph("End of document - Aegis Bank Limited AML/CFT Policy v3.2 "
                       "(synthetic test data).", SMALL))


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(20 * mm, 12 * mm, "Aegis Bank Limited - AML/CFT Policy v3.2 (Internal)")
    canvas.drawRightString(190 * mm, 12 * mm, "Page %d" % doc.page)
    canvas.restoreState()


def main():
    doc = SimpleDocTemplate(
        OUT, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title="Aegis Bank Limited - AML/CFT Policy",
        author="Aegis Bank Limited (synthetic)",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    size = os.path.getsize(OUT)
    print("Wrote %s (%d bytes, %d flowables)" % (OUT, size, len(story)))


if __name__ == "__main__":
    main()
