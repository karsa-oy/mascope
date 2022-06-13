<template>
  <div v-on:click="onClick">
    <b-menu-item tag="router-link" :to="{ path, query }" :icon="icon">
    </b-menu-item>
  </div>
</template>

<script>
import { mapState } from "vuex";

export default {
  props: {
    label: {
      type: String,
      required: true,
    },
    path: {
      type: String,
      required: true,
    },
    icon: {
      type: String,
      required: true,
    },
    newQuery: {
      type: Object,
      required: false,
      default: null,
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
    onClick: {
      type: Function,
      required: false,
      default: () => {},
    },
  },
  computed: {
    ...mapState({
      existingQuery: "query",
    }),
    query() {
      return this.newQuery ?? this.existingQuery;
    },
  },
};
</script>

<style>
li > .icon-text {
  line-height: 40x !important;
}
</style>