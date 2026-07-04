/**
 * Builds the self-contained "Technical Integration Reference" HTML document that the bank's
 * compliance team hands to their engineering team. Rendered in an isolated iframe on the
 * Schema page and reused verbatim for Print / Save-as-PDF / Download.
 *
 * The contract below is the REAL one the ingestion API enforces:
 *   POST /api/v1/ingest/  with headers X-API-Key, X-Tenant-ID (+ optional Idempotency-Key),
 *   the STANDARD_FINTECH nested body, and the sar.approved webhook back to the bank.
 * Keep it accurate — this is what a customer integrates against. ASCII only (no curly quotes).
 */

const API_BASE = 'https://api.aegis-aml.com'

type Field = { path: string; example: string; pii: boolean; desc: string }
type Group = { group: string; blurb: string; fields: Field[] }

const REQUEST_SPEC: Group[] = [
  {
    group: 'customer', blurb: 'The account holder the alert is about.',
    fields: [
      { path: 'customer.full_name', example: 'Rajesh Kumar Sharma', pii: true, desc: 'Legal name of the account holder. Tokenized before any analysis.' },
      { path: 'customer.id', example: 'CUST-98271', pii: true, desc: 'Your internal customer identifier.' },
    ],
  },
  {
    group: 'account', blurb: 'The originating account.',
    fields: [
      { path: 'account.number', example: 'HDFC-00123456789', pii: true, desc: 'Debited account number / IBAN.' },
    ],
  },
  {
    group: 'txn', blurb: 'The transaction that fired your alert.',
    fields: [
      { path: 'txn.ref_id', example: 'TXN-2026-061099182', pii: false, desc: 'Unique transaction reference. Echoed back and used to correlate the report.' },
      { path: 'txn.amount', example: '990000.00', pii: false, desc: 'Transaction amount as a decimal number.' },
      { path: 'txn.currency', example: 'INR', pii: false, desc: 'ISO 4217 currency code.' },
      { path: 'txn.type', example: 'NEFT_TRANSFER', pii: false, desc: 'Instrument / rail, e.g. NEFT_TRANSFER, IMPS, UPI, INTERNATIONAL_WIRE.' },
      { path: 'txn.direction', example: 'DEBIT', pii: false, desc: 'DEBIT or CREDIT.' },
      { path: 'txn.timestamp', example: '2026-06-10T09:30:00+05:30', pii: false, desc: 'ISO 8601 timestamp of the transaction.' },
    ],
  },
  {
    group: 'counterparty', blurb: 'The other side of the transaction.',
    fields: [
      { path: 'counterparty.account', example: 'ICICI-00987654321', pii: true, desc: 'Beneficiary account number.' },
      { path: 'counterparty.name', example: 'Priya Enterprises', pii: true, desc: 'Beneficiary name.' },
      { path: 'counterparty.bank', example: 'ICICI Bank', pii: false, desc: 'Beneficiary institution.' },
    ],
  },
  {
    group: 'metadata', blurb: 'Optional context that sharpens the risk assessment.',
    fields: [
      { path: 'metadata.ip', example: '103.27.9.44', pii: true, desc: 'Originating IP address of the session.' },
      { path: 'metadata.device_id', example: 'MOB-a1b2c3d4e5f6', pii: true, desc: 'Device fingerprint of the session.' },
    ],
  },
  {
    group: 'risk', blurb: 'Your own scoring, passed through for context.',
    fields: [
      { path: 'risk.score', example: '87', pii: false, desc: 'Your TMS risk score (0-100). Aegis independently re-scores; a composite score >= 75 triggers a SAR.' },
      { path: 'risk.reason', example: 'Near reporting threshold', pii: false, desc: 'Short reason your rule fired.' },
    ],
  },
]

const CURL = (tenantId: string) => [
  `curl -X POST ${API_BASE}/api/v1/ingest/ \\`,
  '  -H "X-API-Key: sk-ae-YOUR-API-KEY" \\',
  `  -H "X-Tenant-ID: ${tenantId}" \\`,
  '  -H "Idempotency-Key: TXN-2026-061099182" \\',
  '  -H "Content-Type: application/json" \\',
  "  -d '{",
  '    "customer":     { "full_name": "Rajesh Kumar Sharma", "id": "CUST-98271" },',
  '    "account":      { "number": "HDFC-00123456789" },',
  '    "txn":          {',
  '      "ref_id": "TXN-2026-061099182", "amount": 990000.00, "currency": "INR",',
  '      "type": "NEFT_TRANSFER", "direction": "DEBIT",',
  '      "timestamp": "2026-06-10T09:30:00+05:30"',
  '    },',
  '    "counterparty": { "account": "ICICI-00987654321", "name": "Priya Enterprises", "bank": "ICICI Bank" },',
  '    "metadata":     { "ip": "103.27.9.44", "device_id": "MOB-a1b2c3d4e5f6" },',
  '    "risk":         { "score": 87, "reason": "Near reporting threshold" }',
  "  }'",
].join('\n')

