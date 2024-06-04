import { ref, onBeforeUnmount } from 'vue'
import { defineStore } from 'pinia'

export const useDashboard = defineStore('dashboard', () => {
  const charts = ref([])
  const tab = ref('batch')

  function register(chart) {
    charts.value.push(chart)
    const destructor = () =>
      onBeforeUnmount(() => {
        charts.value = charts.value.filter(({ id }) => chart.id !== id)
      })
    return destructor
  }

  function clear() {
    charts.value.forEach((chart) => {
      chart.clear()
      console.log(`[Dash]: cleared ${chart.name} data`)
    })
  }

  return {
    tab,
    charts,
    register,
    clear
  }
})
