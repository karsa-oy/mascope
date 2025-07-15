import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useSplit = defineStore('app.ui.split', () => {
  const hsplit = JSON.parse(localStorage.getItem('mascope-dashboard-split')) ?? [25, 75]
  const left = ref(hsplit[0])
  const right = ref(hsplit[1])

  const vsplit = JSON.parse(localStorage.getItem('mascope-browser-split')) ?? [25, 75]
  const top = ref(vsplit[0])
  const bottom = ref(vsplit[1])

  return {
    left,
    right,
    top,
    bottom
  }
})
