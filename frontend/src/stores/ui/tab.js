import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useTab = defineStore('app.ui.tab', () => {
  const active = ref('batch')

  return { active }
})
