import { ref, onBeforeUnmount } from 'vue'
import { defineStore } from 'pinia'

export const useChart = defineStore('app.ui.chart', () => {
  const list = ref([])

  function register(chart) {
    list.value.push(chart)
    const destructor = () =>
      onBeforeUnmount(() => {
        list.value = list.value.filter(({ id }) => chart.id !== id)
      })
    return destructor
  }

  function clear() {
    list.value.forEach((chart) => {
      chart.clear()
      console.log(`[chart]: cleared ${chart.name} data`)
    })
  }

  return {
    list,
    register,
    clear
  }
})
