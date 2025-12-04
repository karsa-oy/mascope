import { ref, onBeforeUnmount } from 'vue'
import { defineStore } from 'pinia'

export const useChart = defineStore('app.ui.chart', () => {
  const list = ref([])

  function register(chart) {
    list.value.push(chart)
    const destructor = () =>
      onBeforeUnmount(() => {
        console.debug(`📊 [${chart.name}]: unregistering chart`)
        list.value = list.value.filter(({ id }) => chart.id !== id)
      })
    return destructor
  }

  function clear() {
    list.value.forEach((chart) => {
      console.debug(`📊 [${chart.name}]: clearing`)
      chart.clear()
    })
  }

  return {
    list,
    register,
    clear
  }
})
