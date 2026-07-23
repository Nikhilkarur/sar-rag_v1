import client from './client'
import type { WebhookConfig, LLMConfig, UsageStats, WebhookEvent, SchemaPreset, ApprovedSAR, Billing } from '../types'

export async function getBilling(): Promise<Billing> {
  const { data } = await client.get('/tenant/billing')
  return data
}

export async function getCredentials(): Promise<{ api_key_prefix: string; tenant_id_public: string }> {
  const { data } = await client.get('/tenant/credentials')
  return data
}

export async function revealApiKey(): Promise<{ api_key: string }> {
  const { data } = await client.get('/tenant/credentials/reveal')
  return data
}

export async function rotateApiKey(): Promise<{ new_api_key: string; api_key_prefix: string }> {
  const { data } = await client.post('/tenant/credentials/rotate')
  return data
}

export async function getWebhookConfig(): Promise<WebhookConfig> {
  const { data } = await client.get('/tenant/webhook')
  return data
}

export async function updateWebhookConfig(payload: { use_internal_sink: boolean; callback_url?: string }): Promise<WebhookConfig> {
  const { data } = await client.put('/tenant/webhook', payload)
  return data
}

export async function sendTestWebhook(): Promise<{ status: string; latency_ms: number; message?: string }> {
  const { data } = await client.post('/tenant/webhook/test')
  return data
}

export async function getWebhookEvents(): Promise<WebhookEvent[]> {
  const { data } = await client.get('/tenant/webhook/events')
  return data
}

export interface PolicyInfo {
  client_id: string
  policy_present: boolean
  policy_path: string | null
  chunks_indexed: number | null
}

export async function getPolicyInfo(): Promise<PolicyInfo> {
  const { data } = await client.get('/documents/')
  return data
}

export interface PolicyUploadResult {
  status: string
  client_id: string
  stored_path: string
  original_filename: string
  chunks_indexed: number
}

export async function uploadPolicy(file: File): Promise<PolicyUploadResult> {
  const form = new FormData()
  form.append('file', file)
  // axios 1.x fills in the multipart boundary when Content-Type is multipart/form-data
  const { data } = await client.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deletePolicy(): Promise<{ status: string; deleted_client: string }> {
  const { data } = await client.delete('/documents/')
  return data
}

export async function getSchemas(): Promise<SchemaPreset[]> {
  const { data } = await client.get('/tenant/schemas')
  return data
}

export async function selectSchema(templateKey: string): Promise<SchemaPreset> {
  const { data } = await client.post('/tenant/schemas/select-preset', { template_key: templateKey })
  return data
}

export async function getLLMConfig(): Promise<LLMConfig> {
  const { data } = await client.get('/tenant/llm-config')
  return data
}

export async function updateLLMConfig(style: LLMConfig['sar_template_style']): Promise<LLMConfig> {
  const { data } = await client.put('/tenant/llm-config', { sar_template_style: style })
  return data
}

export async function getUsage(): Promise<UsageStats> {
  const { data } = await client.get('/tenant/usage')
  return data
}

export async function listApprovedSars(): Promise<ApprovedSAR[]> {
  const { data } = await client.get('/tenant/sars')
  return data
}

/** Fetch a SAR PDF as a blob. The file is served at /files/sar/<id>.pdf (root, not
    under /api/v1) and is now tenant-authenticated, so we hit it through the same axios
    client (absolute URL bypasses baseURL; the interceptor still attaches the JWT). */
const FILES_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/api\/v1\/?$/, '')
export async function downloadSarPdf(sarId: string): Promise<Blob> {
  const { data } = await client.get(`${FILES_BASE}/files/sar/${sarId}.pdf`, { responseType: 'blob' })
  return data
}
