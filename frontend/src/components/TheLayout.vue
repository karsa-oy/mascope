<template>
  <div>
    <section>
      <the-modal-aggregator></the-modal-aggregator>
      <slot></slot>
    </section>
  </div>
</template>

<script>
import TheModalAggregator from "./TheModalAggregator.vue";

export default {
  name: "TheLayout",
  components: {
    TheModalAggregator,
  },
};
</script>
