<template>
  <div>
    <the-notification-in-development></the-notification-in-development>
    <the-notification-batch-compute-progress></the-notification-batch-compute-progress>
  </div>
</template>

<script>
import TheNotificationBatchComputeProgress from "./TheNotificationBatchComputeProgress.vue";
import TheNotificationInDevelopment from "./TheNotificationInDevelopment.vue";

export default {
  name: "TheNotificationAggregator",
  components: {
    TheNotificationInDevelopment,
    TheNotificationBatchComputeProgress,
  },
};
</script>
