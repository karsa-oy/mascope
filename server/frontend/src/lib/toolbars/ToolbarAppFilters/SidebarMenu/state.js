import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useSidebarMenu = defineStore('menu.sidebar', () => {
  const open = ref(false)
  const tab = ref('workspaces')

  return {
    open,
    tab
  }
})
