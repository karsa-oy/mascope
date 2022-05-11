<template>
  <div id="app">
    <router-view></router-view>
  </div>
</template>

<style src="./assets/css/style.css"></style>
<style src="./assets/css/logo.css"></style>

<script>
import { bindState } from "$lib/store";
import { mapActions, mapMutations } from "vuex";

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
      // workspace
      workspaceActive: "workspace/active",
      workspaceRoom: "workspace/$roomActive",
      // schema
      $sampleItemSchemaRequest: "sample/item/schema/$request",
      $sampleItemSchemaResponse: "sample/item/schema/$response",
      $sampleFileSchemaRequest: "sample/file/schema/$request",
      $sampleFileSchemaResponse: "sample/file/schema/$response",
      // template
      $templateListResponse: "template/$listResponse",
    }),
    ready: function () {
      // check that the API connected succesfully to the backend
      let apiConnected = this.api ? this.api.connected : false;
      return apiConnected;
    },
  },
  methods: {
    ...mapMutations({
      sampleFileSchemaHandleResponse: "sample/file/schema/HANDLE_RESPONSE",
      sampleItemSchemaHandleResponse: "sample/item/schema/HANDLE_RESPONSE",
    }),
    ...mapActions({
      workspaceRead: "workspace/read",
      sampleBatchRead: "sample/batch/read",
      templateSetRows: "template/setRows",
      keydown: "key/down",
      keyup: "key/up",
    }),
    load() {
      if (!this.workspaceActive) {
        this.workspaceRead();
      } else {
        this.$sampleFileSchemaRequest = {};
        this.$sampleItemSchemaRequest = {};
        this.sampleBatchRead({
          workspaceId: this.workspaceActive.id,
        });
      }
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
    workspaceActive: function () {
      this.load();
    },
    // sample
    $sampleFileSchemaResponse: function () {
      this.sampleFileSchemaHandleResponse();
    },
    // schema
    $sampleItemSchemaResponse: function () {
      this.sampleItemSchemaHandleResponse();
    },
    // template
    $templateListResponse: function (rows) {
      this.templateSetRows(rows);
    },
  },
};
</script>