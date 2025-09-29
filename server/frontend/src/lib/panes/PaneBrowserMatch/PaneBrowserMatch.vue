<script setup>
import { watch, computed, provide } from 'vue'

import { useWindowSize } from '@vueuse/core'

import { useApp } from '@/stores'

import MatchCollectionTable from './MatchCollectionTable.vue'
import MatchIonTable from './MatchIonTable.vue'

const app = useApp()

/**
 * Utility function to allow scrolling to matches in the watchers below
 * Lock prevents race conditions when focusing propagates through hierarchy,
 * ensuring only the initially focused level is scrolled to.
 */
let scrollLock = false
const scrollToMatch = (target) => {
  if (!scrollLock && target) {
    scrollLock = true
    setTimeout(() => {
      const element = document.getElementById(
        `match-${target.target_collection_id || target.target_ion_id}`
      )
      element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      scrollLock = false
    }, 300)
  }
}

/**
 * Watch collection focus changes
 * Clear visualized matches when collection changes or is deselected
 */
watch(
  () => app.data.match.collection.focused,
  (collection, oldCollection) => {
    const collectionChanged =
      collection?.target_collection_id !== oldCollection?.target_collection_id

    // Clear visualized match on collection change or deselection
    if (!collection || collectionChanged) {
      app.data.match.visualized.clear()
    }

    // Clear ion selection when collection changes (but not when first selecting)
    if (collectionChanged && oldCollection) {
      app.data.match.ion.unfocus()
    }

    if (collection) {
      scrollToMatch(collection)
    }
  }
)

/**
 * Watch ion focus changes
 */
watch(
  () => app.data.match.ion.focused,
  (ion) => {
    if (ion) {
      scrollToMatch(ion)
    } else {
      // Clear visualized match when ion is unfocused
      app.data.match.visualized.clear()
    }
  }
)

/**
 * Watch sample changes - re-scroll to current selection
 */
watch(
  () => app.data.sample.focused,
  () => {
    const currentSelection = app.data.match.ion.focused ?? app.data.match.collection.focused
    if (currentSelection) {
      scrollToMatch(currentSelection)
    }
  }
)

// Calculate table height for virtual scrolling
const { height } = useWindowSize()
const PADDING = 100
const BOTTOM_OFFSET = 50
const tableHeight = computed(
  () => ((height.value - PADDING) * app.ui.split.bottom) / 100 - BOTTOM_OFFSET
)
provide('match-table-height', tableHeight)
</script>

<template>
  <MatchIonTable v-if="app.data.match.collection.focused" />
  <MatchCollectionTable v-else />
</template>
