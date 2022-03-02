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
      sampleSelected: "ui/selected/sample",
      $matchUpdate: "match/$update",
      // aggregation
      compoundRows: "target/compoundRows",
      compoundMatches: "match/compoundRows",
      compoundStatsAgg: "workspace/agg/targetCompoundStats",
      ionRows: "target/ionRows",
      ionMatches: "match/ionRows",
      ionStatsAgg: "workspace/agg/targetIonStats",
      isotopeRows: "target/isotopeRows",
      isotopeMatches: "match/isotopeRows",
      isotopeStatsAgg: "workspace/agg/targetIsotopeStats",
    }),
    ready: function () {
      let apiConnected = this.api ? this.api.connected : false;
      let workspacesExist = this.$workspaceRows
        ? this.$workspaceRows.length > 0
        : false;
      return apiConnected && workspacesExist;
    },
  },
  methods: {
    ...mapMutations({
      targetHandleIonCalcResponse: "target/handleIonCalcResponse",
    }),
    ...mapActions({
      sampleBatchList: "sample/batchList",
      sampleHandleResponse: "sample/handleResponse",
      matchRequest: "match/request",
      matchHandleUpdate: "match/handleUpdate",
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
    // match
    $matchUpdate: function () {
      this.matchHandleUpdate();
    },
  },
};
</script>