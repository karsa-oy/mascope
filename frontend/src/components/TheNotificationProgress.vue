<template>
  <div v-if="notificationIsActive">
    <b-message
      type="is-notification"
      :title="progressTitle"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing }"
    >
      <div>
        <section>
          <p>{{ progressMessage }}</p>
        </section>
        <section class="notification-progress-bar">
          <b-progress
            v-if="progressPercentage === 0"
            size="is-medium"
            :type="progressType"
          ></b-progress>
          <b-progress
            v-else
            :value="progressPercentage"
            size="is-medium"
            :type="progressType"
          ></b-progress>
        </section>
      </div>
    </b-message>
  </div>
</template>

<script>
import { mapMutations, mapState } from "vuex";
import { sync, get } from "vuex-pathify";

export default {
  name: "TheNotificationProgress",
  data() {
    return {
      isClosing: false,
      indefiniteProgressActions: ["delete", "copy", "export"],
      valueProgressActions: ["matchCompute", "calibration"],
    };
  },
  computed: {
    ...sync({
      notificationIsActive: "notification/progressActive",
      progressAction: "notification/progressAction",
      progressActionType: "notification/progressActionType",
      progressMessage: "notification/progressMessage",
      progressPercentage: "notification/progressPercentage",
      progressData: "notification/progressData",
      progressError: "notification/progressError",
    }),
    progressTitle() {
      const actionTypeCapitalized =
        this.progressActionType.charAt(0).toUpperCase() +
        this.progressActionType.slice(1);

      switch (this.progressAction) {
        case "copy":
          return `Copy ${actionTypeCapitalized} Progress`;
        case "delete":
          return `Deleting ${actionTypeCapitalized} Progress`;
        case "export":
          return `Export ${actionTypeCapitalized} Progress`;
        default:
          return `${
            this.progressAction.charAt(0).toUpperCase() +
            this.progressAction.slice(1)
          } Progress`;
      }
    },
    progressType() {
      // default case for actions with indefinite progress bars
      if (this.indefiniteProgressActions.includes(this.progressAction)) {
        return this.progressError
          ? "is-danger"
          : this.progressPercentage === 100
          ? "is-success"
          : "is-primary";
      }
    },
    // Dynamically compute the name of the progress state based on the action
    progressStateName() {
      return this.progressAction ? this.progressAction + "Progress" : null;
    },
    // Fetch the progress state value dynamically from the store
    progressStateValue() {
      return this.progressStateName
        ? this.$store.state.notification[this.progressStateName]
        : false;
    },
  },
  methods: {
    ...mapMutations({
      activateNotification: "notification/activate",
      deactivateNotification: "notification/deactivate",
    }),
    close() {
      this.isClosing = true;
      setTimeout(() => {
        this.deactivateNotification();
        this.isClosing = false;
      }, 480);
    },
  },
  watch: {
    progressStateValue(newValue, oldValue) {
      if (newValue && !oldValue) {
        // If the value has changed from false to true, activate the notification
        this.activateNotification({
          notification: "progress",
        });
      } else if (!newValue && oldValue) {
        // If the value has changed from true to false, close the notification
        this.close();
      }
    },
  },
};
</script>
