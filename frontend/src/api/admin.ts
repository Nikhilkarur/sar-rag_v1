import client from './client'
import type { VerificationItem, CustomerItem, ApiLogItem, GroqUsage, PlatformOverview, PlatformBilling } from '../types'

export async function getPlatformOverview(): Promise<PlatformOverview> {
  const { data } = await client.get('/admin/overview')
  return data
}

export async function listVerifications(): Promise<VerificationItem[]> {
  const { data } = await client.get('/admin/verifications')
  return data
}

export async function approveTenant(id: string): Promise<{ tenant_id: string; status: string; api_key: string }> {
  const { data } = await client.post(`/admin/tenants/${id}/approve`)
  return data
}

export async function rejectTenant(id: string, reason: string): Promise<void> {
  await client.post(`/admin/tenants/${id}/reject`, { reason })
}

export async function listCustomers(): Promise<CustomerItem[]> {
  const { data } = await client.get('/admin/tenants')
  return data
}

export async function suspendTenant(id: string): Promise<void> {
  await client.post(`/admin/tenants/${id}/suspend`)
}

export async function reinstateTenant(id: string): Promise<void> {
  await client.post(`/admin/tenants/${id}/reinstate`)
}

export async function listApiLogs(): Promise<ApiLogItem[]> {
  const { data } = await client.get('/admin/logs')
  return data
}

export async function getGroqUsage(): Promise<GroqUsage> {
  const { data } = await client.get('/admin/groq-usage')
  return data
}

export async function getPlatformBilling(): Promise<PlatformBilling> {
  const { data } = await client.get('/admin/billing')
  return data
}
