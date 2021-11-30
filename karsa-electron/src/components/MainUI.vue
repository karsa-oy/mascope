<template>
  <div class="columns">
    <b-loading
      v-model="is_disconnected"
      :can-cancel="false"
      :is-full-page="false"
    >
    </b-loading>
    <!-- Left column -->
    <div class="column is-one-third">
      <b-tabs class="tabs-main" v-model="active_tab" :animated="true">
        <b-tab-item icon="flask" label="Samples">
          <!-- Data source selector -->
          <div>
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
          <!-- End of data source selector -->
          <div><br></div>
          <SampleBrowser></SampleBrowser>
        </b-tab-item>
        <b-tab-item icon="crosshairs" label="Targets">
          <TargetBrowser></TargetBrowser>
        </b-tab-item>
        <b-tab-item icon="cogs" label="Settings">
          <ConfigVue></ConfigVue>
        </b-tab-item>
      </b-tabs>
      <!-- End of tabs -->
    </div>
    <!-- End of left column -->
    <!-- Right side content -->
    <div class="column is-two-thirds">
      <SampleView></SampleView>
    </div>
    <!-- End of Right side content -->
  </div>
</template>

<script type="text/javascript">
import { mapState } from "vuex";
import ConfigVue from "./ConfigVue.vue";
import RAWimport from "./RAWimport.vue";
import TOFControl from "./TOFControl.vue";
import SampleView from "./SampleView.vue";
import SampleBrowser from "./SampleBrowser.vue";
import TargetBrowser from "./TargetBrowser.vue";
import store from "../store";
import { BECom, read_dotenv, write_dotenv } from "../karsalib.js";

const _ = require("underscore");

export default {
  name: "MainUi", //used as app_name - keep it unique
  store,
  components: {
    ConfigVue,
    RAWimport,
    TOFControl,
    SampleBrowser,
    SampleView,
    TargetBrowser,
  },
  data() {
    return {
      active_tab: 0,
      dotenv: {},
      be: null,
      room_sid: null,
      // endpoints - list of notifications the MainUI wants to receive
      endpoints: ["instrument_data", "room_mate_gone"],
      instrument_data: {},
      instrument_data_queue: Promise.resolve(),
      is_disconnected: true,
      room_mate_gone: null,
      data_source_name_selected: null,
      data_sources: [],
      room_data_sources: "room_data_sources",
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