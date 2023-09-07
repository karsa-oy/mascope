<template>
  <div v-if="notificationActive">
    <b-message
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
  </div>
</template>

<script>
import { mapMutations } from "vuex";
import { sync } from "vuex-pathify";

export default {
  name: "TheNotificationInDevelopment",
  data() {
    return {
      isClosing: false,
    };
  },
  computed: {
    ...sync({
      notificationActive: "notification/inDevelopmentActive",
    }),
  },
  methods: {
    ...mapMutations({
      deactivateNotification: "notification/deactivate",
    }),
    close() {
      // TODO_configuration  move animation delay to config file
      this.isClosing = true;
      setTimeout(() => {
        this.deactivateNotification();
        this.isClosing = false;
      }, 500);
    },
  },
};
</script>
