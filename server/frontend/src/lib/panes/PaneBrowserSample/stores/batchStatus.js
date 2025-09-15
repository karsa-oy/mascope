import { defineStore } from 'pinia'

export const useBatchStatus = defineStore('browser.sample.batchStatus', () => {
  const config = {
    rematch: {
      type: 'button',
      icon: 'ph ph-arrows-clockwise',
      tooltip:
        'Sample batch has been modified, matches may be out of date. Click to refresh this batch matches',
      severity: 'secondary'
    },
    ready: {
      type: 'button',
      icon: 'ph ph-check-circle',
      tooltip: 'Sample batch matches are up to date',
      severity: 'primary',
      disabled: true
    },
    processing: {
      type: 'spinner',
      tooltip: 'Sample batch is processing, computing matches'
    }
  }

  return { config }
})
