<script setup>
import { ref, watchEffect, computed, provide } from 'vue'

import OverlayBadge from 'primevue/overlaybadge'

import { useApp } from '@/stores'

const app = useApp()

/**
 * Computes the badge count to display based on recentErrors or recentWarnings.
 * If there are recent errors, their count is displayed.
 * If there are no errors but warnings, the warning count is displayed.
 * If there are neither, an empty string is returned, hiding the badge.
 *
 *  @returns {String} The badge value as a string.
 */
const badgeValue = computed(() => {
  const errors = app.ui.notification.recentErrors
  const warnings = app.ui.notification.recentWarnings
  return errors > 0 ? String(errors) : warnings > 0 ? String(warnings) : ''
})

/**
 * Determines the severity of the badge.
 * If there are any recent errors, the badge severity is set to 'danger'.
 * Otherwise, if there are only warnings, the badge severity is set to 'warn'.
 *
 * @returns {String} The badge severity ('danger' or 'warn').
 */
const badgeSeverity = computed(() => {
  return app.ui.notification.recentErrors > 0 ? 'danger' : 'warn'
})

/**
 * Controls the visibility of the notification badge.
 * If there are no recent errors or warnings, the badge is hidden.
 *
 * @returns {Boolean} True if the badge should be hidden, otherwise false.
 */
const hiddenBadge = computed(() => {
  return app.ui.notification.recentWarnings === 0 && app.ui.notification.recentErrors === 0
})
</script>

<template>
  <slot v-if="hiddenBadge"></slot>
  <OverlayBadge v-else :value="badgeValue" :severity="badgeSeverity" size="small">
    <slot></slot>
  </OverlayBadge>
</template>
