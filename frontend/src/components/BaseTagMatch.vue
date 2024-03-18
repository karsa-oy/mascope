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
      <b-tag
        v-if="!(matchScore === null || isNaN(matchScore))"
        :icon="tag.icon"
        :class="tag.class"
        style="font-size: small"
        @click="clicked"
      >
        <span v-if="displayMatchScore" :style="tag.weight">
          {{ formatter.format(matchScore) }}
        </span>
      </b-tag>
      <!-- tooltip slot -->
      <template
        v-slot:content
        v-bind:key="field"
      >
        <template v-for="(value, field) in tooltip">
          {{ field }}: {{ value }}<br/>
        </template>
      </template>
    </b-tooltip>
  </b-field>
</template>

<script>
export default {
  name: "BaseTagMatch",
  props: {
    displayMatchScore: {
      type: Boolean,
      required: false,
      default: true,
    },
    row: {
      type: Object,
      required: false,
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
    matchScore: function () {
      return this.row !== null
        ? this.row.matched === undefined || this.row.matched
          ? this.row.match_score
          : null
        : null;
    },
    tag: function () {
      if (this.row.alarm_mode) {
        switch (this.row.match_category) {
          case 2:
            return {
              category: "probable",
              class: "is-danger",
              // weight: "font-weight: bold",
            };
          case 1:
            return {
              category: "possible",
              class: "is-warning",
              // weight: "font-weight: bold",
            };
          default:
            return {
              category: "improbable",
              class: "is-success",
              // weight: "font-weight: bold",
            };
        }
      } else {
        switch (this.row.match_category) {
          case 2:
            return {
              category: "probable",
              class: "is-danger-pale",
            };
          case 1:
            return {
              category: "possible",
              class: "is-warning-pale",
            };
          default:
            return {
              category: "improbable",
              class: "is-success-pale",
            };
        }
      }
    },
    tooltipActive: function () {
      return Object.keys(this.tooltip).length > 0;
    },
  },
  methods: {
    clicked: function () {
      this.$emit("tagClicked", this.row);
    },
  },
};
</script>
