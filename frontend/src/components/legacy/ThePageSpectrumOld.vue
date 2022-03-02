<template>
  <div>
    <!-- Modals -->
    <!--- Add annotation modal-->
    <!--- End of add annotation modal-->
    <!-- End of modals -->

    <div style="text-align: center">
      <h1 style="color: #b7b7b7; font-size: 18px; padding: 0.3em 1em">
        {{ experimentSelected.title }} - {{ sampleInFocus.title }}
      </h1>
    </div>
    <!-- Main content  area-->
    <div class="columns">
      <!-- Left side -->
      <div class="column is-half">
        <!-- Heatmap section -->
        <section class="heatmap-section">
          <ThePageAnalysisChartSpectrogram id="spectrogram">
          </ThePageAnalysisChartSpectrogram>
        </section>
        <!-- End of heatmap section-->
        <!-- Multiselect section -->
        <section class="multiselect-section">
          <div hidden>
            <div class="column tps-multiselect">
              <h2 class="multiselect-title">Select parameter to display</h2>
              <multiselect
                v-model="tpsParametersSelectedUi"
                tag-placeholder="Add this as new tag"
                placeholder="Search or add a tag"
                label="label"
                track-by="value"
                :options="tpsParameters"
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
          <ThePageAnalysisChartTimeseries id="timeseries">
          </ThePageAnalysisChartTimeseries>
        </section>
        <!-- End of timeseries -->
      </div>

      <!-- Right side -->
      <div class="column is-half">
        <!-- Spec stack section -->
        <ThePageAnalysisChartWaterfall id="waterfall">
        </ThePageAnalysisChartWaterfall>
        <!-- End of spec stack -->
      </div>
    </div>
  </div>
</template>


<script>
import { mapState } from "vuex";
import Multiselect from "vue-multiselect";

import ThePageAnalysisChartSpectrogram from "./ThePageAnalysisChartSpectrogram";
import ThePageAnalysisChartTimeseries from "./ThePageAnalysisChartTimeseries";
import ThePageAnalysisChartWaterfall from "./ThePageAnalysisChartWaterfall";

const _ = require("underscore");