const RESPONSE = [
  '{',
  '  "status": "success",',
  '  "alert_id": "a3f1c2e8-...-9b7d",',
  '  "risk_score": 92,',
  '  "message": "Ingested successfully. SAR generation triggered."',
  '}',
].join('\n')

const WEBHOOK = [
  'POST <your callback_url>',
  'X-Aegis-Event: sar.approved',
  'X-Aegis-Signature: sha256=<hex hmac of the raw body, keyed with your webhook secret>',
  '',
  '{',
  '  "event": "sar.approved",',
  '  "sar_id": "...", "alert_id": "...",',
  '  "transaction_ref": "TXN-2026-061099182",',
  '  "narrative_text": "<the policy-cited STR narrative>",',
  '  "compliance_rules_triggered": ["STRUCTURING_BELOW_THRESHOLD", "HIGH_RISK_INSTRUMENT"],',
  '  "recommended_action": { ... },',
  '  "pdf_base64": "<the STR PDF, base64-encoded>"',
  '}',
].join('\n')

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function fieldRows(): string {
  return REQUEST_SPEC.map((g) => `
    <div class="grp">
      <h3>${g.group} <span class="grp-blurb">${esc(g.blurb)}</span></h3>
      ${g.fields.map((f) => `
        <div class="field">
          <div class="field-head">
            <code>${esc(f.path)}</code>
            ${f.pii
              ? '<span class="tag pii">PII &middot; tokenized</span>'
              : '<span class="tag plain">not PII</span>'}
          </div>
          <div class="desc">${esc(f.desc)}</div>
          <div class="eg">Example: <span>${esc(f.example)}</span></div>
        </div>`).join('')}
    </div>`).join('')
}

