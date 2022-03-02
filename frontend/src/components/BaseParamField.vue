<template>
  <b-field :label="label">
    <b-numberinput
      v-model="param"
      v-bind="range"
      :type="type"
      size="is-small"
      controls-alignment="right"
      style="margin-right: 15px"
    >
    </b-numberinput>
    <b-slider
      v-model="param"
      v-bind="range"
      :type="type"
      :tooltip="tooltip"
      tooltip-type="is-white"
      lazy
    >
    </b-slider>
  </b-field>
</template>

<script>
export default {
  name: "BaseParamField",
  props: {
    label: {
      type: String,
      required: true,
    },
    path: {
      type: String,
      required: true,
    },
    range: {
      type: Object,
      required: false,
      default() {
        return { min: 0, max: 1, step: 0.01 };
      },
    },
    type: {
      type: String,
      required: false,
      default: "is-info",
    },
    tooltip: {
      type: Boolean,
      required: false,
      default: true,
    },
  },
  computed: {
    param: {
      get() {
        return this.$store.getters.getPath(this.path);
      },
      set(value) {
        this.$store.commit("setPath", { path: this.path, value });
      },
    },
  },
};
</script>

<style>
.input.input.is-small {
  width: 80px;
}

.b-slider.is-info .b-slider-fill {
  background: #3298dc !important;
}

.b-slider.is-success .b-slider-fill {
  background: #5cb85c !important;
}

.b-slider.is-primary .b-slider-fill {
  background: #df691a !important;
}
</style>