export default {
  name: "ThePageAnalysis",
  components: {
    ThePageAnalysisChartSpectrogram,
    ThePageAnalysisChartTimeseries,
    ThePageAnalysisChartWaterfall,
    // using third party multiselect component
    Multiselect,
  },
  props: {
    id: String,
  },
  computed: {
    ...mapState([
      "experimentSelected",
      "figureDoubleClick",
      "parameterPeakIntensityThreshold",
      "rootNamespace",
      "sampleAnnotationTimestamp",
      "sampleInFocus",
      "stopVisualizeRange",
      "targetToDisplay",
      "visualizeRange",
    ]),
    figureData: {
      get() {
        return this.$store.state.figureData;
      },
      set(value) {
        this.$store.commit("figureData", value);
      },
    },
    figureRanges: {
      get() {
        return this.$store.state.figureRanges;
      },
      set(value) {
        this.$store.commit("figureRanges", value);
      },
    },
    peakData: {
      get() {
        return this.$store.state.peakData;
      },
      set(value) {
        this.$store.commit("peakData", value);
      },
    },
    sampleAnnotations: {
      get() {
        return this.$store.state.sampleAnnotations;
      },
      set(value) {
        this.$store.commit("sampleAnnotations", value);
      },
    },
    tofdaqLogEntry: {
      get() {
        return this.$store.state.tofdaqLogEntry;
      },
      set(value) {
        this.$store.commit("tofdaqLogEntry", value);
      },
    },
    targetClearIsotopeTable: {
      get() {
        return this.$store.state.dimTarget.clearIsotopeTable;
      },
      set(value) {
        this.$store.commit("clearIsotopeTable", value);
      },
    },
  },
  data: function () {
    return {
      be: null, //backend communicator
      namespace: null,
      roomSid: null,

      // UI variables
      isModalAddLogEntryActive: false,
      isModalAddAnnotationActive: false,
      //

      // Annotation modal variables
      sampleAnnotationDefaultTemplate: [
        { label: "Annotation text", value: "" },
      ],
      sampleAnnotationFields: {},
      sampleAnnotationSaveButtonType: "is-success",
      sampleAnnotationTemplatePath: "./templates",
      //

      filename: "",

      tpsParameters: [],
      tpsParametersSelectedUi: [],
      tpsParametersSelected: {},

      vizTypes: ["spectrogram", "timeseries", "waterfall"],
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
      let annotationText = "";
      for (let i in this.sampleAnnotationFields) {
        let label = this.sampleAnnotationFields[i].label;
        let value = this.sampleAnnotationFields[i].value;
        annotationText += label + ": " + value + "<br>";
      }
      let annotation = {
        text: annotationText,
        timestamp: this.sampleAnnotationTimestamp,
      };
      this.sampleAnnotations.push(annotation);
      this.isModalAddAnnotationActive = false;

      // For backwards compatibility, let BaseImportTof know about annotation
      this.tofdaqLogEntry = annotation;

      // Format annotation for SampleManagerService
      const annotationData = {
        filename: this.filename,
        project: this.sampleInFocus.project,
        experiment: this.sampleInFocus.experiment,
        annotation: {
          timestamp: this.sampleAnnotationTimestamp,
          entry: this.sampleAnnotationFields,
        },
      };

      return this.be.exportOneWayBindingProp(
        "saveSampleAnnotation",
        annotationData,
        null,
        this.roomSid
      );
    },
    requestPeakData() {
      if (this.filename) {
        this.be.exportOneWayBindingProp(
          "peakDataRequest",
          {
            filename: this.filename,
            parameters: {
              peakThreshold: this.parameterPeakIntensityThreshold,
            },
          },
          null,
          this.roomSid
        );
      }
    },
  },
  watch: {
    figureDoubleClick: function () {
      return;
    },
    parameterPeakIntensityThreshold: function () {
      this.requestPeakData();
    },
    sampleAnnotationFields: {
      handler() {
        this.sampleAnnotationSaveButtonType = "is-danger";
      },
      deep: true,
    },
    sampleAnnotationTimestamp: function () {
      this.isModalAddAnnotationActive = true;
    },
    sampleInFocus: function (newValue) {
      this.filename = newValue.filename;
      this.figureRanges = {
        filename: newValue.filename,
        tRange: [0, newValue.properties.length],
        mzRange: newValue.properties.range,
        id: Math.random().toString(36).substring(2),
      };
      this.targetClearIsotopeTable = Math.random().toString(36).substring(2);
      this.requestPeakData();
    },
    stopVisualizeRange: function (newValue, oldValue) {
      if (_.isEqual(newValue.requestIds, oldValue.requestIds)) {
        return;
      }
      return this.be.exportOneWayBindingProp(
        "stopVisualizeRange",
        { ...newValue, uid: Math.random() },
        oldValue,
        this.roomSid
      );
    },
    targetToDisplay: function (newValue, oldValue) {
      if (
        !newValue ||
        _.isEqual(newValue, oldValue) ||
        _.isEmpty(this.filename)
      ) {
        return false;
      }
      let mz = newValue;
      let dmz = 1000; // ppm
      let targetMzRange = [(1 - dmz * 1e-6) * mz, (1 + dmz * 1e-6) * mz];
      let newFigureRanges = {
        filename: this.filename,
        id: Math.random().toString(36).substring(2),
        tRange: this.figureRanges.tRange,
        mzRange: targetMzRange,
        volatile: true,
      };
      this.figureRanges = newFigureRanges;
    },
    tpsParameters: function (newValue, oldValue) {
      if (_.isEmpty(newValue) || _.isEqual(newValue, oldValue)) {
        return false;
      }
    },
    tpsParametersSelectedUi: function (value) {
      this.tpsParametersSelected = {
        tpsParametersSelected: value,
        figureRanges: this.figureRanges,
      };
    },
    tpsParametersSelected: function (newValue, oldValue) {
      return this.be.exportOneWayBindingProp(
        "tpsParametersSelected",
        newValue,
        oldValue,
        this.roomSid
      );
    },
    visualizeRange: function (newValue, oldValue) {
      if (_.isEqual(newValue.requestId, oldValue.requestId)) {
        return;
      }

      return this.be.exportOneWayBindingProp(
        "visualizeRange",
        {
          ...newValue,
          vizTypes: this.vizTypes,
          room: this.roomSid,
          uid: Math.random(),
        },
        oldValue,
        this.roomSid
      );
    },
    "rootNamespace.connected": function (newValue) {
      if (newValue === true) {
        this.namespace = this.rootNamespace;
        // handlers for for external notifications:
        this.namespace.on("figureData", (value) =>
          this.be.importOneWayBindingProp("figureData", value)
        );
        this.namespace.on("peakData", (value) =>
          this.be.importOneWayBindingProp("peakData", {
            mz: new Float32Array(value.value.mz),
            height: new Float32Array(value.value.height),
            tof: new Float32Array(value.value.tof),
          })
        );

        this.roomSid = this.rootNamespace.id;
      }
    },
  },
};
</script>