export function buildTechDocHtml(tenantId: string): string {
  const generated = new Date().toISOString().slice(0, 10)
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Aegis AML - Technical Integration Reference (${tenantId})</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1c1917; background: #fff; line-height: 1.55; font-size: 13.5px;
    margin: 0; padding: 32px 36px; max-width: 880px;
  }
  h1 { font-size: 22px; margin: 0 0 2px; letter-spacing: -0.02em; }
  h2 { font-size: 15px; margin: 30px 0 10px; padding-bottom: 6px; border-bottom: 1px solid #e7e5e4; letter-spacing: -0.01em; }
  h3 { font-size: 13.5px; margin: 16px 0 8px; text-transform: capitalize; }
  h3 code, h3 { color: #1c1917; }
  p { margin: 8px 0; color: #44403c; }
  a { color: #047857; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12.5px; background: #f5f5f4; padding: 1px 5px; border-radius: 4px; }
  pre { background: #f8f8f7; border: 1px solid #e7e5e4; border-radius: 8px; padding: 14px 16px; overflow-x: auto; }
  pre code { background: none; padding: 0; font-size: 12px; line-height: 1.5; white-space: pre; }
  .sub { color: #78716c; font-size: 12.5px; margin: 0 0 4px; }
  .meta { color: #a8a29e; font-size: 12px; margin-top: 6px; }
  .kv { border-collapse: collapse; width: 100%; margin: 6px 0; }
  .kv td { padding: 6px 10px; border-bottom: 1px solid #f0efed; vertical-align: top; font-size: 13px; }
  .kv td:first-child { width: 190px; color: #57534e; font-family: ui-monospace, Menlo, monospace; font-size: 12.5px; }
  .grp { margin: 6px 0 14px; }
  .grp-blurb { font-weight: 400; color: #a8a29e; font-size: 12px; margin-left: 8px; }
  .field { border-top: 1px solid #f0efed; padding: 8px 0; page-break-inside: avoid; }
  .field-head { display: flex; align-items: center; gap: 10px; }
  .desc { color: #57534e; font-size: 12.5px; margin-top: 3px; }
  .eg { color: #a8a29e; font-size: 12px; margin-top: 2px; }
  .eg span { color: #57534e; font-family: ui-monospace, Menlo, monospace; }
  .tag { font-size: 10px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; padding: 1px 7px; border-radius: 999px; white-space: nowrap; }
  .tag.pii { background: #fef3c7; color: #92400e; }
  .tag.plain { background: #f5f5f4; color: #a8a29e; }
  .note { border-left: 3px solid #10b981; background: #f0fdf4; padding: 10px 14px; border-radius: 0 6px 6px 0; font-size: 12.5px; color: #3f6212; margin: 10px 0; }
  section { page-break-inside: avoid; }
  footer { margin-top: 34px; padding-top: 12px; border-top: 1px solid #e7e5e4; color: #a8a29e; font-size: 11.5px; }
  @page { margin: 16mm 14mm; }
  @media print { body { padding: 0; max-width: none; } a { color: #1c1917; } }
</style>
</head>
<body>
  <header>
    <h1>Aegis AML &mdash; Technical Integration Reference</h1>
    <p class="sub">How your transaction-monitoring system submits flagged alerts to Aegis, and how the finished report comes back.</p>
    <p class="meta">Tenant <code>${tenantId}</code> &nbsp;&middot;&nbsp; Generated ${generated} &nbsp;&middot;&nbsp; Base URL <code>${API_BASE}</code></p>
  </header>

  <section>
    <h2>1. Overview</h2>
    <p>Your TMS pushes each flagged transaction to Aegis over one authenticated HTTPS call. Aegis masks the PII, retrieves your AML policy, drafts a policy-cited Suspicious Transaction Report, and (once approved) delivers the finished report plus a PDF back to your systems via a signed webhook. Two calls total &mdash; nothing else is integrated.</p>
  </section>

  <section>
    <h2>2. Authentication</h2>
    <p>Every request carries two headers. Your API key is secret &mdash; keep it server-side and retrieve it from <b>Settings &rarr; Credentials</b> (it is never printed in this document).</p>
    <table class="kv">
      <tr><td>X-API-Key</td><td>Your secret key, format <code>sk-ae-...</code>. Server-to-server only.</td></tr>
      <tr><td>X-Tenant-ID</td><td>Your tenant id: <code>${tenantId}</code></td></tr>
      <tr><td>Content-Type</td><td><code>application/json</code></td></tr>
      <tr><td>Content-Length</td><td>Required. Send a buffered body (not chunked/streamed) or the request is rejected with <code>411</code>.</td></tr>
      <tr><td>Idempotency-Key</td><td>Optional but recommended (e.g. your <code>txn.ref_id</code>). A repeat of the same key returns <code>409</code> instead of creating a duplicate alert.</td></tr>
    </table>
  </section>

  <section>
    <h2>3. Endpoint</h2>
    <p><code>POST ${API_BASE}/api/v1/ingest/</code></p>
    <p class="sub">Submits one flagged transaction. Returns immediately; the SAR is drafted asynchronously and delivered by webhook.</p>
  </section>

  <section>
    <h2>4. Request body</h2>
    <p>The <b>STANDARD_FINTECH</b> shape &mdash; a JSON object with six sections. Fields marked <span class="tag pii">PII</span> are tokenized before any model sees them and re-hydrated only in your final report.</p>
    ${fieldRows()}
  </section>

  <section>
    <h2>5. Example request</h2>
    <pre><code>${esc(CURL(tenantId))}</code></pre>
  </section>

  <section>
    <h2>6. Response (200)</h2>
    <p class="sub">A successful ingest is acknowledged synchronously. <code>risk_score</code> is Aegis's own composite score; <code>&gt;= 75</code> triggers a SAR, otherwise the alert is cleared with no report.</p>
    <pre><code>${esc(RESPONSE)}</code></pre>
    <h3>Error responses</h3>
    <table class="kv">
      <tr><td>400</td><td>Malformed JSON or non-object body.</td></tr>
      <tr><td>401 / 403</td><td>Missing or invalid <code>X-API-Key</code> / <code>X-Tenant-ID</code>.</td></tr>
      <tr><td>409</td><td>Duplicate submission (idempotency key already processed). Includes the original alert id.</td></tr>
      <tr><td>411</td><td>Missing <code>Content-Length</code> (body was streamed/chunked).</td></tr>
      <tr><td>413</td><td>Payload too large.</td></tr>
      <tr><td>429</td><td>Rate limited &mdash; honor <code>Retry-After</code>.</td></tr>
    </table>
  </section>

  <section>
    <h2>7. Report delivery (webhook)</h2>
    <p>When the SAR is approved, Aegis POSTs it to the callback URL you configure in <b>Settings &rarr; Webhook</b>. Verify authenticity by recomputing the HMAC over the raw request body with your webhook secret and comparing it to <code>X-Aegis-Signature</code>.</p>
    <pre><code>${esc(WEBHOOK)}</code></pre>
    <div class="note">The report carries the STR narrative, the indicators that fired, a structured recommended action, and the STR PDF as <code>pdf_base64</code> &mdash; so you keep your own copy of the filing and never depend on Aegis being reachable to retrieve it.</div>
  </section>

  <section>
    <h2>8. Security &amp; PII handling</h2>
    <p>All PII fields are tokenized before retrieval, scoring, or drafting &mdash; the model never sees raw names, accounts, or device identifiers. PII is re-hydrated only into your tenant-facing report. Transport is HTTPS end to end; the webhook is HMAC-signed. Keep your API key and webhook secret in a server-side secret store and rotate the API key from <b>Settings &rarr; Credentials</b> if it is ever exposed.</p>
  </section>

  <footer>
    Aegis AML &mdash; Technical Integration Reference for tenant ${tenantId}. Generated ${generated}. For questions contact your Aegis onboarding engineer.
  </footer>
</body>
</html>`
}
