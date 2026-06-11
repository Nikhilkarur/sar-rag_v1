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

export interface SARDraft {
  id: string
  draft_text: string
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
  delta_alerts: number
  sars_approved: number
  delta_sars: number
  pending_review: number
  false_positives_cleared: number
  avg_review_time_minutes: number
  daily_breakdown: { date: string; alerts: number; approved: number }[]
  monthly_sars: { month: string; sars: number }[]
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
