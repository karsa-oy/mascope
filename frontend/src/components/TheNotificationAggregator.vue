<template>
  <div>
    <the-notification-in-development></the-notification-in-development>
    <the-notification-batch-compute-progress></the-notification-batch-compute-progress>
    <the-notification-item-compute-progress></the-notification-item-compute-progress>
  </div>
</template>

<script>
import TheNotificationInDevelopment from "./TheNotificationInDevelopment.vue";
import TheNotificationBatchComputeProgress from "./TheNotificationBatchComputeProgress.vue";
import TheNotificationItemComputeProgress from "./TheNotificationItemComputeProgress.vue";

export default {
  name: "TheNotificationAggregator",
  components: {
    TheNotificationInDevelopment,
    TheNotificationBatchComputeProgress,
    TheNotificationItemComputeProgress,
  },
};
</script>
