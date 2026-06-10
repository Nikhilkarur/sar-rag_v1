import client from './client'
import type { AlertDetail } from '../types'

export async function listAlerts(): Promise<AlertDetail[]> {
  const { data } = await client.get('/alerts/queue')
  return data
}

export async function getAlert(id: string): Promise<AlertDetail> {
  const { data } = await client.get(`/alerts/queue/${id}`)
  return data
}

export async function updateDraft(id: string, text: string): Promise<void> {
  await client.put(`/alerts/queue/${id}/draft`, { draft_text: text })
}

export async function previewRehydrated(id: string): Promise<string> {
  const { data } = await client.get(`/alerts/queue/${id}/preview-rehydrated`)
  return data.rehydrated_text
}

export async function approveAlert(id: string, overrides?: any): Promise<void> {
  await client.post(`/alerts/queue/${id}/approve`, overrides || {})
}

export async function rejectAlert(id: string, reason: string): Promise<void> {
  await client.post(`/alerts/queue/${id}/reject`, { reason })
}

export async function submitTestAlert(scenario: string): Promise<string> {
  const { data } = await client.post('/alerts/simulator/submit-test-alert', { scenario })
  return data.alert_id
}
