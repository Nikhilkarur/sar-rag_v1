# Real AML Source Documents (India)

Official, free, public regulatory documents to download into this folder when we
want to test RAG against genuine regulatory text. The synthetic Aegis Bank policy
in `../generated/` is distilled from the structure and language of these.

| # | Document | Why it matters | URL |
|---|----------|----------------|-----|
| 1 | FIU-India — STR / reporting guidance & FAQs | Governs what an STR must contain and when to file | https://fiuindia.gov.in/files/FAQs/faqs.html |
| 2 | RBI — Master Direction: KYC, 2016 (as amended) | CDD, risk categorisation, ongoing monitoring, STR obligation | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566 |
| 3 | SEBI — AML/CFT Master Circular for intermediaries | The broker persona (Aegis's target customer) | https://www.sebi.gov.in/ |
| 4 | PMLA, 2002 — Bare Act | Foundational legislation; Sec.12 record/reporting duties | https://www.indiacode.nic.in/bitstream/123456789/2062/1/A2003-15.pdf |
| 5 | FIU-India — goAML STR user manual | Exact fields a valid STR submission requires | https://fiuindia.gov.in/ |

## Key facts captured from these sources (June 2026 research)

- **No threshold for STR:** an STR is filed whenever there are reasonable grounds
  to suspect proceeds of crime / terror financing, *irrespective of amount*.
- **Timeline:** file within **7 working days** of forming suspicion.
- **Tipping-off is prohibited** — the customer must not be alerted.
- **Reporting entities:** banks, NBFCs, SEBI intermediaries, virtual asset
  service providers.
- **RBI KYC pillars:** Customer Acceptance Policy, Risk Management, Customer
  Identification Procedures (CIP), Monitoring of Transactions.
- **India-specific typologies:** UPI/wallet structuring below monitoring
  thresholds, dormant Jan-Dhan account activation, benami/beneficial-ownership
  concealment, layering across banks/borders.
- **Penalties:** ~Rs. 10,000 to Rs. 1,00,000 per violation; possible license
  action.

> When downloading the real PDFs, save them here as e.g.
> `fiu_str_guidance.pdf`, `rbi_kyc_md_2016.pdf`, etc., then upload through the
> document endpoint once it exists.
