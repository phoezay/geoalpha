import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { RegionStatus } from '../../components/ui/AsyncRegion'
import { api, type RunDetail, type Stage, type StageKey } from '../../lib/api'
import { runKey } from '../../lib/runStream'

/** Agent stages can legitimately take minutes; past this the region shows an error. */
export const REPORT_TIMEOUT_MS = 20 * 60_000

export function getStage(run: RunDetail, key: StageKey): Stage {
  return run.stages.find((s) => s.key === key)!
}

export function stageRegionStatus(stage: Stage | undefined, runStatus: RunDetail['status']): RegionStatus {
  if (!stage) return 'loading'
  switch (stage.status) {
    case 'done':
      return 'ready'
    case 'failed':
      return 'error'
    case 'skipped':
    case 'unavailable':
      return 'empty'
    default:
      // A pending stage of a run that has stopped will not progress without a retry.
      return runStatus === 'failed' || runStatus === 'interrupted' ? 'error' : 'loading'
  }
}

export function stageError(stage: Stage | undefined, run: RunDetail): string {
  if (stage?.error) return stage.error
  if (run.status === 'interrupted') return 'The run was interrupted before this step ran.'
  return 'An earlier step failed, so this one did not run.'
}

export function useRetryRun(runId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (mode: 'resume' | 'fresh') => api.retryRun(runId, mode),
    onSuccess: (run) => {
      qc.setQueryData(runKey(run.id), run)
      void qc.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

