<template>
  <div id="app">
    <b-message v-if="isDevelopmentMode" type="is-danger" has-icon>
      NOTE: You are running the development version of Mascope. Any changes are not persisted.
    </b-message>
    <div v-if="appReady">
      <router-view></router-view>
    </div>
    <section v-else>
      <b-loading :is-full-page="true"> Loading... </b-loading>
    </section>
  </div>
</template>

<style src="./assets/css/style.css"></style>
<style src="./assets/css/logo.css"></style>

<script>
import { call, get } from "vuex-pathify";

export default {
  data: function () {
    return {};
  },
  computed: {
    ...get({
      appMode: "app/mode",
      appPushNotification: "app/pushNotification@message",
      appReady: "app/ready",
    }),
    isDevelopmentMode() {
      return this.appMode === "development";
    }
  },
  created() {
    // add event listeners
    window.addEventListener("keydown", (event) => {
      this.keydown(event);
    });
    window.addEventListener("keyup", (event) => {
      this.keyup(event);
    });
    // Return to home page at reload
    if (this.$route.path !== '/') this.$router.push('/');
  },
  methods: {
    ...call({
      keydown: "key/down",
      keyup: "key/up",
    }),
  },
  watch: {
    appPushNotification: {
      handler() {
        this.$buefy.dialog.alert(this.appPushNotification);
      },
      deep: true
    },
  },
};
</script>