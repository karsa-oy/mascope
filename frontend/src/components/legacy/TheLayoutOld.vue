<template>
  <div>
    <b-tabs
      class="tabs-main"
      v-model="activeTab"
      :animated="false"
      type="is-boxed main-tab"
    >
      <!-- Tabs -->
      <!-- Config tab -->
      <b-tab-item icon="settings" label="">
        <ThePageSettings></ThePageSettings>
      </b-tab-item>
      <!-- Main tab -->
      <b-tab-item
        icon=""
        :label="
          this.projectSelected.title + '/' + this.experimentSelected.title
        "
      >
        <div class="columns">
          <b-loading
            v-model="isDisconnected"
            :can-cancel="false"
            :is-full-page="false"
          >
          </b-loading>
          <div>
            <!-- Samples sidebar -->
            <div class="sidebar-page">
              <section class="sidebar-layout">
                <b-sidebar
                  position="static"
                  :expand-on-hover="true"
                  :fullheight="true"
                  :reduce="!sampleBrowserPinned"
                  open
                >
                  <div>
                    <b-button
                      icon-left="file-tree"
                      :type="sampleBrowserPinned ? 'is-primary' : 'is-dark'"
                      size="is-medium"
                      @click="sampleBrowserPinned = !sampleBrowserPinned"
                    >
                      Samples
                    </b-button>
                    <div>
                      <BaseBrowserSample></BaseBrowserSample>
                    </div>
                    <!-- Data source selector -->
                    <div
                      style="
                        text-align: center;
                        margin-top: 0.4rem;
                        margin-bottom: 1rem;
                      "
                    >
                      <b-field label="Data source" grouped>
                        <b-select
                          v-model="dataSourceNameSelected"
                          placeholder="Select data source"
                          expanded
                        >
                          <option
                            v-for="source in dataSources"
                            :value="source.name"
                            :key="source.name"
                          >
                            {{ source.name }}
                          </option>
                        </b-select>

                        <b-switch
                          style="color: white"
                          v-model="autosaveOn"
                          :disabled="!experimentSelected.title.length"
                        >
                          Auto-save
                        </b-switch>
                      </b-field>
                    </div>
                    <!-- End of data source selector -->
                    <!-- Data source component -->
                    <BaseImportRaw
                      v-if="
                        dataSourceSelected.type &&
                        dataSourceSelected.type.indexOf('H5') != -1
                      "
                    >
                    </BaseImportRaw>
                    <BaseImportRaw
                      v-if="
                        dataSourceSelected.type &&
                        dataSourceSelected.type.indexOf('Raw') != -1
                      "
                    >
                    </BaseImportRaw>
                    <BaseImportTof
                      v-if="
                        dataSourceSelected.type &&
                        dataSourceSelected.type.indexOf('TofDaq') != -1
                      "
                    >
                    </BaseImportTof>
                    <!-- End of data source component -->
                  </div>
                </b-sidebar>
              </section>
            </div>
            <!-- End of samples sidebar -->
          </div>
          <div>
            <!-- Targets sidebar -->
            <div class="sidebar-page">
              <section class="sidebar-layout">
                <b-sidebar
                  position="static"
                  :expand-on-hover="true"
                  :fullheight="true"
                  :reduce="!targetBrowserPinned"
                  open
                >
                  <div>
                    <b-button
                      icon-left="target"
                      :type="targetBrowserPinned ? 'is-primary' : 'is-dark'"
                      size="is-medium"
                      @click="targetBrowserPinned = !targetBrowserPinned"
                    >
                      Targets
                    </b-button>
                  </div>
                  <BaseBrowserTarget></BaseBrowserTarget>
                </b-sidebar>
              </section>
            </div>
            <!-- End of targets sidebar -->
          </div>
          <!-- Right column -->
          <div class="column" style="padding-right: 2rem; max-width: 50vw">
            <ThePageAnalysis></ThePageAnalysis>
          </div>
          <!-- End of Right column -->
        </div>
      </b-tab-item>
      <!-- End of tabs -->
    </b-tabs>
  </div>
</template>

<script type="text/javascript">
import { mapState } from "vuex";
import { bindState } from "$lib/store";

import BaseBrowserSample from "./BaseBrowserSample";
import BaseBrowserTarget from "./BaseBrowserTarget";
import BaseImportRaw from "./BaseImportRaw";
import BaseImportTof from "./BaseImportTof";

import ThePageAnalysis from "./ThePageAnalysis";
import ThePageSettings from "./ThePageSettings";

import store from "$store";

const _ = require("underscore");

