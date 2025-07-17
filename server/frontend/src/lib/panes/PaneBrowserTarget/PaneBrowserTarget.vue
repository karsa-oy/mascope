<script setup>
import { watch, computed, provide } from 'vue'

import { useWindowSize } from '@vueuse/core'

import { useApp } from '@/stores'

import TargetCollectionTable from './TargetCollectionTable.vue'
import TargetCompoundTable from './TargetCompoundTable.vue'
import TargetIonTable from './TargetIonTable.vue'
import TargetIsotopeTable from './TargetIsotopeTable.vue'

const app = useApp()

// trigger visualization on match focus
watch(
  () =>
    app.data.match.isotope.focused ?? app.data.match.ion.focused ?? app.data.match.compound.focused,
  async (match) => {
    const ionId =
      match?.target_ion_id ??
      app.data.match.ion.list?.find((ion) => ion.target_compound_id === match?.target_compound_id)
        ?.target_ion_id
    if (
      ionId &&
      app.data.sample.focused &&
      app.data.match.visualized.ion?.target_ion_id !== ionId
    ) {
      await app.data.match.visualized.set({
        sampleId: app.data.sample.focused.sample_item_id,
        ionId,
        collectionId: match?.target_collection_id,
        // pass the ion specific filter params if available to the loadSampleIon function
        params: app.data.match.ion.list.find((ion) => ion.target_ion_id === ionId)?.filter_params[
          app.data.sample.focused.instrument
        ]
      })
    }
  }
)

/**
 * Utility function to allow scrolling to targets in the watchers below
 *
 * A lock prevents race conditions when focusing one level of the hierarchy
 * is propegated to other levels, ensuring only the initially focused level
 * is scrolled to.
 */
let lock = false
function scrollTo(target) {
  // TODO - reimplement this
  //if (!lock && target) {
  //  lock = true
  //  setTimeout(() => {
  //    document
  //      .getElementById(target.match_key)
  //      ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  //    lock = false
  //  }, 1000)
  //}
}

/**
 * Watcher that monitors changes of the focused target collection.
 *
 * It unfocuses all child elements (compounds, ions, isotopes) and unsets the visualized Match when:
 *   1. A different collection is selected.
 *   2. The current collection is deselected.
 *
 * @param {Object|null} collection - The currently focused collection.
 * @param {Object|null} oldCollection - The previously focused collection.
 */
watch(
  () => app.data.match.collection.focused,
  (collection, oldCollection) => {
    const changedCollection =
      collection?.target_collection_id !== oldCollection?.target_collection_id
    // conditionally unset match visualized
    if (!collection || changedCollection) {
      app.data.match.visualized.clear()
    }
    if (collection) {
      scrollTo(collection)
    }
  }
)
watch(
  () => app.data.match.compound.focused,
  (compound) => {
    if (compound) {
      // focus parent if focused
      app.data.match.collection.focus((coll) => coll.match_key == compound.parent_key)
      // unfocus unrelated ions
      if (app.data.match.ion.focused?.parent_key !== compound.match_key) {
        app.data.match.ion.unfocus()
      }
      scrollTo(compound)
    } else {
      // unfocus child if unfocused
      app.data.match.ion.unfocus()
      // and unset visualized match
      app.data.match.visualized.clear()
    }
  }
)
watch(
  () => app.data.match.ion.focused,
  (ion) => {
    if (ion) {
      // focus parent if focused
      app.data.match.compound.focus((comp) => comp.match_key == ion.parent_key)
      // unfocus unrelated isotopes
      if (app.data.match.isotope.parent_key !== ion.match_key) {
        app.data.match.isotope.unfocus()
      }
      scrollTo(ion)
    } else {
      // unfocus child if unfocused
      app.data.match.isotope.unfocus()
    }
  }
)
watch(
  () => app.data.match.isotope.focused,
  (isotope) => {
    if (isotope) {
      scrollTo(isotope)
    }
  }
)
watch(
  () => app.data.sample.focused,
  (sample) => {
    scrollTo(
      app.data.match.isotope.focused ??
        app.data.match.ion.focused ??
        app.data.match.compound.focused ??
        app.data.match.collection.focused
    )
  }
)

const { height } = useWindowSize()
const padding = 100
const tableHeight = computed(() => ((height.value - padding) * app.ui.split.bottom) / 100 - 50)

provide('target-table-height', tableHeight)
</script>

<template>
  <TargetIsotopeTable v-if="app.data.match.ion.focused" />
  <TargetIonTable v-else-if="app.data.match.compound.focused" />
  <TargetCompoundTable v-else-if="app.data.match.collection.focused" />
  <TargetCollectionTable v-else />
</template>
