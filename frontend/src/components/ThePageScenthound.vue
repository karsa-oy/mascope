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
                      ? calibrationStatus.failed
                        ? 'is-danger'
                        : 'is-success'
                      : 'is-primary'
                    "
              >
            </b-progress>
          </b-field>
          <b-field label="Target search">
            <b-progress
              :value="matchingProgress"
              :type="sampleMatchClass"
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
        <!-- Sample information step -->
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
            <b-field label="Filter ID">
              <b-input
                v-model="sampleItemFilterId"
                disabled
                expanded
              >
              </b-input>
              <b-dropdown
                aria-role="list"
                v-model="sampleItemFilterId"
                :disabled="!acquisitionFilename"
                expanded
                >
                <template #trigger>
                  <b-button
                      :label="sampleItemFilterId"
                      icon-right="menu-down"
                      style="align:left"
                  />
                </template>
                <template v-for="filterId of batchFilterIds">
                  <b-dropdown-item
                    aria-role="listitem"
                    :key="filterId"
                    :value="filterId"
                  >
                    {{ filterId }}
                  </b-dropdown-item>
                </template>
              </b-dropdown>
              <b-button
                type='is-primary'
                icon-left='plus'
                :disabled="!acquisitionFilename"
                @click="generateFilterId()"
                >
              </b-button>
            </b-field>
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
                <b-dropdown-item
                  aria-role="listitem"
                  value="BACKGROUND"
                  v-if="!sampleItemFilterId"
                >
                  Instrument background
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="BACKGROUND"
                  v-if="sampleItemFilterId && filterIsNew"
                >
                  Filter background
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="HOT"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Hot
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="BLANK"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Blank
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="UNKNOWN"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Unknown
                </b-dropdown-item>
              </b-dropdown>
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
            <b-field label="Sample batch">
              <b-tooltip
                :delay="200"
                position="is-top"
                type="is-dark"
                size="is-small"
                multilined
              >
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
                <!-- tooltip slot -->
                <template v-slot:content>
                  <table style="text-align:center; width:100%">
                    <tr>
                      <th>#</th>
                      <th>Sample name</th>
                    </tr>
                    <template v-for="(item) in sampleItems">
                      <tr v-bind:key="item.sample_item_id">
                        <td>{{item.index}}</td>
                        <td>{{item.sample_item_name}}</td>
                      </tr>
                    </template>
                  </table>
                </template>
              </b-tooltip>
            </b-field>
            <div class="container" style="text-align: center; padding: 2em 0em 0em 0em;">
              <div class="columns">
                <div class="column is-full">
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
                    @click="saveSampleInformation"
                  >
                    Save sample info
                  </b-button>
                </div>
              </div>
            </div>
          </b-step-item>
          <!-- Calibration step -->
          <b-step-item
            label="Calibration"
            :clickable="this.sampleActive ? true : false"
            :type="{'is-success': this.sampleMzCalibrated}"
            >
              <h1 class="title has-text-centered">Calibration</h1>
              <b-collapse
                :open="false"
                animation="slide"
              >
                <template #trigger>
                  <section style="padding: 0.5em">
                    <b-button
                      icon-left="wrench"
                      size="is-small"
                      @click="
                        (props) => {
                          props.open = !props.open;
                        }
                      "
                    >
                    </b-button>
                  </section>
                </template>
                <the-pane-settings-calibration></the-pane-settings-calibration>
              </b-collapse>
              <b-message v-if="mzFitError" type="is-danger" has-icon>
                {{ mzFitError }}
              </b-message>
              <base-table
                :key="mzCalibrationTableKey"
                :rows="mzCalibrationTableRows"
                :cols="mzCalibrationTableCols"
                :checkable="false"
                :defaultSort="['mz', 'asc']"
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
              <div style="text-align: center">
                <b-button
                  type="is-primary"
                  icon-left="close"
                  @click="reset()"
                  v-if="mzFitError"
                >
                  Close
                </b-button>
              </div>
          </b-step-item>
          <!-- Target search step -->
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
                  @click="reset()"
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
import ThePaneSettingsCalibration from "./ThePaneSettingsCalibration.vue";

