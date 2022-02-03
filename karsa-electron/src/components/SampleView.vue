<template>
  <div>
    <!-- Modals -->
    <!--- Add annotation modal-->
    <section class="add-log-entry-modal">
      <b-modal
        :active.sync="is_modal_add_annotation_active"
        has-modal-card
        trap-focus
        :can-cancel="true"
        :destroy-on-hide="false"
        aria-role="dialog"
        aria-modal
      >
        <div class="modal-card" style="width: 500px">
          <header class="modal-card-head">
            <p class="modal-card-title">Add sample annotation</p>
          </header>
          <section class="modal-card-body">
            <b-field label="Timestamp">
              <b-numberinput
                v-model="sample_annotation_timestamp"
                :value="sample_annotation_timestamp"
              >
              </b-numberinput>
            </b-field>
            <MetaDataForm
              :default_template="sample_annotation_default_template"
              :editable="true"
              :template_path="sample_annotation_template_path"
              @metaDataUpdated="sample_annotation_fields = $event"
            >
            </MetaDataForm>
            <div><br /></div>
          </section>
          <!-- Footer -->
          <footer class="modal-card-foot">
            <b-button
              :type="sample_annotation_save_button_type"
              @click="createSampleAnnotation()"
            >
              Save
            </b-button>
            <b-button @click="is_modal_add_annotation_active = false">
              Cancel
            </b-button>
          </footer>
        </div>
      </b-modal>
    </section>
    <!--- End of add annotation modal-->
    <!-- End of modals -->

    <div style="text-align: center">
      <h1 style="color: #b7b7b7; font-size: 18px; padding: 0.3em 1em">
        {{ experiment_selected.title }} - {{ sample_in_focus.title }}
      </h1>
    </div>
    <!-- Main content  area-->
    <!--  -->
    <div class="rows">
      <div class="row">
        <div>
          <ExperimentView></ExperimentView>
        </div>
        <!--  -->
      </div>
      <div class="row">
        <div class="columns">
          <!-- Left side -->
          <div class="column is-half">
            <!-- Heatmap section -->
            <section class="heatmap-section">
              <ViewPortSpectrogram id="spectrogram"> </ViewPortSpectrogram>
            </section>
            <!-- End of heatmap section-->
            <!-- Multiselect section -->
            <section class="multiselect-section">
              <div hidden>
                <div class="column tps-multiselect">
                  <h2 class="multiselect-title">Select parameter to display</h2>
                  <multiselect
                    v-model="tps_parameters_selected_ui"
                    tag-placeholder="Add this as new tag"
                    placeholder="Search or add a tag"
                    label="label"
                    track-by="value"
                    :options="tps_parameters"
                    :multiple="true"
                    :taggable="true"
                  >
                  </multiselect>
                </div>
              </div>
            </section>
            <!-- End of multiselect section -->
            <!-- Timeseries section -->
            <section>
              <ViewPortTimeseries id="timeseries"> </ViewPortTimeseries>
            </section>
            <!-- End of timeseries -->
          </div>
          <!-- Right side -->
          <div class="column is-half">
            <!-- Spec stack section -->
            <ViewPortWaterfall id="waterfall"> </ViewPortWaterfall>
            <!-- End of spec stack -->
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from "vuex";
import Buefy from "buefy";
import Multiselect from "vue-multiselect";
import ExperimentView from "./ExperimentView.vue";
import MetaDataForm from "./MetaDataForm.vue";
import ViewPortSpectrogram from "./ViewPortSpectrogram.vue";
import ViewPortTimeseries from "./ViewPortTimeseries.vue";
import ViewPortWaterfall from "./ViewPortWaterfall.vue";
import "buefy/dist/buefy.css";
import "@mdi/font/css/materialdesignicons.min.css";
import { BECom } from "../karsalib.js";

Vue.use([Buefy]);

var _ = require("underscore");

