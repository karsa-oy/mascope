<script setup>
import { computed, inject } from 'vue'

import Chip from 'primevue/chip'

import { useApp } from '@/stores'
import { prettyTrim } from '@/lib/utils'
import { num } from '@/lib/formatters'

const app = useApp()

const active = computed(() => app.data.match.collection.focused)

const clear = () => {
  app.data.match.isotope.unfocus()
  app.data.match.ion.unfocus()
  app.data.match.compound.unfocus()
  app.data.match.collection.unfocus()
}

const register = inject('register-filter')
register({
  clear,
  active
})

const label = computed(() => {
  const collectionLabel = app.data.match.collection.focused?.target_collection_name
  const compoundName = app.data.match.compound.focused?.target_compound_name
  const compoundLabel =
    compoundName && compoundName.length > 0
      ? compoundName
      : app.data.match.compound.focused?.target_compound_formula
  const ionLabel = app.data.match.ion.focused?.target_ion_formula
  const isotopeLabel = app.data.match.isotope.focused
    ? num.mz.format(app.data.match.isotope.focused?.mz)
    : null
  if (isotopeLabel) {
    return {
      short: `${prettyTrim(collectionLabel)} ❯ ${compoundLabel} ❯ ${ionLabel} ❯ ${isotopeLabel}`,
      full: `Target Isotope
             ${collectionLabel} ❯ ${compoundLabel} ❯ ${ionLabel} ❯ ${isotopeLabel}`
    }
  } else if (ionLabel) {
    return {
      short: `${prettyTrim(collectionLabel)} ❯ ${compoundLabel} ❯ ${ionLabel}`,
      full: `Target Ion
             ${collectionLabel} ❯ ${compoundLabel} ❯ ${ionLabel}`
    }
  } else if (compoundLabel) {
    return {
      short: `${prettyTrim(collectionLabel)} ❯ ${compoundLabel}`,
      full: `Target Compound
             ${collectionLabel} ❯ ${compoundLabel}`
    }
  } else if (collectionLabel) {
    return {
      short: prettyTrim(collectionLabel),
      full: `Target Collection
             ${collectionLabel}`
    }
  } else {
    return null
  }
})
</script>

<template>
  <Chip
    v-if="active"
    icon="pi pi-bullseye"
    :label="label.short"
    v-tooltip.bottom="label.full"
    removable
    @remove="clear()"
  />
</template>
