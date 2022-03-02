<template>
  <div id="app">
    <router-view></router-view>
  </div>
</template>


<style src="./assets/css/style.css"></style>
<style src="./assets/css/logo.css"></style>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"></style>
<style src = "./assets/css/multiselect.css"></style>


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
      query: "ui/query",
      workspaceActive: "workspace/active",
      workspaceRoom: "workspace/$roomActive",
      $targetIonCalculationResponse: "workspace/target/$ionCalculationResponse",
      $sampleResponse: "workspace/sample/$response",
      sampleSelected: "ui/selected/sample",
      $matchUpdate: "workspace/match/$update",
      // aggregation
      compoundRows: "workspace/target/compoundRows",
      compoundMatches: "workspace/match/compoundRows",
      compoundStatsAgg: "workspace/agg/targetCompoundStats",
      ionRows: "workspace/target/ionRows",
      ionMatches: "workspace/match/ionRows",
      ionStatsAgg: "workspace/agg/targetIonStats",
      isotopeRows: "workspace/target/isotopeRows",
      isotopeMatches: "workspace/match/isotopeRows",
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
      targetHandleIonCalculationResponse:
        "workspace/target/handleIonCalculationResponse",
    }),
    ...mapActions({
      sampleBatchList: "workspace/sample/batchList",
      sampleHandleResponse: "workspace/sample/handleResponse",
      matchRequest: "workspace/match/request",
      matchHandleUpdate: "workspace/match/handleUpdate",
      keydown: "ui/key/down",
      keyup: "ui/key/up",
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
    $targetIonCalculationResponse: function () {
      this.targetHandleIonCalculationResponse();
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