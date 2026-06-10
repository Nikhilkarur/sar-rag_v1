import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as alertsApi from '../api/alerts'
import type { SimulatorScenario } from '../types'

export function useAlerts(poll = true) {
  return useQuery({
    queryKey: ['alerts'],
    queryFn: alertsApi.listAlerts,
    refetchInterval: poll ? 5000 : false,
  })
}

export function useAlert(id: string | undefined) {
  return useQuery({
    queryKey: ['alerts', id],
    queryFn: () => alertsApi.getAlert(id!),
    enabled: !!id,
  })
}

export function useSubmitTestAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (scenario: SimulatorScenario) => alertsApi.submitTestAlert(scenario),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })
}

export function useUpdateDraft(alertId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (text: string) => alertsApi.updateDraft(alertId, text),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts', alertId] }),
  })
}

export function useApproveAlert(alertId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (officerName: string) => alertsApi.approveAlert(alertId, officerName),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
      qc.invalidateQueries({ queryKey: ['webhook-events'] })
      qc.invalidateQueries({ queryKey: ['usage'] })
      qc.invalidateQueries({ queryKey: ['approved-sars'] })
    },
  })
}

export function useRejectAlert(alertId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reason: string) => alertsApi.rejectAlert(alertId, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })
}
