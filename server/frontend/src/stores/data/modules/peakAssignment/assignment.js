import { computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { useData } from '@/lib/store'

import { useSample } from '../sample'
import { usePeakAssignmentRun } from './run'

// Peak ASSIGNMENTS for the focused sample + focused run.
//
// One row per observed peak, keyed by sample_peak_id (unique within a run and
// the join key back to the peak list). Exposes byPeakId (consumed by the peak
// ledger and the annotated spectrum) and a tier histogram. See
// docs/dev/peak_assignment_frontend.md.
export const usePeakAssignment = defineStore('app.data.peakAssignment', () => {
  const name = 'peak_assignment'
  const key = 'sample_peak_id'

  const data = useData(
    name,
    ({ sample_item_id, peak_assignment_run_id }) => {
      if (!sample_item_id || !peak_assignment_run_id) return []
      return api.http.get(`/peak-assignments/sample/${sample_item_id}`, {
        params: { peak_assignment_run_id },
        use: 'read',
        type: 'load_peak_assignments'
      })
    },
    {
      key,
      deps: () => ({
        sample_item_id: useSample().focusedId,
        peak_assignment_run_id: usePeakAssignmentRun().focusedId ?? null
      }),
      selection: true
    }
  )

  // Run metadata for the current view. The shared `read` handler unwraps the
  // response to its `data` field, dropping the {run, data} envelope's `run`, so
  // we take run metadata from the run store instead of the assignments call.
  const run = computed(() => usePeakAssignmentRun().focused)

  // Peak-join map keyed by String(sample_peak_id): the peak list keys peaks by
  // `peak_id`, which the engine stringifies into `sample_peak_id`. Consumed by
  // PaneBrowserPeak (the ledger) and ChartSampleSpectrum (tier coloring).
  const byPeakId = computed(() => {
    const map = new Map()
    for (const record of data.list.value) {
      map.set(String(record.sample_peak_id), record)
    }
    return map
  })

  // Look up the assignment for a peak by its peak_id.
  const forPeak = (peakId) =>
    peakId == null ? null : (byPeakId.value.get(String(peakId)) ?? null)

  // Confidence-tier histogram for the ledger header and the run summary. Roles
  // reagent/artifact are counted separately (orthogonal to tier).
  const tierCounts = computed(() => {
    const counts = {
      identified: 0,
      candidate: 0,
      below_assignability: 0,
      unassigned: 0,
      reagent: 0
    }
    for (const record of data.list.value) {
      if (record.role === 'reagent' || record.role === 'artifact') {
        counts.reagent += 1
      } else {
        counts[record.tier] = (counts[record.tier] ?? 0) + 1
      }
    }
    return counts
  })

  return {
    ...data,
    run,
    byPeakId,
    forPeak,
    tierCounts
  }
})
