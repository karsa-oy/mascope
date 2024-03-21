<script setup>
import BaseMenuButton from './BaseMenuButton.vue'

defineProps({
  buttons: {
    type: Array,
    required: true
  },
  footerButtons: {
    type: Array
  },
  tooltipPosition: {
    type: String,
    default: 'is-right'
  },
  tooltipDelay: {
    type: Number,
    default: 200
  }
})
</script>

<template>
  <b-menu label="menu">
    <b-menu-list label="">
      <base-menu-button
        v-for="button of buttons"
        v-bind="button"
        :key="button.label"
        :tooltipPosition="tooltipPosition"
        :tooltipDelay="tooltipDelay"
      >
      </base-menu-button>
    </b-menu-list>
    <div class="menu-footer">
      <b-menu-list>
        <base-menu-button
          v-for="button of footerButtons"
          v-bind="button"
          :key="button.label"
          :tooltipPosition="tooltipPosition"
          :tooltipDelay="tooltipDelay"
        >
        </base-menu-button>
      </b-menu-list>
    </div>
  </b-menu>
</template>

<style>
.menu-header {
  top: 0;
  width: 100%;
}
.menu-footer {
  position: absolute;
  bottom: 0;
  width: 100%;
}
</style>
