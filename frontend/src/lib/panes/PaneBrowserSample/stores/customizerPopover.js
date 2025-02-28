import { ref } from 'vue'
import { defineStore } from 'pinia'

import { useBatchContextMenu } from './batchContextMenu.js'
import { useSampleContextMenu } from './sampleContextMenu.js'

export const useCustomizerPopover = defineStore('browser.sample.customizer', () => {
  const batchContextMenu = useBatchContextMenu()
  const sampleContextMenu = useSampleContextMenu()

  const popover = ref()
  const config = ref({})

  function show(event) {
    batchContextMenu.hide()
    sampleContextMenu.hide()
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
