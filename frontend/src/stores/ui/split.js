import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useSplit = defineStore('app.ui.split', () => {
  const split = JSON.parse(localStorage.getItem('mascope-dashboard-split')) ?? [25, 75]
  const left = ref(split[0])
  const right = ref(split[1])

  return {
    left,
    right
  }
})
