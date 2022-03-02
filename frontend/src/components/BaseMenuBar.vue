<template>
  <b-menu>
    <b-menu-list>
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

<script>
import BaseMenuButton from "./BaseMenuButton.vue";

export default {
  name: "BaseMainMenu",
  components: {
    BaseMenuButton,
  },
  props: {
    buttons: {
      type: Array,
      required: true,
    },
    footerButtons: {
      type: Array,
      required: false,
    },
    tooltipPosition: {
      type: String,
      required: false,
      default: "is-right",
    },
    tooltipDelay: {
      type: Number,
      required: false,
      default: 200,
    },
  },
};
</script>

<style>
.menu-footer {
  position: absolute;
  bottom: 0;
  width: 100%;
}
</style>