export default {
  name: "SampleView",
  components: {
    ExperimentView,
    MetaDataForm,
    // using third party multiselect component
    Multiselect,
    ViewPortSpectrogram,
    ViewPortTimeseries,
    ViewPortWaterfall,
  },
  props: {
    id: String,
  },
  computed: {
    ...mapState([
      "experiment_selected",
      "figure_double_click",
      "parameter_peak_intensity_threshold",
      "root_namespace",
      "sample_annotation_timestamp",
      "sample_in_focus",
      "stop_visualize_range",
      "target_to_display",
      "visualize_range",
    ]),
    figure_data: {
      get() {
        return this.$store.state.figure_data;
      },
      set(value) {
        this.$store.commit("figure_data", value);
      },
    },
    figure_ranges: {
      get() {
        return this.$store.state.figure_ranges;
      },
      set(value) {
        this.$store.commit("figure_ranges", value);
      },
    },
    sample_annotations: {
      get() {
        return this.$store.state.sample_annotations;
      },
      set(value) {
        this.$store.commit("sample_annotations", value);
      },
    },
    tofdaq_log_entry: {
      get() {
        return this.$store.state.tofdaq_log_entry;
      },
      set(value) {
        this.$store.commit("tofdaq_log_entry", value);
      },
    },
  },
  data: function () {
    return {
      be: null, //backend communicator
      namespace: null,
      room_sid: null,

      // UI variables
      is_modal_add_log_entry_active: false,
      is_modal_add_annotation_active: false,
      //

      // Annotation modal variables
      sample_annotation_default_template: [
        { label: "Annotation text", value: "" },
      ],
      sample_annotation_fields: {},
      sample_annotation_save_button_type: "is-success",
      sample_annotation_template_path: "./metadata_templates",
      //

      filename: "",

      tps_parameters: [],
      tps_parameters_selected_ui: [],
      tps_parameters_selected: {},

      viz_types: ["spectrogram", "timeseries", "waterfall"],
    };
  },

  created: function () {
    this.be = new BECom(this);
  },

  mounted: function () {},

  methods: {
    log: function (...args) {
      console.log("[" + this.$options.name + "]", ...args);
    },

    createSampleAnnotation() {
      // Format annotation for display
      let annotation_text = "";
      for (let i in this.sample_annotation_fields) {
        let label = this.sample_annotation_fields[i].label;
        let value = this.sample_annotation_fields[i].value;
        annotation_text += label + ": " + value + "<br>";
      }
      let annotation = {
        text: annotation_text,
        timestamp: this.sample_annotation_timestamp,
      };
      this.sample_annotations.push(annotation);
      this.is_modal_add_annotation_active = false;

      // For backwards compatibility, let TOFControl know about annotation
      this.tofdaq_log_entry = annotation;

      // Format annotation for SampleManagerService
      const annotation_data = {
        filename: this.filename,
        project: this.sample_in_focus.project,
        experiment: this.sample_in_focus.experiment,
        annotation: {
          timestamp: this.sample_annotation_timestamp,
          entry: this.sample_annotation_fields,
        },
      };

      return this.be.export_one_way_binding_prop(
        "save_sample_annotation",
        annotation_data,
        null,
        this.room_sid
      );
    },
  },

  watch: {
    figure_double_click: function () {
      return;
    },
    sample_annotation_fields: {
      handler() {
        this.sample_annotation_save_button_type = "is-danger";
      },
      deep: true,
    },
    sample_annotation_timestamp: function () {
      this.is_modal_add_annotation_active = true;
    },
    sample_in_focus: function (new_value) {
      this.filename = new_value.filename;
      this.figure_ranges = {
        filename: new_value.filename,
        t_range: [0, new_value.properties.length],
        mz_range: new_value.properties.range,
        id: Math.random().toString(36).substring(2),
      };
    },
    stop_visualize_range: function (new_value, old_value) {
      if (_.isEqual(new_value.request_ids, old_value.request_ids)) {
        return;
      }
      return this.be.export_one_way_binding_prop(
        "stop_visualize_range",
        { ...new_value, uid: Math.random() },
        old_value,
        this.room_sid
      );
    },
    target_to_display: function (new_value) {
      if (
        !new_value ||
        _.isEmpty(this.filename)
      ) {
        return false;
      }
      let mz = new_value;
      let dmz = 1000; // ppm
      let target_mz_range = [(1 - dmz * 1e-6) * mz, (1 + dmz * 1e-6) * mz];
      let new_figure_ranges = {
        filename: this.filename,
        id: Math.random().toString(36).substring(2),
        t_range: this.figure_ranges.t_range,
        mz_range: target_mz_range,
        volatile: true,
      };
      this.figure_ranges = new_figure_ranges;
    },
    tps_parameters: function (new_value, old_value) {
      if (_.isEmpty(new_value) || _.isEqual(new_value, old_value)) {
        return false;
      }
    },
    tps_parameters_selected_ui: function (value) {
      this.tps_parameters_selected = {
        tps_parameters_selected: value,
        figure_ranges: this.figure_ranges,
      };
    },
    tps_parameters_selected: function (new_value, old_value) {
      return this.be.export_one_way_binding_prop(
        "tps_parameters_selected",
        new_value,
        old_value,
        this.room_sid
      );
    },
    visualize_range: function (new_value, old_value) {
      if (_.isEqual(new_value.request_id, old_value.request_id)) {
        return;
      }

      return this.be.export_one_way_binding_prop(
        "visualize_range",
        {
          ...new_value,
          viz_types: this.viz_types,
          room: this.room_sid,
          uid: Math.random(),
        },
        old_value,
        this.room_sid
      );
    },
    "root_namespace.connected": function (new_value) {
      if (new_value === true) {
        this.namespace = this.root_namespace;
        // handlers for for external notifications:
        this.namespace.on("figure_data", (value) =>
          this.be.import_one_way_binding_prop("figure_data", value)
        );
        this.room_sid = this.root_namespace.id;
      }
    },
  },
};
</script>