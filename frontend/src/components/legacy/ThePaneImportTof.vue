<template>
  <div>
    <!-- Modals -->
    <!--- Add log entry modal-->
    <section class="add-log-entry-modal">
      <b-modal
        :active.sync="isModalAddLogEntryActive"
        has-modal-card
        trap-focus
        :can-cancel="true"
        :destroy-on-hide="true"
        aria-role="dialog"
        aria-modal
      >
        <div class="modal-card" style="width: 500px">
          <!-- Main content -->
          <div>
            <header class="modal-card-head">
              <p class="modal-card-title">Add instrument log entry</p>
            </header>
            <section class="modal-card-body">
              <b-field label="Datetime">
                <b-datetimepicker
                  v-model="logEntryDatetimestamp"
                  icon="calendar-today"
                  :timepicker="{ 'hour-format': '24' }"
                  horizontal-time-picker
                >
                </b-datetimepicker>
              </b-field>
              <BaseMetadataForm
                :defaultTemplate="logEntryDefaultTemplate"
                :editable="true"
                :templatePath="logEntryTemplatePath"
                @metaDataUpdated="logEntryFields = $event"
              >
              </BaseMetadataForm>
              <div><br /></div>
            </section>
          </div>
          <!-- Footer -->
          <footer class="modal-card-foot">
            <b-button
              @click="writeInstrumentLogEntry()"
              :type="logEntrySaveButtonType"
            >
              Save
            </b-button>
            <b-button
              is-dark
              @click="
                isModalAddLogEntryActive = false;
                isModalInstrumentLogActive = true;
              "
            >
              Cancel
            </b-button>
          </footer>
        </div>
      </b-modal>
    </section>
    <!--- End of add log entry modal-->

    <!--- Show log modal-->
    <section class="instrument-log-modal">
      <b-modal
        :active.sync="isModalInstrumentLogActive"
        has-modal-card
        trap-focus
        :can-cancel="true"
        :destroy-on-hide="false"
        aria-role="dialog"
        aria-modal
      >
        <div class="modal-card" style="width: 500px">
          <!-- Main content -->
          <div>
            <header class="modal-card-head">
              <p class="modal-card-title">Instrument log</p>
            </header>
            <section class="modal-card-body">
              <b-table :data="instrumentLogRows">
                <template v-for="column in instrumentLogCols">
                  <b-table-column :key="column.id" v-bind="column">
                    <template #searchable="props">
                      <b-input
                        v-model="props.filters[props.column.field]"
                        placeholder="Search..."
                        icon="magnify"
                        size="is-small"
                      />
                    </template>
                    <template v-slot="props">
                      {{ props.row[column.field] }}
                    </template>
                  </b-table-column>
                </template>
              </b-table>
            </section>
          </div>
          <!-- Footer -->
          <footer class="modal-card-foot">
            <b-button type="is-success" @click="onButtonInstrumentLogEntry()">
              New entry
            </b-button>
            <b-button is-dark @click="isModalInstrumentLogActive = false">
              Close
            </b-button>
          </footer>
        </div>
      </b-modal>
    </section>
    <!--- End of show log modal-->

    <!-- Modal for edit temperature ramp datatable values -->
    <section class="modal-edit-temperature-ramp-data-table-row">
      <b-modal
        :active.sync="isModalDesorptionStepActive"
        has-modal-card
        trap-focus
        aria-role="dialog"
        aria-modal
      >
        <div class="columns">
          <div class="modal-card" style="width: auto">
            <section class="modal-card-body idparams-edit-body">
              <b-field label="time [s]">
                <b-input
                  v-model="desorptionStepModalTime"
                  placeholder="seconds"
                >
                </b-input>
              </b-field>

              <b-field label="Temperature [C]">
                <b-input
                  v-model="desorptionStepModalTemperature"
                  placeholder="Temperature"
                >
                </b-input>
              </b-field>

              <b-field label="Cassette in">
                <b-switch v-model="desorptionStepModalFilterIn"> </b-switch>
              </b-field>
            </section>
            <footer class="modal-card-foot">
              <b-button
                @click="editDesorptionCycle()"
                :disabled="
                  !(desorptionStepModalTemperature && desorptionStepModalTime)
                "
              >
                Save
              </b-button>
              <b-button @click="isModalDesorptionStepActive = false">
                Close
              </b-button>
            </footer>
          </div>
        </div>
      </b-modal>
    </section>
    <!-- End of Modal for edit temperature ramp datatable values -->
    <!-- End of modals -->

    <!-- Main content area -->
    <section>
      <!-- Acquisiton parameters collapsable -->
      <section>
        <!-- Instrument control collapsable -->
        <b-collapse class="card" animation="slide" aria-id="contentIdForA11y3">
          <div
            slot="trigger"
            slot-scope="props"
            class="card-header"
            role="button"
            aria-controls="contentIdForA11y3"
          >
            <p class="card-header-title">
              {{ dataSourceSelected.name }}
            </p>
            <a class="card-header-icon">
              <b-icon :icon="props.open ? 'menu-down' : 'menu-up'"> </b-icon>
            </a>
          </div>
          <div class="card-content">
            <div class="content">
              <!-- Instrument status display -->
              <div
                style="
                  text-align: center;
                  margin-top: 0.4rem;
                  margin-bottom: 1rem;
                "
              >
                <h1 class="acquisition-parameters-h1">
                  Instrument status: {{ scenthoundStatus }}
                </h1>
              </div>
              <!-- End of instrument status display -->
              <!-- Acquisition progress bar -->
              <div
                style="
                  margin-left: 1rem;
                  margin-right: 1rem;
                  margin-bottom: 1rem;
                "
              >
                <b-progress
                  v-bind:value="acquisitionProgress"
                  show-value
                  format="percent"
                  :precision="1"
                  type="is-primary"
                  size="is-large"
                >
                </b-progress>
              </div>
              <!-- End of acquisition progress bar -->
              <!-- Controls -->
              <div style="text-align: center">
                <div v-if="method.tofdaq.acquisitionMode === 'manual'">
                  <b-button
                    v-bind:icon-left="
                      acquisitionStatus == 'starting' ||
                      acquisitionStatus == 'stopping' ||
                      instrumentStatus == 'notReady'
                        ? 'flattr'
                        : ''
                    "
                    :type="acquisitionButtonType"
                    :disabled="
                      method.tofdaq.acquisitionMode == 'triggered' ||
                      instrumentStatus == 'notReady'
                    "
                    @click="onButtonChangeAcquisitionStatus()"
                  >
                    {{ acquisitionControlLabel }}
                  </b-button>
                  <div><br /></div>
                </div>
                <b-button
                  type="is-primary"
                  :disabled="!controlModeActive"
                  @click="onButtonShowInstrumentLog()"
                >
                  Instrument log
                </b-button>
                <div><br /></div>
              </div>
              <!-- End of controls -->
            </div>
            <section style="width: 100%; padding: 0.5rem">
              <!-- Method collapsable -->
              <b-collapse
                class="card"
                animation="slide"
                aria-id="contentIdForA11y3"
                :open="false"
              >
                <div
                  slot="trigger"
                  slot-scope="props"
                  class="card-header"
                  style="background-color: transparent"
                  role="button"
                  aria-controls="contentIdForA11y3"
                >
                  <p class="card-header-title">Method</p>
                  <a class="card-header-icon">
                    <b-icon :icon="props.open ? 'menu-down' : 'menu-up'">
                    </b-icon>
                  </a>
                </div>
                <div class="card-content" style="background-color: #3f3f48">
                  <div class="content">
                    <!-- TofDaq section -->
                    <section style="width: 100%; padding: 0.5rem">
                      <div
                        class="card-content"
                        style="background-color: #50505a"
                      >
                        <div class="box" style="background-color: inherit">
                          <h1 style="font-size: 16px; text-align: center">
                            <p><b>TofDaq</b></p>
                          </h1>
                          <b-field label="Acquisition mode">
                            <div style="text-align: center; color: white">
                              <b-radio
                                type="is-white"
                                v-model="method.tofdaq.acquisitionMode"
                                native-value="triggered"
                              >
                                Triggered
                              </b-radio>
                              <b-radio
                                type="is-white"
                                v-model="method.tofdaq.acquisitionMode"
                                native-value="manual"
                              >
                                Manual
                              </b-radio>
                            </div>
                          </b-field>
                          <b-field label="Sample length [s]">
                            <b-input
                              size="is-small"
                              placeholder="seconds"
                              v-model="method.tofdaq.sampleLength"
                              type="number"
                              min="0"
                              max="20000"
                              lazy
                            >
                            </b-input>
                          </b-field>
                        </div>
                      </div>
                    </section>
                    <!-- End of TofDaq section -->
                    <!-- TPS section -->
                    <section style="width: 100%; padding: 0.5rem">
                      <div
                        class="card-content"
                        style="background-color: #50505a"
                      >
                        <div class="box" style="background-color: inherit">
                          <h1 style="font-size: 16px; text-align: center">
                            <p><b>TPS</b></p>
                          </h1>
                          <div class="">
                            <b-field label="TPS settings file">
                              <b-input
                                size="is-small"
                                v-model="method.tps.settingsFile"
                                lazy
                              >
                              </b-input>
                            </b-field>
                            <b-field label="TPS settings file directory">
                              <b-input
                                size="is-small"
                                v-model="method.tps.settingsFileDirectory"
                                lazy
                              >
                              </b-input>
                            </b-field>
                          </div>
                        </div>
                      </div>
                    </section>
                    <!-- End of TPS section -->
                    <!-- CI section -->
                    <section style="width: 100%; padding: 0.5rem">
                      <div
                        class="card-content"
                        style="background-color: #50505a"
                      >
                        <BaseMetadataForm
                          formTitle="CI configuration"
                          :editable="true"
                          :defaultTemplate="[
                            { label: 'Reagent flow', value: '' },
                            { label: 'Sample flow', value: '' },
                            { label: 'Sheath flow', value: '' },
                          ]"
                          :templatePath="ciTemplatePath"
                          @metaDataUpdated="method.ci = $event"
                        >
                        </BaseMetadataForm>
                      </div>
                    </section>
                    <!-- End of CI section -->
                    <!-- Desorption section -->
                    <section style="width: 100%; padding: 0.5rem">
                      <div
                        class="card-content"
                        style="background-color: #50505a"
                      >
                        <div class="box" style="background-color: inherit">
                          <h1 style="font-size: 16px; text-align: center">
                            <p><b>Desorption cycle</b></p>
                          </h1>
                          <!-- Desorption cycle edot buttons -->
                          <div class="desorption-temperature-ramp-controls">
                            <b-tooltip
                              label="Add step"
                              position="is-left"
                              :delay="500"
                            >
                              <b-button
                                icon-left="file-document-box-plus-outline"
                                size="is-small"
                                type="is-dark"
                                @click="
                                  desorptionTableSelectedRow = null;
                                  launchDesorptionStepModal();
                                "
                                outlined
                                inverted
                              >
                              </b-button>
                            </b-tooltip>
                            <b-tooltip
                              label="Edit step"
                              position="is-left"
                              :delay="500"
                            >
                              <b-button
                                icon-left="file-document-edit-outline"
                                size="is-small"
                                type="is-dark"
                                @click="launchDesorptionStepModal()"
                                v-if="desorptionTableSelectedRow != null"
                                outlined
                                inverted
                              >
                              </b-button>
                            </b-tooltip>
                            <b-tooltip
                              label="Remove step"
                              position="is-left"
                              :delay="500"
                            >
                              <b-button
                                icon-left="trash-can-outline"
                                size="is-small"
                                type="is-dark"
                                @click="deleteDesorptionCycleStep()"
                                v-if="desorptionTableSelectedRow != null"
                                outlined
                                inverted
                              >
                              </b-button>
                            </b-tooltip>
                          </div>
                          <!-- End of desorption cycle edot buttons -->
                          <div class="">
                            <b-table
                              class="
                                desorption-temperature-ramp-table
                                desorption-data-table
                              "
                              :data="desorptionTableData"
                              :columns="desorptionTableColumns"
                              :selected.sync="desorptionTableSelectedRow"
                            >
                            </b-table>
                          </div>
                          <div id="desorption-chart-holder">
                            <div
                              class="columns"
                              style="margin-left: 2px"
                              id="desorption-chart"
                            ></div>
                          </div>
                          <br />
                        </div>
                      </div>
                    </section>
                    <!-- End of Desorption section -->
                  </div>
                  <div style="text-align: center; padding: 10px">
                    <b-button
                      :type="buttonSaveMethodType"
                      @click="saveMethod()"
                    >
                      Save method
                    </b-button>
                  </div>
                </div>
              </b-collapse>
              <!-- End of method collapsable -->
            </section>
          </div>
        </b-collapse>
        <!-- End of instrument control collapsable -->
      </section>
    </section>
    <!-- End of main content area -->
  </div>
