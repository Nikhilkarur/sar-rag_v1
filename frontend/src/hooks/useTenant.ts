import { useQuery } from '@tanstack/react-query'
import * as tenantApi from '../api/tenant'

export function useCredentials() {
  return useQuery({ queryKey: ['credentials'], queryFn: tenantApi.getCredentials })
}

export function useWebhookConfig() {
  return useQuery({ queryKey: ['webhook-config'], queryFn: tenantApi.getWebhookConfig })
}

export function useWebhookEvents(enabled = true) {
  return useQuery({
    queryKey: ['webhook-events'],
    queryFn: tenantApi.getWebhookEvents,
    refetchInterval: () => (document.visibilityState === 'visible' ? 3000 : false),
    enabled,
  })
}

export function useSchemas() {
  return useQuery({ queryKey: ['schemas'], queryFn: tenantApi.getSchemas })
}

export function useLLMConfig() {
  return useQuery({ queryKey: ['llm-config'], queryFn: tenantApi.getLLMConfig })
}

export function useUsage() {
  return useQuery({ queryKey: ['usage'], queryFn: tenantApi.getUsage })
}

export function useApprovedSars() {
  return useQuery({ queryKey: ['approved-sars'], queryFn: tenantApi.listApprovedSars })
}
