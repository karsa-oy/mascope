import { ref, useTemplateRef } from 'vue'
import { defineStore } from 'pinia'

import { useBatchContext } from './batchContext.js'
import { useSampleContext } from './sampleContext.js'

export const useCustomizerPopover = defineStore('browser.sample.customizer', () => {
  const batchContext = useBatchContext()
  const sampleContext = useSampleContext()

  const popover = ref()
  const config = ref({})

  function show(event) {
    batchContext.hide()
    sampleContext.hide()
    popover.value?.show(event)
  }

  function hide() {
    popover.value?.hide()
  }

  return {
    show,
    hide,
    popover,
    config
  }
})
