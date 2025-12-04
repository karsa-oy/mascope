<script setup>
import { computed, inject, watch } from 'vue'

import Chip from 'primevue/chip'

import { useApp } from '@/stores'

const app = useApp()

const active = computed(() => !!app.data.ionization.mechanism.focused)

const register = inject('register-filter')

const clear = () => {
  app.data.ionization.mechanism.unfocus()
}

register({
  clear,
  active
})

const label = computed(() => {
  const mechanism = app.data.ionization.mechanism.focused?.ionization_mechanism
  return mechanism
    ? {
        short: mechanism,
        full: `Ionization Mechanism:\n${mechanism}`
      }
    : null
})

// Clear mechanism filter when collection unfocused
watch(
  () => app.data.match.collection.focused,
  (focused) => !focused && clear()
)
// Auto-clear if focused mechanism unavailable in current match ion list
// Prevents "ghost filter" scenario where chart shows empty due to unavailable mechanism
watch(
  () => [app.data.ionization.mechanism.focused, app.data.match.ion.list],
  ([focused, ionList]) => {
    if (
      focused &&
      !ionList.some((ion) => ion.ionization_mechanism_id === focused.ionization_mechanism_id)
    ) {
      clear()
    }
  }
)
</script>

<template>
  <Chip
    v-if="active"
    icon="ph ph-lightning"
    :label="label.short"
    v-tooltip.bottom="label.full"
    removable
    @remove="clear()"
  />
</template>