import * as _ from "underscore";
import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";
import { genId } from "../lib/util";

export default {
  name: "TheModalScenthoundWorkflow",
  components: {
    BaseParamField,
    BaseTable,
    TheLayoutSidebar,
    ThePaneBrowserTarget,
    ThePaneSettingsCalibration,
  },
  props: {},
  data: function () {
    return {
      activeStep: 0,
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
        { field: "calibrant_to_tic", label: "fraction of TIC", subheading: null },
      ],
      mzCalibrationTableKey: 0,
      sampleItemFilterId: null,
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
      calibrationStatus: "instrument/calibrationStatus",
      conversionProgress: "instrument/conversionProgress",
      instrumentActive: "instrument/active",
      matchingProgress: "instrument/matchingProgress",
      mzCalibrationParams: "calibration/params",
      mzFit: "calibration/mzFit",
      mzFitError: "calibration/mzFitError",
      mzFitStats: "calibration/mzFitStats",
      possibleMatchThreshold: "batch/paramPossibleMatchThreshold",
      probableMatchThreshold: "batch/paramProbableMatchThreshold",
      sampleActive: "sample/active",
      sampleItems: "batch/sampleItems",
      sampleMatched: "sample/matched",
      sampleMatchCollections: "sample/matchCollections",
      sampleMzCalibrated: "sample/active@mz_calibration.verified",
    }),
    ...sync({
      scenthoundModeActive: "instrument/scenthoundModeActive",
    }),
    batchFilterIds() {
      return this.batchActive
        ? [null, ...new Set(this.sampleItems.map((item) => item.filter_id))]
        : [];
    },
    calibrationProgress() {
      return this.calibrationStatus
        ? this.calibrationStatus.progress
        : 0
    },
    filterIsNew() {
      return !this.batchFilterIds.includes(this.sampleItemFilterId);
    },
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
          && this.sampleItemFilterId === this.sampleActive.filter_id
        )
      : false;
    },
    sampleMatchClass() {
      if (this.sampleMaxMatchScore === null) return 'is-primary'
      if (this.sampleMaxMatchScore >= this.probableMatchThreshold) {
        return "is-danger";
      } else if (this.sampleMaxMatchScore >= this.possibleMatchThreshold) {
        return "is-primary";
      } else {
        return "is-success";
      }
    },
    sampleMaxMatchScore() {
      return this.sampleMatchCollections
        ? Math.max(
            ...this.sampleMatchCollections.map((row) => row.match_score)
          )
        : null;
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
      resetAcquisitionStatus: "instrument/resetAcquisitionStatus",
      sampleUnload: "sample/unload",
    }),
    ...mapMutations({
    }),
    clone(obj) {
      return JSON.parse(JSON.stringify(obj));
    },
    generateFilterId() {
      this.sampleItemFilterId = genId(6, false);
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
      this.$api.emit(
        'calibration_mz_fit',
        this.sampleActive.sample_item_id,
        this.mzCalibrationParams,
      );
    },
    reset() {
      this.resetAcquisitionStatus();
      this.resetSampleItem();
      this.activeStep = 0;
    },
    resetSampleItem() {
      this.sampleUnload();
      this.sampleItemFilterId = null;
      this.sampleItemName = null;
      this.sampleItemType = null;
    },
    sampleMatch() {
      this.$api.emit(
        'match_item_compute',
        this.sampleActive
      )
    },
    saveSampleInformation() {
      let newSampleItem = {
        filename: this.sampleFilename,
        sample_item_name: this.sampleItemName,
        sample_item_type: this.sampleItemType,
        sample_batch_id: this.batchActive.sample_batch_id,
        sample_item_attributes: {},
        filter_id: this.sampleItemFilterId,
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
      if (newValue == 0) {
        this.resetSampleItem();
        this.activeStep = 0;
      }
    },
    calibrationProgress(newValue, oldValue) {
      if (oldValue != 100 && newValue == 100) {
        if (this.calibrationStatus.failed) {
          this.activeStep = 1;
        }
      }
    },
    sampleMaxMatchScore() {
      if (this.sampleMaxMatchScore >= this.possibleMatchThreshold) {
        this.activeStep = 2;
      }
    },
  },
};
</script>