export default {
  name: "MainUi", //used as appName - keep it unique
  store,
  components: {
    ThePageSettings,
    BaseImportRaw,
    BaseBrowserSample,
    ThePageAnalysis,
    BaseBrowserTarget,
    BaseImportTof,
  },
  data() {
    return {
      activeTab: 2,
      // endpoints - list of notifications the MainUI wants to receive
      endpoints: ["instrumentData", "roomMateGone", "serviceError"],

      dataSourceNameSelected: null,
      instrumentData: {},
      instrumentDataQueue: Promise.resolve(),
      isDisconnected: true,
      roomMateGone: null,
      roomDataSources: "roomDataSources",
      serviceError: "",
      sampleBrowserPinned: true,
      targetBrowserPinned: true,
    };
  },
  computed: {
    ...mapState({
      experimentSelected: "experiment/selected",
      projectSelected: "project/selected",
    }),
    ...bindState({
      autosaveOn: "io/source/autosave",
      dataSourceSelected: "io/source/selected",
      dataSources: "io/source/list",
      instrumentData: "io/instrument/data",
      instrumentDataQueue: "io/instrument/dataQueue",
    }),
  },
  methods: {
    filterDataSourcesProp(name, value) {
      return this.dataSources.filter((o) => {
        return o[name] === value;
      });
    },
    onInstrumentData: function (newValue) {
      if (
        !newValue.name ||
        !_.isEmpty(this.filterDataSourcesProp("name", newValue.name))
      )
        return false;
      this.dataSources.push(newValue);
    },
  },

  // watchers for internal notifications
  // watchers also see changes from external notifications, if any
  watch: {
    dataSourceNameSelected: function (newValue, oldValue) {
      if (newValue === oldValue) return false;
      this.dataSourceSelected = this.filterDataSourcesProp(
        "name",
        newValue
      )[0];
    },
    instrumentData: function (newValue) {
      var self = this;
      self.instrumentDataQueue = self.instrumentDataQueue.then(function () {
        return self.onInstrumentData(newValue);
      });
    },
    roomMateGone: async function () {
      this.dataSources = [];
      await this.be.emitClientNotification(
        "instrumentDataRequest",
        {},
        this.roomDataSources,
        this.roomDataSources
      );
    },
    serviceError: function (newValue) {
      if (_.isEmpty(newValue)) {
        return false;
      }
      this.$buefy.dialog.alert({
        title: "Error",
        message: newValue,
        type: "is-danger",
        hasIcon: true,
        icon: "times-circle",
        iconPack: "fa",
        ariaRole: "alertdialog",
        ariaModal: true,
      });
      this.serviceError = "";
    },
    "rootNamespace.connected": function (newValue) {
      this.isDisconnected = !newValue;
      if (newValue === true) {
        // handlers for for external notifications:
        this.rootNamespace.on("instrumentData", (value) =>
          this.be.importOneWayBindingProp("instrumentData", value.value)
        );
        this.rootNamespace.on("roomMateGone", (value) =>
          this.be.importOneWayBindingProp("roomMateGone", {
            ...value.value,
            uid: Math.random(),
          })
        );
        this.namespace.on("serviceError", (value) =>
          this.be.importTwoWayBindingProp("serviceError", value.value)
        );
        this.be.subscribe(this.endpoints, this.roomDataSources);
      }
    },
  },
};
</script>

<style scoped>
#app {
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: left;
  position: absolute;
  margin: 0;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
}
</style>

<style src = "../assets/css/MascopeStyle.css"></style>
<style src = "../assets/css/Layout.css"></style>
<style src = "../assets/css/Tabs.css"></style>
<style src = "../assets/css/Charts.css"></style>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"></style>
<style src = "../assets/css/Multiselect.css"></style>

<!-- <style src = "../assets/css/Deprecated.css"></style>  -->

<style>
/* MAIN */

html {
  background-color: #1f1f22 !important;
  color: #dfdfdf;
  margin: 0;
  min-height: 100%;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
    Arial, sans-serif;
  font-size: 0.8rem;
  -webkit-user-select: none; /* Safari */
  -moz-user-select: none; /* Firefox */
  -ms-user-select: none; /* IE10+/Edge */
  user-select: none; /* Standard */
  height: 100vh;
  margin: 0;
  bottom: 0;
  padding: 0;
}

/* Sidebar */
.b-sidebar .sidebar-content {
  background-color: inherit;
  padding-left: 2px;
  width: 25vw;
}
.b-sidebar .sidebar-content.is-mini.is-mini-expand:hover:not(.is-fullwidth) {
  height: auto;
  width: 25vw;
}
.b-sidebar .sidebar-content.is-mini {
  height: 50px;
  width: 160px;
  overflow: hidden;
}
/* End of sidebar */

.head {
  background-color: #000;
  color: #dfdfdf;
}

/* webkit */

body::-webkit-scrollbar {
  display: none;
}

::-webkit-scrollbar {
  width: 1em;
}
::-webkit-scrollbar-track {
  box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.3);
}
::-webkit-scrollbar-thumb {
  background-color: #888886;
  outline: 1px solid slategrey;
}
</style>