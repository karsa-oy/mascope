<template>
  <section>
    <the-layout-sidebar>
      <div style="margin: 0 auto; width: 50vw">
        <!-- Progress bars -->
        <section>
          <b-field label="Acquisition">
            <b-progress
              :value="acquisitionProgress"
              :type="acquisitionProgress == 100
                      ? 'is-success'
                      : 'is-primary'
                    "
              >
            </b-progress>
          </b-field>
          <b-field label="Conversion">
            <b-progress
              :value="conversionProgress"
              :type="conversionProgress == 100
                      ? 'is-success'
                      : 'is-primary'
                    "
              >
            </b-progress>
          </b-field>
          <b-field label="Calibration">
            <b-progress
              :value="calibrationProgress"
              :type="calibrationProgress == 100
                      ? 'is-success'
                      : 'is-primary'
                    "
              >
            </b-progress>
          </b-field>
          <b-field label="Target search">
            <b-progress
              :value="matchingProgress"
              :type="matchingProgress == 100
                      ? 'is-success'
                      : 'is-primary'
                    "
              >
            </b-progress>
          </b-field>
        </section>
        <br>
        <!-- Steps -->
        <b-steps
            v-model="activeStep"
            :has-navigation="false"
            >

            <b-step-item
              label="Sample information"
              :clickable="true"
              :type="{'is-success': this.sampleActive ? true : false}"
              >
              <div style="padding-bottom: 1.5em">
                <h1 class="title has-text-centered">Sample information</h1>
              </div>
              <b-field label="Sample name">
                <b-input
                  v-model="sampleItemName"
                  required
                  :disabled="!acquisitionFilename"
                  expanded
                >
                </b-input>
              </b-field>
              <b-field label="Filename">
                <b-input
                  v-model="acquisitionFilename"
                  required
                  :disabled="true"
                  expanded
                >
                </b-input>
              </b-field>
              <div>
                <b-field label="Sample type">
                  <b-dropdown
                    aria-role="list"
                    v-model="sampleItemType"
                    :disabled="!acquisitionFilename"
                    expanded
                    >
                    <template #trigger>
                        <b-button
                            :label="sampleItemType"
                            icon-right="menu-down"
                            expanded
                            style="align:left"
                        />
                    </template>
                    <b-dropdown-item aria-role="listitem" value="SAMPLE">Sample</b-dropdown-item>
                    <b-dropdown-item aria-role="listitem" value="BACKGROUND">Background</b-dropdown-item>
                    <b-dropdown-item aria-role="listitem" value="BLANK">Blank</b-dropdown-item>
                    <b-dropdown-item aria-role="listitem" value="UNKNOWN">Unknown</b-dropdown-item>
                  </b-dropdown>
                </b-field>
                <b-field label="Sample batch">
                  <b-dropdown
                    aria-role="list"
                    expanded
                    @change="selectBatch"
                    disabled
                    >
                    <template #trigger>
                      <b-button
                        :label="batchActive
                          ? batchActive.sample_batch_name
                          : ''
                          "
                        icon-right="menu-down"
                        expanded
                        style="align:left"
                      />
                    </template>
                    <template v-for="batch of batches">
                      <b-dropdown-item
                        aria-role="listitem"
                        :key="batch.sample_batch_id"
                        :value="batch"
                      >
                        {{ batch.sample_batch_name }}
                      </b-dropdown-item>
                    </template>
                  </b-dropdown>
                </b-field>
              </div>
              <div class="container" style="text-align: center; padding: 2em;">
                <b-button
                  :disabled="
                    sampleIsSaved
                    ||
                    !sampleItemName
                    ||
                    !sampleItemType
                    ||
                    !acquisitionFilename
                  "
                  :type="sampleIsSaved
                    ? 'is-success'
                    : 'is-danger'
                    "
                  icon-left="content-save"
                  expanded
                  @click="saveSampleItem"
                >
                  Save sample info
                </b-button>
              </div>
            </b-step-item>

            <b-step-item
              label="Calibration"
              :clickable="this.sampleActive ? true : false"
              :type="{'is-success': this.sampleMzCalibrated}"
              >
                <h1 class="title has-text-centered">Calibration</h1>
                <base-param-field
                  label="Min. match score"
                  path="calibration/paramMatchScoreMin"
                  :range="{ min: 0, max: 1, step: .1 }"
                  type="is-primary"
                >
                </base-param-field>
                <base-param-field
                  label="Refine window [ppm]"
                  path="calibration/paramRefineWindow"
                  :range="{ min: 0, max: 100, step: 1 }"
                  type="is-primary"
                >
                </base-param-field>
                <base-table
                  :key="mzCalibrationTableKey"
                  :rows="mzCalibrationTableRows"
                  :cols="mzCalibrationTableCols"
                  :checkable="false"
                  :searchable="false"
                  :minPrecision="4"
                  :maxPrecision="4"
                >
                </base-table>
                <div style="text-align: right">
                  <b-button
                    :disabled="this.sampleActive ? false : true"
                    type="is-primary"
                    icon-left=""
                    @click="mzCalibrationFit"
                  >
                    Fit
                  </b-button>
                  <b-button
                    :disabled="this.mzFit ? false : true"
                    type="is-success"
                    icon-left="content-save"
                    @click="mzCalibrationApply"
                  >
                    Apply calibration
                  </b-button>
                </div>
            </b-step-item>

            <b-step-item
              label="Target search"
              :clickable="this.sampleActive
                ? this.sampleMzCalibrated
                  ? true
                  : false
                : false
                "
              :type="{'is-success': this.sampleMatched}"
              >
                <h1 class="title has-text-centered">Target search</h1>
                <div v-if="this.sampleMatched">
                  <the-pane-browser-target></the-pane-browser-target>
                </div>
                <div style="text-align: center">
                  <b-button
                    :disabled="this.sampleActive ? false : true"
                    type="is-success"
                    icon-left="content-save"
                    @click="sampleMatch"
                    v-if="!sampleMatched"
                  >
                    Process
                  </b-button>
                  <b-button
                    type="is-primary"
                    icon-left="close"
                    @click=";"
                    v-if="sampleMatched"
                  >
                    Close
                  </b-button>
                </div>
            </b-step-item>
        </b-steps>
      </div>
    </the-layout-sidebar>
  </section>
