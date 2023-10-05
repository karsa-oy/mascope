<template>
  <div>
    <the-notification-warning></the-notification-warning>
    <the-notification-batch-compute-progress></the-notification-batch-compute-progress>
    <the-notification-item-compute-progress></the-notification-item-compute-progress>
    <the-notification-calibration-progress></the-notification-calibration-progress>
  </div>
</template>

<script>
import TheNotificationWarning from "./TheNotificationWarning.vue";
import TheNotificationBatchComputeProgress from "./TheNotificationBatchComputeProgress.vue";
import TheNotificationItemComputeProgress from "./TheNotificationItemComputeProgress.vue";
import TheNotificationCalibrationProgress from "./TheNotificationCalibrationProgress.vue";

export default {
  name: "TheNotificationAggregator",
  components: {
    TheNotificationWarning,
    TheNotificationBatchComputeProgress,
    TheNotificationItemComputeProgress,
    TheNotificationCalibrationProgress,
  },
};
</script>
