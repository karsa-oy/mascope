<template>
  <div id="app">
    <router-view></router-view>
  </div>
</template>

<style src="./assets/css/style.css"></style>
<style src="./assets/css/logo.css"></style>

<script>
import { bindState } from "$lib/store";
import { mapActions, mapGetters } from "vuex";

export default {
  data: function () {
    return {};
  },
  created() {
    // save query
    this.query = this.$route.query;
    // add event listeners
    window.addEventListener("keydown", (event) => {
      this.keydown(event);
    });
    window.addEventListener("keyup", (event) => {
      this.keyup(event);
    });
  },
  computed: {
    ...bindState({
      api: "api",
      query: "query",
    }),
    ...mapGetters({
      workspaceSelected: "workspace/selectedRow",
    }),
    ready: function () {
      // check that the API connected succesfully to the backend
      let apiConnected = this.api ? this.api.connected : false;
      return apiConnected;
    },
  },
  methods: {
    ...mapActions({
      ionMechanismRead: "config/ion_mechanism/read",
      sampleFileGetSchema: "sample/file/schema/requestSchema",
      sampleItemGetSchema: "sample/item/schema/requestSchema",
      targetCollectionRead: "target/collection/read",
      workspaceRead: "workspace/read",
      keydown: "key/down",
      keyup: "key/up",
    }),
    load() {
      this.ionMechanismRead();
      this.sampleFileGetSchema();
      this.sampleItemGetSchema();
      this.targetCollectionRead();
      this.workspaceRead();
    },
  },
  watch: {
    // initialization
    ready: function () {
      if (this.ready) {
        this.load();
      }
    },
    // query
    "$route.query": function () {
      this.query = this.$route.query;
    },
  },
};
</script>