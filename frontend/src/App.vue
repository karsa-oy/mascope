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
<style src="./assets/css/logo.css"></style>

<script>
import { call, get } from "vuex-pathify";

export default {
  data: function () {
    return {};
  },
  computed: {
    ...get({
      appReady: "app/ready",
    }),
  },
  created() {
    // add event listeners
    window.addEventListener("keydown", (event) => {
      this.keydown(event);
    });
    window.addEventListener("keyup", (event) => {
      this.keyup(event);
    });
  },
  methods: {
    ...call({
      keydown: "key/down",
      keyup: "key/up",
    }),
  },
};
</script>