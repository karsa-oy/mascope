<template>
  <b-field>
    <b-tooltip
      :active="tooltipActive"
      :delay="200"
      position="is-left"
      type="is-white"
      append-to-body
      size="is-small"
      multilined
    >
      <b-tag :icon="tag.icon" :class="tag.class" style="font-size: small">
        <span :style="tag.weight">
          {{ formatter.format(matchScore) }}
        </span>
      </b-tag>
      <!-- tooltip slot -->
      <template v-slot:content>
        <template v-for="(value, field) in tooltip">
          {{ field }}: {{ value }}<br v-bind:key="field" />
        </template>
      </template>
    </b-tooltip>
  </b-field>
</template>

<script>
import { get } from "vuex-pathify";

export default {
  name: "BaseTagMatch",
  props: {
    matchScore: {
      type: Number,
      required: true,
    },
    tooltip: {
      type: Object,
      required: false,
    },
  },
  created: function () {
    this.formatter = new Intl.NumberFormat("en-US", {
      style: "percent",
      minimumIntegerDigits: 2,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  },
  computed: {
    ...get({
      probableMatchThreshold: "batch/active@filter_params.probable_match_threshold",
      possibleMatchThreshold: "batch/active@filter_params.possible_match_threshold",
    }),
    tag: function () {
      if (this.matchScore >= this.probableMatchThreshold) {
        return {
          category: "probable",
          class: "is-success",
          icon: "check-bold",
          weight: "font-size: bold",
        };
      } else if (this.matchScore >= this.possibleMatchThreshold) {
        return {
          category: "possible",
          class: "is-primary",
          icon: "help",
          weight: "font-size: bold",
        };
      } else {
        return {
          category: "improbable",
          class: "",
          icon: "close",
          weight: "",
        };
      }
    },
    tooltipActive: function () {
      return Object.keys(this.tooltip).length > 0;
    },
  },
};
</script>
