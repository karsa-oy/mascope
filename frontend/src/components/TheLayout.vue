<template>
  <div>
    <section>
      <the-modal-aggregator></the-modal-aggregator>
      <the-notification-aggregator></the-notification-aggregator>
      <slot></slot>
    </section>
  </div>
</template>

<script>
import TheModalAggregator from "./TheModalAggregator.vue";
import TheNotificationAggregator from "./TheNotificationAggregator.vue";

export default {
  name: "TheLayout",
  components: {
    TheModalAggregator,
    TheNotificationAggregator,
  },
};
</script>
