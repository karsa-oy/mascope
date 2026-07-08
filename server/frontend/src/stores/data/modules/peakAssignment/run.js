import { computed, watch } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { useData } from '@/lib/store'

import { useSample } from '../sample'

// Peak assignment RUNS for the focused sample.
//
// One row per assignment run over the sample, newest first. The focused run is
// the one currently being viewed; usePeakAssignment reads its assignments. See
// docs/dev/peak_assignment_frontend.md.
export const usePeakAssignmentRun = defineStore('app.data.peakAssignment.run', () => {
  const name = 'peak_assignment_run'
  const key = 'peak_assignment_run_id'

  const data = useData(
    name,
    ({ sample_item_id }) => {
      if (!sample_item_id) return []
      return api.http.get(`/peak-assignments/sample/${sample_item_id}/runs`, {
        use: 'read',
        type: 'load_peak_assignment_runs'
      })
    },
    {
      key,
      deps: () => ({ sample_item_id: useSample().focusedId }),
      selection: true,
      // The backend emits peak_assignment_reload when a run finalizes (mirrors
      // match_reload); the useData events framework re-syncs the run list.
      events: ['peak_assignment_reload']
    }
  )

  // Runs are returned newest-first, so the first completed run is the latest.
  const latestCompleted = computed(
    () => data.list.value.find((run) => run.status === 'completed') ?? null
  )

  // Default the view to the latest completed run on initial load and on sample
  // switch. The run list holds only the focused sample's runs, so a focused id
  // that is absent from it is either empty or a stale carry-over from the
  // previous sample (selection persists) -- in both cases re-focus the latest.
  // An explicit pick of an older run of the SAME sample stays in the list, so it
  // is left alone; live completion of a new run is likewise not yanked into
  // focus (that affordance belongs to the Assignments browser).
  watch(
    [latestCompleted, () => data.list.value],
    ([run]) => {
      const focusedInList = data.list.value.some(
        (r) => r.peak_assignment_run_id === data.focusedId.value
      )
      if (run && !focusedInList) data.focus(run)
    },
    { immediate: true }
  )

  // Launch a new assignment run. Completion arrives via the
  // peak_assignment_reload event (see events above); the progress bar is driven
  // by the assign_sample_peaks user notification (PaneProgress) meanwhile.
  const assign = (sampleItemId, config = null) =>
    api.http.post(
      `/peak-assignments/sample/${sampleItemId}/assign`,
      { config },
      {
        use: 'process',
        type: 'assign_sample_peaks'
      }
    )

  return {
    ...data,
    latestCompleted,
    assign
  }
})
