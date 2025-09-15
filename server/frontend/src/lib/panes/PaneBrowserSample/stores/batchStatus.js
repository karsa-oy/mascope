import { defineStore } from 'pinia'

export const useBatchStatus = defineStore('browser.sample.batchStatus', () => {
  const config = {
    rematch: {
      type: 'button',
      icon: 'ph ph-arrows-clockwise',
      tooltip: 'Batch has been modified, matches may be out of date. Click to refresh matches',
      severity: 'secondary'
    },
    ready: {
      type: 'button',
      icon: 'ph ph-check-circle',
      tooltip: 'Batch is up to date',
      severity: 'primary',
      disabled: true
    },
    processing: {
      type: 'spinner',
      tooltip: 'Computing matches for the batch'
    }
  }

  return { config }
})
