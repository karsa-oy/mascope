<template>
  <b-field :label="label">
    <b-numberinput
      v-model="param"
      v-bind="range"
      :disabled="disabled"
      :type="type"
      size="is-small"
      controls-alignment="right"
      style="margin-right: 15px"
      lazy
    >
    </b-numberinput>
    <b-slider
      v-model="param"
      v-bind="range"
      :disabled="disabled"
      :type="type"
      :tooltip="tooltip"
      tooltip-type="is-white"
      lazy
    >
    </b-slider>
  </b-field>
</template>

<script>
import { sync } from "vuex-pathify";

export default {
  name: "BaseParamField",
  props: {
    disabled: {
      type: Boolean,
      required: false,
      default: false,
    },
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
    ...sync({
      param: ":path",
    }),
  },
  watch: {
    param: function (newVal, oldVal) {
      if (newVal === null) return;
      this.$emit("paramChange");
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
