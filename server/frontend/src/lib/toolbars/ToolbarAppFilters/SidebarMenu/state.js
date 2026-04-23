import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useSidebarMenu = defineStore('menu.sidebar', () => {
  const open = ref(false)
  const tab = ref('datasets')

  return {
    open,
    tab
  }
})
