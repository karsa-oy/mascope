<script setup>
defineProps({
  disabled: {
    type: Boolean,
    required: false,
    default: false
  },
  label: {
    type: String,
    required: true
  },
  path: {
    type: String,
    required: true
  },
  icon: {
    type: String,
    required: true
  },
  tooltipPosition: {
    type: String,
    required: false,
    default: 'is-right'
  },
  tooltipDelay: {
    type: Number,
    required: false,
    default: 200
  },
  onClick: {
    type: Function,
    required: false,
    default: () => {}
  }
})
</script>

<template>
  <div v-on:click="onClick">
    <b-menu-item tag="router-link" :to="{ path }" :icon="icon" :disabled="disabled"> </b-menu-item>
  </div>
</template>

<style>
li > .icon-text {
  line-height: 40x !important;
}
</style>