</template>


<script>
import { mapState } from "vuex";
import BaseMetadataForm from "./BaseMetadataForm";

const fs = require("fs");
const Plotly = require("plotly.js-dist");
const _ = require("underscore");

export default {
  name: "BaseImportTof",
  components: {
    BaseMetadataForm,
  },
  props: [],
  computed: {
    ...mapState([
      "url",
      "dataSourceSelected",
      "experimentSelected",
      "tofdaqLogEntry",
    ]),
    acquisitionStatus: {
      get() {
        return this.$store.state.acquisitionStatus;
      },
      set(value) {
        this.$store.commit("acquisitionStatus", value);
      },
    },
    newFile: {
      get() {
        return this.$store.state.newFile;
      },
      set(value) {
        this.$store.commit("newFile", value);
      },
    },
  },
  data: function () {
    return {
      // UI variables
      acquisitionButtonType: "is-success",
      acquisitionControlLabel: "Start Acquisition",
      buttonSaveMethodType: "is-success",
      controlModeActive: false,
      isModalAddLogEntryActive: false,
      isModalDesorptionStepActive: false,
      isModalInstrumentLogActive: false,
      // Communication
      be: null,
      namespace: null,
      roomSid: null,
      endpoints: [
        "acquisitionProgress",
        "acquisitionStarted",
        "acquisitionStatus",
        "instrumentStatus",
      ],
      // TOF variables
      acquisitionProgress: 0,
      acquisitionStarted: {},
      instrumentLog: [],
      instrumentLogRows: [],
      instrumentLogCols: [],
      instrumentStatus: "notReady", // notReady/ready
      scenthoundStatus: "Offline", // Offline/Ready/Measuring.../Processing...
      //
      // Method variables
      ciTemplatePath: "./templates/ciTemplates",
      method: {
        tofdaq: {
          acquisitionMode: null,
          sampleLength: null,
        },
        ci: [],
        desorptionCycle: [],
        tps: {
          settingsFile: null,
          settingsFileDirectory: null,
        },
      },
      methodJson: null,
      //
      // Log entry modal variables
      logEntry: null,
      logEntryDatetimestamp: null,
      logEntryDefaultTemplate: [{ label: "Log text", value: "" }],
      logEntryFields: [],
      logEntrySaveButtonType: "is-success",
      logEntryTemplatePath: "./templates/instrument",
      //
      // variables for desorption config
      desorptionStepModalFilterIn: true,
      desorptionStepModalTime: null,
      desorptionStepModalTemperature: null,

      desorptionChartData: [],

      desorptionTableData: [],
      desorptionTableColumns: [
        {
          field: "time",
          label: "time [s]",
        },
        {
          field: "temperature",
          label: "Temp. [C]",
        },
        {
          field: "filterIn",
          label: "Cassette in",
        },
      ],
      desorptionTableSelectedRow: null,
      //
    };
  },
  created: function () {
    this.be = new BECom(this);
    this.confirmAcquisitionControl();
  },
  mounted: function () {
    this.initializeMethod();
  },
  methods: {
    addDesorptionCycleStep() {
      this.method.desorptionCycle.push({
        filterIn: this.desorptionStepModalFilterIn,
        time: this.desorptionStepModalTime,
        temperature: this.desorptionStepModalTemperature,
      });
      this.method.desorptionCycle = this.method.desorptionCycle.sort(function (
        a,
        b
      ) {
        return a.time - b.time;
      });
    },
    confirmAcquisitionControl() {
      this.$buefy.dialog.confirm({
        title: "Instrument control",
        message: `You have requested access to instrument controls.
                          Please proceed only if are willing to operate the instrument.`,
        cancelText: "Cancel",
        confirmText: "Proceed",
        type: "is-danger",
        onCancel: () => (this.controlModeActive = false),
        onConfirm: () => {
          this.$buefy.toast.open({
            message: "Instrument control granted",
            type: "is-success",
          });
          this.be.connect(this.url + "/" + this.dataSourceSelected.name);
        },
      });
    },
    deleteDesorptionCycleStep() {
      var deleteIndex = null;
      for (let i in this.desorptionTableData) {
        if (
          _.isEqual(
            this.desorptionTableData[i],
            this.desorptionTableSelectedRow
          )
        ) {
          deleteIndex = i;
        }
      }
      if (deleteIndex) {
        this.method.desorptionCycle.splice(deleteIndex, 1);
      }
    },
    drawDesorptionTable() {
      this.desorptionTableData = [];
      for (let i in this.method.desorptionCycle) {
        let step = this.method.desorptionCycle[i];
        this.desorptionTableData.push(step);
      }
    },
    drawDesorptionChart() {
      // format the data and draw the chart
      this.desorptionChartData = [_.clone(desorptionChartTrace)];
      let filterIn = true;
      for (let i in this.method.desorptionCycle) {
        var step = this.method.desorptionCycle[i];
        if (step.filterIn != filterIn) {
          filterIn = step.filterIn;
          let prevTrace =
            this.desorptionChartData[this.desorptionChartData.length - 1];
          prevTrace.x.push(step.time);
          prevTrace.y.push(step.temperature);
          let newTrace = _.clone(desorptionChartTrace);
          this.desorptionChartData.push(newTrace);
        }
        this.desorptionChartData[this.desorptionChartData.length - 1].x.push(
          step.time
        );
        this.desorptionChartData[this.desorptionChartData.length - 1].y.push(
          step.temperature
        );
        if (filterIn) {
          this.desorptionChartData[this.desorptionChartData.length - 1].fill =
            "tozeroy";
        }
        desorptionChartLayout["xaxis"].tickvals.push(step.time);
        desorptionChartLayout["xaxis"].ticktext.push(step.time.toString());
        desorptionChartLayout["yaxis"].tickvals.push(step.temperature);
        desorptionChartLayout["yaxis"].ticktext.push(
          step.temperature.toString()
        );
      }
      if (step.time < this.sampleLength) {
        this.desorptionChartData[this.desorptionChartData.length - 1].x.push(
          this.sampleLength
        );
        this.desorptionChartData[this.desorptionChartData.length - 1].y.push(
          step.temperature
        );
      }
      Plotly.react(
        "desorption-chart",
        this.desorptionChartData,
        desorptionChartLayout,
        desorptionChartConfig
      );
    },
    editDesorptionCycle() {
      if (this.desorptionTableSelectedRow) {
        this.deleteDesorptionCycleStep();
      }
      this.addDesorptionCycleStep();
      this.isModalDesorptionStepActive = false;
    },
    onButtonInstrumentLogEntry() {
      this.logEntryDatetimestamp = new Date();
      this.isModalInstrumentLogActive = false;
      this.isModalAddLogEntryActive = true;
    },
    onButtonShowInstrumentLog() {
      this.be.emitClientNotification("instrumentLogRequest", {});
      this.isModalInstrumentLogActive = true;
    },
    onButtonChangeAcquisitionStatus() {
      let nextStatus = {
        notRunning: "starting",
        starting: "stopping",
        running: "stopping",
        stopping: "stopping",
      };
      this.acquisitionStatus = nextStatus[this.acquisitionStatus];
    },
    initializeMethod() {
      try {
        if (fs.existsSync("configs/tofcontrolConfig.json")) {
          let tofcontrolConfig = JSON.parse(
            fs.readFileSync("configs/tofcontrolConfig.json", "utf8")
          );
          this.method = tofcontrolConfig;
        }
      } catch (err) {
        console.error(err);
      }
      // ===== Initialize Plotly figure =====
      Plotly.newPlot(
        "desorption-chart",
        [],
        desorptionChartLayout,
        desorptionChartConfig
      );
    },
    saveMethod() {
      fs.writeFileSync("configs/tofcontrolConfig.json", this.methodJson);
      this.buttonSaveMethodType = "is-success";
    },
    launchDesorptionStepModal() {
      this.desorptionStepModalFilterIn = this.desorptionTableSelectedRow
        ? this.desorptionTableSelectedRow.filterIn
        : true;
      this.desorptionStepModalTime = this.desorptionTableSelectedRow
        ? this.desorptionTableSelectedRow.time
        : null;
      this.desorptionStepModalTemperature = this.desorptionTableSelectedRow
        ? this.desorptionTableSelectedRow.temperature
        : null;
      this.isModalDesorptionStepActive = true;
    },
    writeInstrumentLogEntry() {
      var self = this;

      // Parse datetime into string
      let dt = self.logEntryDatetimestamp;
      let hoursDiff = dt.getHours() - dt.getTimezoneOffset() / 60;
      dt.setHours(hoursDiff);
      // Combine timestamp with log entry fields and write to file
      var logEntryData = {
        timestamp: dt.toJSON(),
        entry: self.logEntryFields,
      };

      self.be.exportOneWayBindingProp(
        "instrumentLogEntry",
        logEntryData,
        self.logEntry
      );
      self.logEntry = logEntryData;
      self.logEntrySaveButtonType = "is-success";
      self.isModalAddLogEntryActive = false;
      self.onButtonShowInstrumentLog();
    },
  },
  watch: {
    dataSourceSelected: function (newValue, oldValue) {
      if (_.isEqual(newValue, oldValue)) return false;
      this.be.disconnect(this.namespace);
      this.be.connect(this.url + "/" + this.dataSourceSelected.name);
    },
    acquisitionStarted: function (newValue, oldValue) {
      if (newValue === oldValue) {
        return false;
      }
      this.newFile = { ...newValue, method: this.method };
    },
    acquisitionStatus: function (newValue, oldValue) {
      if (newValue === oldValue) {
        return false;
      }
      if (newValue === "starting") {
        this.acquisitionControlLabel = "Starting Acquisition";
        this.acquisitionButtonType = "is-danger";
        this.be.emitClientNotification("startAcquisition", {});
      }
      if (newValue === "stopping") {
        this.acquisitionControlLabel = "Stopping Acquisition";
        this.acquisitionButtonType = "is-danger";
        this.scenthoundStatus = "Processing...";
        this.be.emitClientNotification("stopAcquisition", {});
      }
      if (newValue === "running") {
        this.sampleTableCheckedRows = [];
        this.acquisitionControlLabel = "Stop Acquisition";
        this.acquisitionButtonType = "is-danger";
        this.scenthoundStatus = "Measuring...";
      }
      if (newValue === "notRunning") {
        this.acquisitionControlLabel = "Start Acquisition";
        this.acquisitionButtonType = "is-success";
        this.scenthoundStatus = "Ready";
      }
    },
    instrumentLog: function (newValue) {
      if (!newValue.length) {
        this.instrumentLogRows = [];
        this.instrumentLogCols = [];
        return;
      }
      let colFields = [];
      let cols = [{ field: "timestamp", label: "Timestamp", searchable: true }];
      let rows = [];
      for (let i in newValue) {
        var row = {};
        const entryData = newValue[i];
        const timestamp = entryData.timestamp;
        row.timestamp = timestamp;
        const entry = entryData.entry;
        for (let j in entry) {
          const label = entry[j].label;
          const field = label.toLowerCase();
          if (colFields.indexOf(field) == -1) {
            // Add field
            colFields.push(field);
            cols.push({ field: field, label: label, searchable: true });
          }
          const value = entry[j].value;
          row[field] = value;
        }
        rows.push(row);
      }
      this.instrumentLogRows = rows;
      this.instrumentLogCols = cols;

      // Update log entry default template with all existing fields
      let instrumentLogAllFields = [];
      for (let i = 1; i < cols.length; ++i) {
        // Ignore timestamp
        const field = {
          label: cols[i].label,
          value: row[cols[i].field] || "", // Value from last entry
        };
        instrumentLogAllFields.push(field);
      }
      this.logEntryDefaultTemplate = instrumentLogAllFields;
    },
    instrumentStatus: function (newValue, oldValue) {
      if (_.isEqual(newValue, oldValue)) {
        return false;
      }
      if (newValue === "ready") {
        this.scenthoundStatus = "Ready";
      } else {
        this.scenthoundStatus = "Offline";
        this.acquisitionStatus = "notRunning";
      }
    },
    logEntryFields: {
      handler() {
        this.logEntrySaveButtonType = "is-danger";
      },
      deep: true,
    },
    method: {
      handler() {
        this.methodJson = JSON.stringify(this.method, null, 4);
        this.buttonSaveMethodType = "is-danger";
      },
      deep: true,
    },
    "method.desorptionCycle": function () {
      this.drawDesorptionTable();
      this.drawDesorptionChart();
    },
    tofdaqLogEntry: function (newValue, oldValue) {
      let texts = newValue.text.split("<br>").slice(0, -1);
      for (let i in texts) {
        texts[i] = texts[i].replace(": ", "=");
      }
      const jointText = texts.join(", ");
      newValue.text = jointText.slice(0, 255);

      this.be.exportOneWayBindingProp(
        "tofdaqLogEntry",
        newValue,
        oldValue,
        this.roomSid
      );
    },
    "namespace.connected": function (newValue) {
      if (newValue) {
        // on connect
        this.controlModeActive = true;
        // handlers for for external notifications:
        this.namespace.on("acquisitionStarted", (value) =>
          this.be.importOneWayBindingProp("acquisitionStarted", value.value)
        );
        this.namespace.on("acquisitionStatus", (value) =>
          this.be.importOneWayBindingProp("acquisitionStatus", value.value)
        );
        this.namespace.on("acquisitionProgress", (value) =>
          this.be.importOneWayBindingProp(
            "acquisitionProgress",
            value.value.progress,
            true
          )
        );
        this.namespace.on("instrumentLog", (value) =>
          this.be.importOneWayBindingProp("instrumentLog", value.value)
        );
        this.namespace.on("instrumentStatus", (value) =>
          this.be.importOneWayBindingProp("instrumentStatus", value.value)
        );

        this.be.subscribe(
          this.endpoints,
          null // room set to null to subscribe to endpoints directly
        );
      } else {
        // on disconnect
        this.controlModeActive = false;
      }
    },
  },
};