</template>

<script>

import BaseParamField from "./BaseParamField.vue";
import BaseTable from "./BaseTable.vue";
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import ThePaneBrowserTarget from "./ThePaneBrowserTarget.vue";

import * as _ from "underscore";
import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";

export default {
  name: "TheModalScenthoundWorkflow",
  components: {
    BaseParamField,
    BaseTable,
    TheLayoutSidebar,
    ThePaneBrowserTarget,
  },
  props: {},
  data: function () {
    return {
      activeStep: 0,
      batchSelected: null,
      mzCalibrationTableCols: [
        { field: "mz", label: "Isotope m/z" },
        { field: "sample_peak_mz", label: "Pre peak m/z" },
        { field: "match_mz_error", label: "Pre m/z error [ppm]", subheading: null },
        { field: "calibration_mz", label: "Post peak m/z" },
        {
          field: "calibration_mz_error",
          label: "Post m/z error [ppm]",
          subheading: null,
        },
        { field: "mz_error_diff", label: "m/z error diff", subheading: null },
      ],
      mzCalibrationTableKey: 0,
      sampleItemName: null,
      sampleItemType: null,
    };
  },
  computed: {
    ...get({
      acquisitionFilename: "instrument/acquisitionActiveFilename",
      acquisitionProgress: "instrument/acquisitionProgress",
      batchActive: "batch/active",
      batches: "workspace/batches",
      calibrationProgress: "instrument/calibrationProgress",
      conversionProgress: "instrument/conversionProgress",
      instrumentActive: "instrument/active",
      matchingProgress: "instrument/matchingProgress",
      mzCalibrationMatchScoreMin: "calibration/paramMatchScoreMin",
      mzCalibrationRefineWindow: "calibration/paramRefineWindow",
      mzFit: "calibration/mzFit",
      mzFitStats: "calibration/mzFitStats",
      sampleActive: "sample/active",
      sampleMatched: "sample/matched",
      sampleMzCalibrated: "sample/active@mz_calibration.verified",
    }),
    ...sync({
      scenthoundModeActive: "instrument/scenthoundModeActive",
    }),
    mzCalibrationTableRows() {
      return this.mzFitStats ?? [];
    },
    sampleFilename() {
      return this.sampleActive
        ? this.sampleActive.filename
        : this.acquisitionFilename
    },
    sampleIsSaved() {
      return this.sampleActive
      ? (
          this.sampleItemName === this.sampleActive.sample_item_name
          && this.sampleItemType === this.sampleActive.sample_item_type
        )
      : false;
    },
  },
  created() {
    this.sampleUnload();
    this.scenthoundModeActive = true;
  },
  beforeRouteLeave (to, from , next) {
    this.scenthoundModeActive = false;
    next();
  },
  methods: {
    ...call({
      batchSelect: "batch/load",
      mzCalibrationReset: "calibration/unload",
      sampleUnload: "sample/unload",
    }),
    ...mapMutations({
    }),
    clone(obj) {
      return JSON.parse(JSON.stringify(obj));
    },
    mzCalibrationApply() {
      this.$api.emit(
        'calibration_mz_apply',
        this.mzFit,
        [this.sampleFilename]
        )
    },
    mzCalibrationFit() {
      this.mzCalibrationReset();
      const calibrationCollectionId = this.batchActive.build_params.calibration_collection;
      const ionizationMechanismIds = this.batchActive.build_params.ion_mechanisms;
      this.$api.emit(
        'calibration_mz_fit',
        this.sampleFilename,
        [calibrationCollectionId],
        ionizationMechanismIds,
        this.mzCalibrationMatchScoreMin,
        this.mzCalibrationRefineWindow
        );
    },
    sampleMatch() {
      this.$api.emit(
        'match_item_compute',
        this.sampleActive
      )
    },
    async saveSampleItem() {
      switch (this.sampleItemType) {
        case 'BACKGROUND':
        case 'BLANK':
        case 'SAMPLE':
        case 'UNKNOWN':
          break;
      }
      this.saveSampleInformation();
    },
    saveSampleInformation() {
      let newSampleItem = {
        filename: this.sampleFilename,
        sample_item_name: this.sampleItemName,
        sample_item_type: this.sampleItemType,
        sample_batch_id: this.batchActive.sample_batch_id,
        sample_item_attributes: {},
      };
      if (!this.sampleActive) {
        this.$api.emit('sample_item_create', [newSampleItem]);
      } else {
        newSampleItem = {
          ...newSampleItem,
          sample_item_id: this.sampleActive.sample_item_id,
          sample_item_attributes: this.sampleActive.sample_item_attributes,
          sample_item_utc_created: this.sampleActive.sample_item_utc_created,
        };
        this.$api.emit('sample_item_update', [newSampleItem]);
      }
    },
    selectBatch(val) {
      this.batchSelect(val);
    },
  },
  watch: {
    activeStep() {
      switch (this.activeStep) {
        case 0:
          break;
        case 1:
          break;
        case 2:
          break;
      }
    },
    acquisitionProgress(newValue, oldValue) {
      if (newValue == 0) this.activeStep = 0;
    },
    calibrationProgress(newValue, oldValue) {
      if (oldValue != 100 && newValue == 100) this.activeStep = 1;
    },
    matchingProgress(newValue, oldValue) {
      if (oldValue != 100 && newValue == 100) this.activeStep = 2;

    },
  },
};
</script>

