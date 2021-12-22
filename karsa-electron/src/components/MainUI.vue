<template>
  <div>
    <b-tabs
      class="tabs-main"
      v-model="active_tab"
      :animated="false"
      type="is-boxed main-tab"
    >
      <!-- Tabs -->
      <!-- Config tab -->
      <b-tab-item icon="settings" label="">
        <ConfigVue></ConfigVue>
      </b-tab-item>
      <!-- Main tab -->
      <b-tab-item
        icon=""
        :label="
          this.project_selected.title + '/' + this.experiment_selected.title
        "
      >
        <div class="columns">
          <b-loading
            v-model="is_disconnected"
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
                  :reduce="!sample_browser_pinned"
                  open
                >
                  <div>
                    <b-button
                      icon-left="file-tree"
                      :type="sample_browser_pinned ? 'is-primary' : 'is-dark'"
                      size="is-medium"
                      @click="sample_browser_pinned = !sample_browser_pinned"
                    >
                      Samples
                    </b-button>
                    <div>
                      <SampleBrowser></SampleBrowser>
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
                          v-model="data_source_name_selected"
                          placeholder="Select data source"
                          expanded
                        >
                          <option
                            v-for="source in data_sources"
                            :value="source.name"
                            :key="source.name"
                          >
                            {{ source.name }}
                          </option>
                        </b-select>

                        <b-switch
                          style="color: white"
                          v-model="autosave_on"
                          :disabled="!experiment_selected.title.length"
                        >
                          Auto-save
                        </b-switch>
                      </b-field>
                    </div>
                    <!-- End of data source selector -->
                    <!-- Data source component -->
                    <RAWimport
                      v-if="
                        data_source_selected.type &&
                        data_source_selected.type.indexOf('H5') != -1
                      "
                    >
                    </RAWimport>
                    <RAWimport
                      v-if="
                        data_source_selected.type &&
                        data_source_selected.type.indexOf('Raw') != -1
                      "
                    >
                    </RAWimport>
                    <TOFControl
                      v-if="
                        data_source_selected.type &&
                        data_source_selected.type.indexOf('TofDaq') != -1
                      "
                    >
                    </TOFControl>
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
                  :reduce="!target_browser_pinned"
                  open
                >
                  <div>
                    <b-button
                      icon-left="target"
                      :type="target_browser_pinned ? 'is-primary' : 'is-dark'"
                      size="is-medium"
                      @click="target_browser_pinned = !target_browser_pinned"
                    >
                      Targets
                    </b-button>
                  </div>
                  <TargetBrowser></TargetBrowser>
                </b-sidebar>
              </section>
            </div>
            <!-- End of targets sidebar -->
          </div>
          <!-- Right column -->
          <div class="column" style="padding-right: 2rem; max-width: 50vw">
            <SampleView></SampleView>
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
import ConfigVue from "./ConfigVue";
import RAWimport from "./RAWimport";
import SampleView from "./SampleView.vue";
import SampleBrowser from "./SampleBrowser.vue";
import TargetBrowser from "./TargetBrowser.vue";
import TOFControl from "./TOFControl.vue";
import store from "../store";
import { BECom, read_dotenv, write_dotenv } from "../karsalib.js";

const _ = require("underscore");

export default {
  name: "MainUi", //used as app_name - keep it unique
  store,
  components: {
    ConfigVue,
    RAWimport,
    SampleBrowser,
    SampleView,
    TargetBrowser,
    TOFControl,
  },
  data() {
    return {
      active_tab: 2,
      dotenv: {},
      be: null,
      room_sid: null,
      // endpoints - list of notifications the MainUI wants to receive
      endpoints: ["instrument_data", "room_mate_gone", "service_error"],

      data_source_name_selected: null,
      instrument_data: {},
      instrument_data_queue: Promise.resolve(),
      is_disconnected: true,
      room_mate_gone: null,
      room_data_sources: "room_data_sources",
      service_error: "",
      sample_browser_pinned: true,
      target_browser_pinned: true,
    };
  },
  computed: {
    ...mapState(["experiment_selected", "project_selected"]),
    autosave_on: {
      get() {
        return this.$store.state.autosave_on;
      },
      set(value) {
        this.$store.commit("autosave_on", value);
      },
    },
    data_source_selected: {
      get() {
        return this.$store.state.data_source_selected;
      },
      set(value) {
        this.$store.commit("data_source_selected", value);
      },
    },
    data_sources: {
      get() {
        return this.$store.state.data_sources;
      },
      set(value) {
        this.$store.commit("data_sources", value);
      },
    },
    root_namespace: {
      get() {
        return this.$store.state.root_namespace;
      },
      set(value) {
        this.$store.commit("root_namespace", value);
      },
    },
    url: {
      get() {
        return this.$store.state.url;
      },
      set(value) {
        this.$store.commit("url", value);
      },
    },
  },
  created() {
    this.be = new BECom(this);
    this.dotenv = read_dotenv();
    this.url =
      this.dotenv.protocol + "//" + this.dotenv.host + ":" + this.dotenv.port;
  },
  methods: {
    filter_data_sources_prop(name, value) {
      return this.data_sources.filter((o) => {
        return o[name] === value;
      });
    },
    on_instrument_data: function (new_value) {
      if (
        !new_value.name ||
        !_.isEmpty(this.filter_data_sources_prop("name", new_value.name))
      )
        return false;
      this.data_sources.push(new_value);
    },
  },

  // watchers for internal notifications
  // watchers also see changes from external notifications, if any
  watch: {
    url: function (new_url) {
      // Connect to new url
      this.be.disconnect(this.root_namespace);
      this.root_namespace = this.be.connect();
      // Parse url into dotenv format and write to file
      let url_obj = new URL(new_url);
      this.dotenv.protocol = url_obj.protocol;
      this.dotenv.host = url_obj.hostname;
      this.dotenv.port = url_obj.port;
      write_dotenv(this.dotenv);
    },
    data_source_name_selected: function (new_value, old_value) {
      if (new_value === old_value) return false;
      this.data_source_selected = this.filter_data_sources_prop(
        "name",
        new_value
      )[0];
    },
    instrument_data: function (new_value) {
      var self = this;
      self.instrument_data_queue = self.instrument_data_queue.then(function () {
        return self.on_instrument_data(new_value);
      });
    },
    room_mate_gone: async function () {
      this.data_sources = [];
      await this.be.emit_client_notification(
        "instrument_data_request",
        {},
        this.room_data_sources,
        this.room_data_sources
      );
    },
    service_error: function (new_value) {
      if (_.isEmpty(new_value)) {
        return false;
      }
      this.$buefy.dialog.alert({
        title: "Error",
        message: new_value,
        type: "is-danger",
        hasIcon: true,
        icon: "times-circle",
        iconPack: "fa",
        ariaRole: "alertdialog",
        ariaModal: true,
      });
      this.service_error = "";
    },
    "root_namespace.connected": function (new_value) {
      this.is_disconnected = !new_value;
      if (new_value === true) {
        // handlers for for external notifications:
        this.root_namespace.on("instrument_data", (value) =>
          this.be.import_one_way_binding_prop("instrument_data", value.value)
        );
        this.root_namespace.on("room_mate_gone", (value) =>
          this.be.import_one_way_binding_prop("room_mate_gone", {
            ...value.value,
            uid: Math.random(),
          })
        );
        this.namespace.on("service_error", (value) =>
          this.be.import_two_way_binding_prop("service_error", value.value)
        );
        this.be.subscribe(this.endpoints, this.room_data_sources);
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