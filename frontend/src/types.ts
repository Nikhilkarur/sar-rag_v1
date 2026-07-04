export type Role = 'SUPER_ADMIN' | 'TENANT_ADMIN' | 'COMPLIANCE_OFFICER'

export type TenantStatus = 'PENDING_VERIFICATION' | 'ACTIVE' | 'REJECTED' | 'SUSPENDED'

/** Statuses as the API serves them (backend pipeline statuses are mapped
    to these in routers/alerts.py::_public_status before leaving the server). */
export type AlertStatus =
  | 'PENDING_INGESTION'
  | 'PROCESSING'
  | 'PENDING_REVIEW'
  | 'COMPLETED_CLEAN'
  | 'PROCESSING_FAILED'
  | 'APPROVED'
  | 'REJECTED'
  | 'DELIVERED'

export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW'

export interface TenantInfo {
  id: string
  name: string
  status: TenantStatus
  tenantIdPublic: string
  companyType: string
  rejectionReason?: string
}

export interface User {
  id: string
  email: string
  fullName: string
  role: Role
  tenant: TenantInfo | null
}

export interface AlertSummary {
  id: string
  transaction_id: string
  transaction_amount: number
  transaction_currency: string
  transaction_type: string
  transaction_direction: 'DEBIT' | 'CREDIT'
  transaction_timestamp: string
  risk_score: number
  status: AlertStatus
  triggered_rules: string[]
  source: 'API' | 'SIMULATOR'
  /** Portal test alerts — excluded from compliance metrics server-side */
  is_synthetic: boolean
  created_at: string
}

export interface ComplianceRule {
  rule_id: string
  rule_name: string
  triggered: boolean
  confidence: Confidence
  evidence: {
    field?: string
    value?: string
    explanation?: string
  }
}

export interface SARKeyIndicator {
  indicator: string
  regulation: string
  description: string
}

export interface SARStructured {
  key_indicators: SARKeyIndicator[]
  recommended_action: string
}

export interface SARDraft {
  id: string
  draft_text: string
  /** Structured half of the SAR (indicators + recommended action); may be null on older drafts */
  draft_structured: SARStructured | null
  llm_model: string
  generation_latency_ms: number
  officer_edit_count: number
  last_edited_at: string | null
  created_at: string
}

export interface AlertDetail extends AlertSummary {
  masked_payload: Record<string, string | number>
  raw_payload: Record<string, unknown>
  compliance: {
    overall_risk: 'HIGH' | 'MEDIUM' | 'LOW'
    triggered_rules: ComplianceRule[]
    clean_checks: { rule_id: string; rule_name: string; triggered: boolean }[]
  }
  /** null until the pipeline has generated a draft (clean/low-risk alerts never get one) */
  sar_draft: SARDraft | null
}

export interface WebhookEvent {
  id: string
  received_at: string
  hmac_valid: boolean
  status: 'DELIVERED' | 'FAILED'
  http_status: number | null
  destination: string
  payload: Record<string, unknown>
}

export interface WebhookConfig {
  callback_url: string | null
  use_internal_sink: boolean
  internal_sink_url: string
  secret_prefix: string | null
  last_tested_at: string | null
  last_test_status: 'SUCCESS' | 'FAILED' | null
}

export interface SchemaPreset {
  template_key: string
  name: string
  description: string
  key_fields: string[]
}

export interface LLMConfig {
  provider: 'GROQ'
  model_name: string
  sar_template_style: 'NARRATIVE' | 'STRUCTURED' | 'BOTH'
  total_tokens_used: number
  total_requests: number
}

export interface UsageStats {
  alerts_ingested: number
  delta_alerts: number | null
  sars_approved: number
  delta_sars: number | null
  pending_review: number
  false_positives_cleared: number
  avg_review_time_minutes: number
  daily_breakdown: { date: string; alerts: number; approved: number }[]
  monthly_sars: { month: string; sars: number }[]
  outcome_monthly: { month: string; label: string; filed: number; review: number; cleared: number; failed: number }[]
  typology: { rule_id: string; rule_name: string; count: number }[]
  tokens_used: number
  total_requests: number
  failed_count: number
  amount_screened_inr: number
  amount_flagged_inr: number
}

export interface ApprovedSAR {
  sar_id: string
  transaction_id: string
  amount: number
  approved_by: string
  approved_at: string
}

export interface VerificationItem {
  id: string
  name: string
  company_type: string
  cin: string
  website: string
  admin_name: string
  admin_email: string
  admin_phone: string
  created_at: string
}

export interface CustomerItem {
  id: string
  name: string
  tenant_id_public: string
  company_type: string
  status: TenantStatus
  total_alerts: number
  approved_sars: number
  joined_at: string
  last_active_at: string
  cin: string
  website: string
  admin_email: string
}

export interface ApiLogItem {
  id: string
  tenant_name: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  endpoint: string
  status_code: number
  latency_ms: number
  created_at: string
}

export interface GroqUsage {
  total_tokens_all_time: number
  total_tokens_this_month: number
  estimated_cost_usd_this_month: number
  per_tenant: {
    tenant_id: string
    tenant_name: string
    tokens_this_month: number
    total_requests: number
    est_cost: number
    last_active: string
  }[]
}

export interface PlatformBilling {
  currency: string
  cycle_start: string
  free_sars: number
  price_per_sar_inr: number
  total_amount_due_inr: number
  total_sars_this_cycle: number
  client_count: number
  billable_client_count: number
  comped_client_count: number
  clients: {
    tenant_id: string
    tenant_id_public: string
    name: string
    status: TenantStatus
    plan: string
    sars_this_cycle: number
    billable_sars: number
    amount_due_inr: number
    special_free_access: boolean
    note: string | null
  }[]
}

export type SimulatorScenario =
  | 'STRUCTURING'
  | 'RAPID_MOVEMENT'
  | 'HIGH_RISK_TYPE'
  | 'VELOCITY'
  | 'DEFAULT'

export interface Credentials {
  tenant_id_public: string
  api_key_prefix: string
  api_key_last_rotated: string | null
}

export interface PlatformOverview {
  kpis: {
    tenants_active: number
    tenants_suspended: number
    tenants_pending: number
    total_alerts: number
    alerts_this_month: number
    total_sars: number
    sars_this_month: number
    failed_total: number
    tokens_this_month: number
    llm_cost_this_month: number
    api_requests_7d: number
    api_error_rate_7d: number
    ingest_requests_7d: number
  }
  monthly: { month: string; label: string; filed: number; review: number; cleared: number; failed: number }[]
  typology: { rule_id: string; rule_name: string; count: number }[]
  api_daily: { date: string; label: string; total: number; ok: number; client_err: number; server_err: number }[]
}

export interface BillingPlan {
  id: string
  name: string
  included_sars: number | null // null = unlimited / per-SAR
  monthly_inr: number | null // null = per-SAR / custom
  per_sar_inr: number | null // null = custom
  effective_per_sar_inr: number
  model: string
  description: string
  features: string[]
}

export interface Billing {
  cycle_start: string
  sars_this_cycle: number
  tokens_this_cycle: number
  free_sars: number
  free_tokens: number
  price_per_sar_inr: number
  premium_price_per_sar_inr: number
  standard_model: string
  premium_model: string
  billable_sars: number
  amount_due_inr: number
  within_free_tier: boolean
  special_free_access?: boolean
  special_access_label?: string | null
  currency: string
  plans: BillingPlan[]
  current_plan: string
  recommended_plan: string | null
}
