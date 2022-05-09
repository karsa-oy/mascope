<template>
  <div id="app">
    <router-view></router-view>
  </div>
</template>

<style src="./assets/css/style.css"></style>
<style src="./assets/css/logo.css"></style>

<script>
import { bindState } from "$lib/store";
import { mapMutations, mapActions } from "vuex";

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
      workspaceActive: "workspace/active",
      workspaceRoom: "workspace/$roomActive",
      $sampleItemSchemaRequest: "sample/item/schema/$request",
      $sampleItemSchemaResponse: "sample/item/schema/$response",
      $sampleFileSchemaRequest: "sample/file/schema/$request",
      $sampleFileSchemaResponse: "sample/file/schema/$response",
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
      sampleBatchRead: "sample/batch/read",
      templateSetRows: "template/setRows",
      keydown: "key/down",
      keyup: "key/up",
    }),
    workspaceById(id) {
      return this.$store.getters["workspace/byId"](id);
    },
    workspaceInit() {
      this.workspaceActive = this.workspaceById(this.query.w);
      if (this.workspaceActive) {
        this.$nextTick(() => {
          this.workspaceRoom = this.workspaceActive.id;
          this.$sampleFileSchemaRequest = {};
          this.$sampleItemSchemaRequest = {};
          this.sampleBatchRead({
            workspaceId: this.workspaceActive.id,
          });
        });
      }
    },
  },
  watch: {
    // initialization
    ready: function () {
      if (this.ready) {
        this.workspaceInit();
      }
    },
    // query
    "$route.query": function () {
      this.query = this.$route.query;
    },
    query: function () {
      this.workspaceInit();
    },
    // sample
    $sampleFileSchemaResponse: function () {
      this.sampleFileSchemaHandleResponse();
    },
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