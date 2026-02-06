import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const usePeakScroller = defineStore('browser.peak.scroller', () => {
  // Component refs and data getters bound from PaneBrowserPeak
  const tableRef = ref(null)
  const getPeaks = ref(() => [])
  const getSortConfig = ref(() => ({ sortField: 'height', sortOrder: -1 }))

  /**
   * Get sorted/filtered data matching DataTable's actual display order.
   * Prefers DataTable's internal processedData, falls back to manual sorting.
   */
  const sortedPeaks = computed(() => {
    // Use DataTable's internal sorted data if available
    if (tableRef.value?.processedData) {
      return tableRef.value.processedData
    }

    // Fallback: manually sort using current config
    const peaks = getPeaks.value()
    const { sortField, sortOrder } = getSortConfig.value()

    if (!sortField) return peaks

    return [...peaks].sort((a, b) => {
      // Navigate nested properties (e.g., 'match.match_score')
      const getValue = (obj, path) => path.split('.').reduce((val, key) => val?.[key], obj)
      const aVal = getValue(a, sortField)
      const bVal = getValue(b, sortField)

      // Handle null/undefined
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1

      // Apply sort direction
      const order = sortOrder || -1
      return aVal < bVal ? -1 * order : aVal > bVal ? 1 * order : 0
    })
  })

  /**
   * Get VirtualScroller component instance for native scroll methods.
   */
  function getScrollerInstance() {
    const scrollerEl = tableRef.value?.$el?.querySelector('.p-virtualscroller')
    return scrollerEl?.__vnode?.component?.exposed || scrollerEl?.__vnode?.component?.ctx
  }

  let scrollLock = false

  /**
   * Scroll to peak using VirtualScroller's native scrollInView method.
   * Uses display index from sorted data to match visual position.
   */
  async function scrollToPeak(peakId) {
    if (!scrollLock && peakId && tableRef.value) {
      scrollLock = true

      // Allow DOM to update
      await new Promise((resolve) => setTimeout(resolve, 0))

      // Find peak's index in display order
      const displayIndex = sortedPeaks.value.findIndex((p) => p.peak_id === peakId)
      if (displayIndex === -1) {
        scrollLock = false
        return
      }

      const scroller = getScrollerInstance()

      if (scroller?.scrollInView) {
        // Use native VirtualScroller method (minimal scroll)
        scroller.scrollInView(displayIndex)
      } else {
        // Fallback: manual scroll calculation
        const container = tableRef.value.$el.querySelector('.p-virtualscroller')
        if (container) {
          const itemSize = 35.5
          container.scrollTop = displayIndex * itemSize

          setTimeout(() => {
            document.getElementById(peakId)?.scrollIntoView({
              behavior: 'smooth',
              block: 'nearest'
            })
          }, 100)
        }
      }

      // Release lock after animation completes
      setTimeout(() => {
        scrollLock = false
      }, 300)
    }
  }

  /**
   * Bind component refs and data from PaneBrowserPeak.
   * Pass getter functions to maintain reactivity across component updates.
   */
  function bind(table, peaksGetter, sortConfigGetter) {
    tableRef.value = table
    getPeaks.value = peaksGetter || (() => [])
    getSortConfig.value = sortConfigGetter || (() => ({ sortField: 'height', sortOrder: -1 }))
  }

  return {
    bind,
    scrollToPeak
  }
})
