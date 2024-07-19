import { reactive } from 'vue'
import { defineStore } from 'pinia'

export const useSplit = defineStore('app.ui.split', () => {
  const [left, right] = JSON.parse(localStorage.getItem('mascope-dashboard-split')) ?? [25, 75]
  const split = reactive({
    left,
    right
  })

  return split
})
