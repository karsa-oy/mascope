<template>
  <div v-if="notificationIsActive">
    <b-message
      type="is-notification"
      :title="' Calibration ' + calibrationAction + ' Progress'"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing }"
    >
      <div>
        <section>
          <p>{{ progressMessage }}</p>
        </section>
        <section class="notification-progress-bar">
          <!-- For MZ Fit -->
          <b-progress
            v-if="calibrationAction === 'MZ Fit'"
            :value="progressPercentage"
            :max="100"
            show-value
            size="is-medium"
            format="percent"
            :type="
              calibrationError
                ? 'is-danger'
                : progressPercentage == 100
                ? 'is-success'
                : 'is-primary'
            "
          ></b-progress>
          <!-- For MZ Apply -->
          <b-progress
            v-else-if="calibrationAction === 'MZ Apply'"
            :value="progressPercentage"
            size="is-medium"
            :type="
              progressPercentage == 100
                ? calibrationError
                  ? 'is-danger'
                  : 'is-success'
                : 'is-primary'
            "
          ></b-progress>
          <!-- For Auto Sampler -->
          <b-progress
            v-else-if="calibrationAction === 'Auto Sampler'"
            :value="progressPercentage"
            size="is-medium"
            :type="
              progressPercentage == 100
                ? calibrationError
                  ? 'is-danger'
                  : 'is-success'
                : 'is-primary'
            "
          ></b-progress>
        </section>
      </div>
    </b-message>
  </div>
</template>

<script>
import { mapMutations, mapState } from "vuex";
import { sync, get, call } from "vuex-pathify";

export default {
  name: "TheNotificationCalibrationProgress",
  data() {
    return {
      isClosing: false,
    };
  },
  computed: {
    ...sync({
      notificationIsActive: "notification/calibrationProgressActive",
      calibrationAction: "notification/calibrationAction",
      progressMessage: "notification/progressMessage",
      progressPercentage: "notification/progressPercentage",
    }),
    ...get({
      calibrationComputing: "notification/calibrationComputing",
      notificationActive: "notification/active",
      calibrationError: "notification/calibrationError",
    }),
  },
  methods: {
    ...mapMutations({
      activateNotification: "notification/activate",
      deactivateNotification: "notification/deactivate",
    }),
    close() {
      // TODO_configuration  move animation delay to config file
      this.isClosing = true;
      setTimeout(() => {
        this.deactivateNotification();
        this.isClosing = false;
      }, 480);
    },
  },
  watch: {
    calibrationComputing(value) {
      if (value) {
        this.activateNotification({
          notification: "calibrationProgress",
        });
      } else {
        if (this.notificationActive === "calibrationProgress") {
          this.close();
        }
      }
    },
  },
};
</script>