var desorptionChartTrace = {
  name: "",
  line: {
    shape: "hv",
  },
  mode: "lines",
  type: "scatter",
  x: [],
  y: [],
  hoverinfo: "x,y",
};

var desorptionChartLayout = {
  width: 280,
  height: 280,

  font: {
    color: "#fff",
  },

  xaxis: {
    title: "time [s]",
    tickmode: "array",
    tickvals: [],
    ticktext: [],
    visible: true,
    linecolor: "#999",
    rangemode: "tozero",
    showgrid: false,
  },

  yaxis: {
    title: "Temperature [C]",
    tickmode: "array",
    tickvals: [],
    ticktext: [],
    visible: true,
    linecolor: "#999",
    rangemode: "tozero",
    showgrid: false,
  },

  showlegend: false,
  dragmode: false,

  plotBgcolor: "transparent",
  paperBgcolor: "transparent",

  margin: {
    l: 30,
    r: 20,
    b: 25,
    t: 60,
    pad: 0,
  },
};

var desorptionChartConfig = {
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: [
    "autoScale2d",
    "hoverClosestGl2d",
    "hoverClosestCartesian",
    "hoverCompareCartesian",
    "lasso2d",
    "pan2d",
    "resetScale2d",
    "select2d",
    "toggleSpikelines",
    "toImage",
    "zoom2d",
    "zoomIn2d",
    "zoomOut2d",
  ],
};
</script>


<style scoped>
/* desorption */

.desorption-data-table {
  color: #a7a7a7;
  margin: 3px 10px 20px 10px;
}

.desorption-temprature-ramp {
  margin-top: 5px;
}

.desorption-temperature-ramp-controls {
  text-align: right;
  margin-top: 5px;
  margin-right: 7px;
}

.desorption-temperature-ramp-controls > .button {
  margin-right: 3px;
}

#desorption-chart-holder {
  margin-right: 0px;
}

.desorption-chart {
  margin-top: 20px;
}

.desorption-datatable {
  padding-right: 0px;
}

.add-new-desorption-row {
  padding: 10px;
}
</style>