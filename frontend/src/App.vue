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
      $targetIonCalcResponse: "target/$ionCalculationResponse",
      $sampleResponse: "sample/$response",
      $sampleFileSchemaResponse: "sample/$fileSchemaResponse",
      $sampleItemSchemaResponse: "sample/$itemSchemaResponse",
      $matchUpdate: "match/$update",
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
      targetHandleIonCalcResponse: "target/handleIonCalcResponse",
      sampleFileSchemaRequest: "sample/fileSchemaRequest",
      sampleItemSchemaRequest: "sample/itemSchemaRequest",
      sampleFileSchema: "sample/fileSchema",
      sampleItemSchema: "sample/itemSchema",
    }),
    ...mapActions({
      sampleBatchList: "sample/batchList",
      sampleHandleResponse: "sample/handleResponse",
      matchRequest: "match/request",
      matchHandleUpdate: "match/handleUpdate",
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
        this.workspaceRoom = this.workspaceActive.id;
      }
    },
  },
  watch: {
    // initialization
    ready: function () {
      if (this.ready) {
        this.workspaceInit();
        this.sampleFileSchemaRequest();
        this.sampleItemSchemaRequest();
      }
    },
    workspaceActive: function () {
      this.sampleBatchList();
    },
    // query
    "$route.query": function () {
      this.query = this.$route.query;
    },
    query: function () {
      this.workspaceInit();
    },
    // target
    $targetIonCalcResponse: function () {
      this.targetHandleIonCalcResponse();
    },
    // sample
    $sampleResponse: function () {
      this.sampleHandleResponse();
    },
    $sampleFileSchemaResponse: function (response) {
      this.sampleFileSchema(response);
    },
    $sampleItemSchemaResponse: function (response) {
      this.sampleItemSchema(response);
    },
    // match
    $matchUpdate: function () {
      this.matchHandleUpdate();
    },
    // template
    $templateListResponse: function (rows) {
      this.templateSetRows(rows);
    },
  },
};
</script>