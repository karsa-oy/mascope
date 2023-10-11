<template>
  <div v-if="notificationIsActive">
    <!-- Submitted Notification -->
    <b-message
      v-if="generalNotification === 'submitted'"
      type="is-notification"
      has-icon
      icon="check-circle"
      :class="{ 'is-closing': isClosing, 'is-submitted': 'is-submitted' }"
    >
      {{ generalNotificationMessage }}
    </b-message>
    <!-- Error Notification -->
    <b-message
      v-if="generalNotification === 'error'"
      type="is-notification"
      has-icon
      icon="alert-circle-outline"
      :class="{ 'is-closing': isClosing, 'is-error': 'is-error' }"
    >
      {{ generalNotificationMessage }}
    </b-message>
  </div>
</template>

<script>
import { mapMutations } from "vuex";
import { sync } from "vuex-pathify";

export default {
  name: "TheNotificationGeneral",
  data() {
    return {
      isClosing: false,
    };
  },
  computed: {
    ...sync({
      notificationIsActive: "notification/generalActive",
      generalNotification: "notification/generalNotification",
      generalNotificationMessage: "notification/generalNotificationMessage",
    }),
  },
  watch: {
    notificationIsActive(newVal) {
      if (!newVal) {
        this.resetGeneralNotification();
      }
      if (newVal) {
        setTimeout(this.close, 3500);
      }
    },
  },
  methods: {
    ...mapMutations({
      deactivateNotification: "notification/deactivate",
      resetGeneralNotification: "notification/RESET_GENERAL_NOTIFICATION",
    }),
    close() {
      // TODO_configuration  move animation delay
      this.isClosing = true;
      setTimeout(() => {
        this.deactivateNotification();
        this.isClosing = false;
      }, 480);
    },
  },
};
</script>
