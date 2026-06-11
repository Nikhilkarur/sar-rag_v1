import client from './client'
import type { WebhookConfig, LLMConfig, UsageStats, WebhookEvent, SchemaPreset, ApprovedSAR } from '../types'

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
