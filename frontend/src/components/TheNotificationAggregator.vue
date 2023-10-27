<template>
  <div>
    <the-notification-warning></the-notification-warning>
    <the-notification-general></the-notification-general>
    <the-notification-progress></the-notification-progress>
    <the-notification-batch-compute-progress></the-notification-batch-compute-progress>
    <the-notification-item-compute-progress></the-notification-item-compute-progress>
    <the-notification-calibration-progress></the-notification-calibration-progress>
  </div>
</template>

<script>
import TheNotificationWarning from "./TheNotificationWarning.vue";
import TheNotificationGeneral from "./TheNotificationGeneral.vue";
import TheNotificationProgress from "./TheNotificationProgress.vue";
import TheNotificationBatchComputeProgress from "./TheNotificationBatchComputeProgress.vue";
import TheNotificationItemComputeProgress from "./TheNotificationItemComputeProgress.vue";
import TheNotificationCalibrationProgress from "./TheNotificationCalibrationProgress.vue";

export default {
  name: "TheNotificationAggregator",
  components: {
    TheNotificationWarning,
    TheNotificationGeneral,
    TheNotificationProgress,
    TheNotificationBatchComputeProgress,
    TheNotificationItemComputeProgress,
    TheNotificationCalibrationProgress,
  },
};
</script>
