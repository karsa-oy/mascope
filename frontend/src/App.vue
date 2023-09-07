<template>
  <div id="app">
    <div v-if="appReady">
      <router-view></router-view>
    </div>
    <section v-else>
      <b-loading :is-full-page="true"> Loading... </b-loading>
    </section>
  </div>
</template>

<style src="./assets/css/style.css"></style>
<style lang="scss">
@import "./assets/css/style.scss";
</style>

<script>
import { call, get } from "vuex-pathify";
import { mapMutations } from "vuex";

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
    },
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
    if (this.$route.path !== "/") this.$router.push("/");
    if (this.isDevelopmentMode) {
      this.activateNotification({
        notification: "inDevelopment",
      });
    }
  },
  methods: {
    ...call({
      keydown: "key/down",
      keyup: "key/up",
    }),
    ...mapMutations({
      activateNotification: "notification/activate",
    }),
  },
  watch: {
    appPushNotification: {
      handler() {
        this.$buefy.dialog.alert(this.appPushNotification);
      },
      deep: true,
    },
  },
};
</script>
