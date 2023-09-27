<template>
  <div v-if="notificationIsActive">
    <!-- Development Warning -->
    <b-message
      v-if="warningNotification === 'inDevelopment'"
      type="is-notification"
      title="Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing, 'in-development': 'in-development' }"
    >
      NOTE: You are running the development version of Mascope. Any changes are
      not persisted.
    </b-message>

    <!-- Failed Calibration Samples Warning -->
    <b-message
      v-if="warningNotification === 'failedCalibrationSamples'"
      type="is-notification"
      title="Calibration Error Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing,
        'failed-calibration': 'failed-calibration',
      }"
    >
      <p>There was an error during calibration with the following samples:</p>
      <ul>
        <li v-for="sample in warningData" :key="sample.index">
          <strong>{{ sample.sample_item_name }}</strong
          >, <em>{{ sample.filename }}</em> encountered an error:
          {{ sample.error }}.
        </li>
      </ul>
      <p>Please check the samples.</p>
    </b-message>

    <!-- Other types of warning messages here -->
  </div>
</template>

<script>
import { mapMutations } from "vuex";
import { sync } from "vuex-pathify";

export default {
  name: "TheNotificationWarning",
  data() {
    return {
      isClosing: false,
    };
  },
  computed: {
    ...sync({
      notificationIsActive: "notification/warningActive",
      warningNotification: "notification/warningNotification",
      warningData: "notification/warningData",
    }),
  },
  methods: {
    ...mapMutations({
      deactivateNotification: "notification/deactivate",
      resetWarningNotification: "notification/RESET_WARNING_NOTIFICATION", // map the resetWarningNotification action
    }),
    close() {
      // TODO_configuration  move animation delay to config file
      this.isClosing = true;
      setTimeout(() => {
        this.deactivateNotification();
        this.resetWarningNotification();
        this.isClosing = false;
      }, 500);
    },
  },
};
</script>
