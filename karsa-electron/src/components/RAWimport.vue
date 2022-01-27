<template>
  <div>
    <!-- Modals -->
    <!-- Modal for raw import -->
    <section class="raw-import-modal">
      <b-modal
        :active.sync="is_raw_import_modal_active"
        has-modal-card
        trap-focus
        :can-cancel="true"
        aria-role="dialog"
        aria-modal
      >
        <div class="columns">
          <div class="modal-card" style="width: 500px; height: 700px">
            <header class="modal-card-head">
              <p class="modal-card-title">
                Import {{ data_source_selected.type }} files
              </p>
            </header>
            <section class="modal-card-body">
              <b-field label="Start">
                <b-datetimepicker
                  v-model="import_start_time"
                  placeholder="Start datetime"
                  :timepicker="{ 'hour-format': '24' }"
                  :min-datetime="import_min_datetime"
                  :max-datetime="import_max_datetime"
                >
                </b-datetimepicker>
              </b-field>
              <b-field label="End">
                <b-datetimepicker
                  v-model="import_end_time"
                  placeholder="End datetime"
                  :timepicker="{ 'hour-format': '24' }"
                  :min-datetime="import_start_time"
                  :max-datetime="import_max_datetime"
                >
                </b-datetimepicker>
              </b-field>
              <button
                class="button"
                type="button"
                @click="FetchSamples()"
                is-dark
                :disabled="
                  instrument_status === 'not_ready' ||
                  import_start_time === null ||
                  import_end_time === null
                    ? true
                    : false
                "
              >
                Fetch {{ data_source_selected.name }} list
              </button>
              <div><br /></div>
              <b-table
                id="raw-samples-table"
                :columns="import_raw_table_cols"
                :data="import_raw_table_rows"
                :checkable="true"
                :checked-rows.sync="import_raw_table_checked_rows"
              >
              </b-table>
              <div><br /></div>
            </section>
            <footer class="modal-card-foot">
              <button
                class="button"
                type="button"
                @click="ImportSamples()"
                is-dark
                :disabled="
                  !import_raw_table_checked_rows.length ||
                  import_start_time === null ||
                  import_end_time === null
                    ? true
                    : false
                "
              >
                Import
              </button>
              <button
                class="button"
                type="button"
                is-dark
                @click="
                  import_raw_table_checked_rows = [];
                  is_raw_import_modal_active = false;
                "
              >
                Cancel
              </button>
              <b-upload v-model="batch_import_list" class="file-label" rounded>
                <span class="file-cta">
                  <b-icon
                    class="file-icon"
                    icon="file-document-outline"
                  ></b-icon>
                  <span class="file-label">Batch Import...</span>
                </span>
              </b-upload>
            </footer>
          </div>
        </div>
      </b-modal>
    </section>
    <!-- End of raw import modal -->
    <!-- Modal for raw import status-->
    <section class="raw-import-status-modal">
      <b-modal
        :active.sync="is_raw_import_status_modal_active"
        has-modal-card
        trap-focus
        :can-cancel="true"
        aria-role="dialog"
        aria-modal
      >
        <div class="columns">
          <div class="modal-card" style="width: auto; height: 700px">
            <header class="modal-card-head">
              <p class="modal-card-title">
                Status of {{ data_source_selected.name }} Import...
              </p>
              <button
                class="button"
                type="button"
                @click="on_button_acquisition_status()"
              >
                Refresh
              </button>
            </header>
            <section class="modal-card-body">
              <b-table
                :data="raw_import_status_rows"
                :columns="raw_import_status_cols"
                :checkable="true"
                :checked-rows.sync="raw_import_status_checked_rows"
                :striped="true"
                :narrowed="true"
                :hoverable="true"
                draggable
                @dragstart="DragStart"
                @drop="DragDrop"
                @dragover="DragOver"
                @dragleave="DragLeave"
              >
              </b-table>
            </section>
            <footer class="modal-card-foot">
              <b-tooltip
                label="Import samples by modified import list"
                position="is-right"
              >
                <button
                  class="button"
                  type="button"
                  @click="
                    StopImportSamples();
                    import_raw_table_checked_rows = raw_import_status_rows;
                    is_raw_import_status_modal_active = false;
                    ImportSamples();
                  "
                  :disabled="is_raw_import_data_modified ? false : true"
                >
                  ReImport
                </button>
                <div />
              </b-tooltip>
              <button
                class="button"
                type="button"
                @click="
                  raw_import_status_checked_rows = [];
                  is_raw_import_status_modal_active = false;
                "
              >
                Cancel
              </button>
              <div style="position: absolute; right: 20px">
                <b-tooltip
                  label="Remove selected items from import list"
                  position="is-left"
                >
                  <b-button
                    type="is-dark"
                    icon-left="delete"
                    :disabled="
                      raw_import_status_checked_rows.length == 0 ? true : false
                    "
                    @click="RemoveCheckedRows()"
                  >
                  </b-button>
                </b-tooltip>
              </div>
            </footer>
          </div>
        </div>
      </b-modal>
    </section>
    <!-- End of raw import status modal -->
    <!-- End of modals -->

    <!-- Main content area -->
    <section>
      <!-- Acquisiton parameters collapsable -->
      <section>
        <b-collapse class="card" animation="slide" aria-id="contentIdForA11y3">
          <div
            slot="trigger"
            slot-scope="props"
            class="card-header"
            role="button"
            aria-controls="contentIdForA11y3"
          >
            <p class="card-header-title">
              {{ data_source_selected.name }} import
            </p>
            <a class="card-header-icon">
              <b-icon :icon="props.open ? 'menu-down' : 'menu-up'"> </b-icon>
            </a>
          </div>
          <div class="card-content">
            <div class="content">
              <div
                style="
                  text-align: center;
                  margin-top: 0.4rem;
                  margin-bottom: 1rem;
                "
              >
                <h1 class="acquisition-parameters-h1">
                  {{ data_source_selected.type }} streamer status:
                  {{ instrument_status }}
                </h1>
              </div>
              <div
                style="
                  margin-left: 1rem;
                  margin-right: 1rem;
                  margin-bottom: 1rem;
                "
              >
                <b-progress
                  v-bind:value="acquisition_progress"
                  show-value
                  format="percent"
                  :precision="1"
                  type="is-primary"
                  size="is-large"
                >
                </b-progress>
              </div>
              <div style="text-align: center">
                <b-button
                  type="is-dark"
                  @click="on_button_acquisition_control()"
                  outlined
                  inverted
                  :disabled="instrument_status == 'ready' ? false : true"
                >
                  {{ acquisition_control_label }}
                </b-button>
                <b-button
                  type="is-dark"
                  @click="on_button_acquisition_status()"
                  outlined
                  inverted
                  :disabled="instrument_status == 'ready' ? false : true"
                >
                  Status
                </b-button>
                <div><br /></div>
              </div>
            </div>
          </div>
        </b-collapse>
        <!-- End of  Acquisition parameters collapsable -->
      </section>
    </section>
    <!-- End of main content area -->
  </div>
</template>

<script type="text/javascript">
"use strict";
import csv from "jquery-csv";
import Vue from "vue";
import { mapState } from "vuex";
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import "@mdi/font/css/materialdesignicons.min.css";
import { BECom } from "../karsalib.js";

Vue.use([Buefy]);

var _ = require("underscore");

export default {
  name: "Rawimport", //used as app_name - keep it unique
  components: {},
  computed: {
    ...mapState(["data_source_selected", "url"]),
    acquisition_status: {
      get() {
        return this.$store.state.acquisition_status;
      },
      set(value) {
        this.$store.commit("acquisition_status", value);
      },
    },
    new_file: {
      get() {
        return this.$store.state.new_file;
      },
      set(value) {
        this.$store.commit("new_file", value);
      },
    },
  },
  data: function () {
    return {
      be: null,
      namespace: null,
      room_sid: null,
      endpoints: [
        "acquisition_progress",
        "acquisition_started",
        "acquisition_finished",
        "acquisition_status",
        "instrument_status",
        "raw_import_status_data",
        "service_error",
      ],
      // raw streamer
      acquisition_control_label: null,
      acquisition_progress: 0,
      acquisition_in_progress: false,
      acquisition_started: {},
      acquisition_finished: {},
      is_raw_import_modal_active: false,
      raw_samples: [],
      instrument_status: "not_ready", // not_ready/ready
      service_error: "",
      raw_import: [],
      stop_raw_import: [],
      // variables for import modal
      import_start_time: new Date(new Date().getFullYear(),
                                  new Date().getMonth(),
                                  new Date().getDate(),
                                  0,
                                  0
                                  ),
      import_end_time: new Date(new Date().getFullYear(),
                                new Date().getMonth(),
                                new Date().getDate(),
                                23,
                                59
                                ),
      import_min_datetime: null,
      import_max_datetime: new Date(),
      import_raw_table_rows: [],
      import_raw_table_cols: [],
      import_raw_table_checked_rows: [],
      import_raw_table_datetime_range: {},
      batch_import_list: {},
      // raw import status vars
      is_raw_import_status_modal_active: false,
      is_raw_import_data_modified: false,
      raw_import_status_data: {},
      raw_import_status_rows: [],
      raw_import_status_cols: [],
      raw_import_status_checked_rows: [],
      // raw import status dialog vars
      draggingRow: null,
      draggingRowIndex: null,
    };
  },
  created: function () {
    this.be = new BECom(this);
    this.namespace = this.be.connect(
      this.url + "/" + this.data_source_selected.name
    );
  },
  methods: {
    FetchSamples() {
      if (this.import_start_time == null || this.import_end_time == null) {
        this.$buefy.toast.open({
          duration: 3000,
          message: "You must select datetime range first!",
          type: "is-danger",
          queue: false,
        });
        return;
      }
      // Revert automatic timezone adjustment
      let dt0 = new Date(this.import_start_time.getTime()); // copy
      let start_hours_diff = dt0.getHours() - dt0.getTimezoneOffset() / 60;
      dt0.setHours(start_hours_diff);

      let dt1 = new Date(this.import_end_time.getTime()); // copy
      let end_hours_diff = dt1.getHours() - dt1.getTimezoneOffset() / 60;
      dt1.setHours(end_hours_diff);

      // Request list of raw files in given range
      let fetch_request = {
        dt0: dt0.toJSON(),
        dt1: dt1.toJSON(),
        uid: Math.random(),
      };
      this.import_raw_table_datetime_range = fetch_request;
    },
    ImportSamples() {
      this.raw_import = this.import_raw_table_checked_rows;
      this.is_raw_import_modal_active = false;
      this.import_raw_table_checked_rows = [];
    },
    StopImportSamples() {
        this.acquisition_control_label = "Stopping...";
        this.be.emit_client_notification("stop_raw_import", this.raw_import);
    },
    on_button_acquisition_control() {
      if (this.acquisition_in_progress) {
        this.StopImportSamples();
      } else {
        // pop up FetchSamples dialog
        this.is_raw_import_modal_active = true;
        this.FetchSamples();
      }
    },
    on_button_acquisition_status() {
      this.be.emit_client_notification("raw_import_status", {});
      this.is_raw_import_data_modified = false;
      this.raw_import_status_checked_rows = [];
      this.is_raw_import_status_modal_active = true;
    },
    DragStart(payload) {
      this.draggingRow = payload.row;
      this.draggingRowIndex = payload.index;
      payload.event.dataTransfer.effectAllowed = "move";
    },
    DragOver(payload) {
      payload.event.dataTransfer.dropEffect = "move";
      payload.event.target.closest("tr").classList.add("is-selected");
      payload.event.preventDefault();
    },
    DragLeave(payload) {
      payload.event.target.closest("tr").classList.remove("is-selected");
      payload.event.preventDefault();
    },
    DragDrop(payload) {
      payload.event.target.closest("tr").classList.remove("is-selected");
      const iFrom = this.draggingRowIndex;
      const iTo = payload.index;
      this.$buefy.toast.open({
        message: `Import list item moved from row ${iFrom + 1} to row ${
          iTo + 1
        }`,
        type: "is-success",
        duration: 3000,
      });
      this.ArrayMoveRow(this.raw_import_status_rows, iFrom, iTo);
      this.is_raw_import_data_modified = true;
    },
    RemoveCheckedRows() {
      let rows = this.raw_import_status_checked_rows;
      this.raw_import_status_checked_rows = [];
      this.$buefy.toast.open({
        message: `Removed ${rows.length} items from import list`,
        type: "is-success",
        duration: 3000,
      });
      rows.forEach((row) =>
        this.raw_import_status_rows.splice(
          this.raw_import_status_rows.indexOf(row),
          1
        )
      );
      this.is_raw_import_data_modified = true;
    },
    ArrayMoveRow(a, iFrom, iTo) {
      let e = a[iFrom];
      a.splice(iFrom, 1);
      a.splice(iTo, 0, e);
    },
  },
  watch: {
    acquisition_started: function (new_value) {
      // if (new_value === old_value) {
      //     return false;
      // }
      this.new_file = new_value;
      this.acquisition_control_label = "Stop Import";
      this.acquisition_in_progress = true;
    },
    acquisition_finished: function () {
      // if (new_value === old_value) {
      //     return false;
      // }
      this.acquisition_control_label =
        "Import " + this.data_source_selected.name;
      this.acquisition_in_progress = false;
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
    // import_raw_table_checked_rows: function(new_value, old_value) {
    //     if ( _.isEqual(new_value, old_value) ) {
    //         return false;
    //     }
    //     var last_selection = [...new_value].pop();
    //     // force single row selection
    //     if ( this.import_raw_table_checked_rows.length > 1 ) {
    //         this.import_raw_table_checked_rows = [last_selection,];
    //     }
    // },
    raw_samples: function (new_data, old_data) {
      if (_.isEqual(new_data, old_data)) {
        return false;
      }
      this.import_raw_table_cols = new_data.cols;
      this.import_raw_table_rows = new_data.rows;
    },
    raw_import_status_data: function (new_data) {
      // // data left for debugging:
      // new_data = {
      //     progress: [
      //         {filename: '1-DataFile_2021.08.02-01h01m00s.h5', path: 'test\\system\\TestData\\DataPool\\H5\\2021.08.02',
      //          props: {datetime: '2021.08.02 01h01m00s', filesize: 2.96}, attrs: {project, experiment ...}, progress: 30.0, ack_progress: 16.67},
      //     ],
      //     queue: {
      //         context: { client_room: 'ZbRWlHlHocoMPKrwAABP', room: null, no_logging: false, no_data_logging: true, cookies: {src_sid: ['ZbRWlHlHocoMPKrwAABP']} },
      //         files: [
      //            {filename: '2-DataFile_2021.08.02-01h01m00s.h5', path: 'test\\system\\TestData\\DataPool\\H5\\2021.08.02', props: {datetime: '2021.08.02 01h01m00s', filesize: 2.96}, attrs: {project, experiment ...}},
      //            {filename: '3-DataFile_2021.08.02-01h01m00s.h5', path: 'test\\system\\TestData\\DataPool\\H5\\2021.08.02', props: {datetime: '2021.08.02 01h01m00s', filesize: 2.96}, attrs: {project, experiment ...}},
      //            {filename: '4-DataFile_2021.08.02-01h01m00s.h5', path: 'test\\system\\TestData\\DataPool\\H5\\2021.08.02', props: {datetime: '2021.08.02 01h01m00s', filesize: 2.96}, attrs: {project, experiment ...}},
      //         ]
      //     }
      // };

      // this.raw_import_status_rows = new_data.progress.concat(
      //   new_data.queue.files || []
      // );

      const straight_filter = (obj) => {
        var res = new Object;
        for (let k in obj) {
          if ( typeof obj[k] === "object" )
            res = {...res, ...obj[k]};
          else
            res[k] = obj[k];
        }
        return res;
      };

      this.raw_import_status_rows = []

      if ( !_.isEmpty(new_data.progress) )
        new_data.progress.forEach(
          (pdata) => {
            this.raw_import_status_rows = this.raw_import_status_rows.concat(straight_filter(pdata));
          }
        );
      if ( !_.isEmpty(new_data.queue.files) )
        new_data.queue.files.forEach(
          (fdata) => {
            this.raw_import_status_rows = this.raw_import_status_rows.concat(straight_filter(fdata));
          }
        );

      let titles = new Set([]);
      this.raw_import_status_rows.forEach(
        (r) => (titles = new Set([...titles, ...Object.keys(r)]))
      );
      let cols = [];
      titles.forEach((t) => (cols = cols.concat({ field: t, label: t })));
      this.raw_import_status_cols = [...cols];
    },
    raw_import: function (new_value, old_value) {
      return this.be.export_one_way_binding_prop(
        "raw_import",
        new_value,
        old_value,
        null,
        null,
        this.namespace
      );
    },
    import_raw_table_datetime_range: function (new_value, old_value) {
      return this.be.export_one_way_binding_prop(
        "import_raw_table_datetime_range",
        new_value,
        old_value,
        this.room_sid,
        null,
        this.namespace
      );
    },
    data_source_selected: function (new_value, old_value) {
      if (_.isEqual(new_value, old_value)) {
        return false;
      }
      // TODO: this is to refresh the datetimepicker, but it doesn't re-render it: why?
      // this.import_start_time = null;
      // this.import_end_time = null;
      this.import_raw_table_cols = [];
      this.import_raw_table_rows = [];
      this.be.disconnect(this.namespace);
      this.namespace = this.be.connect(
        this.url + "/" + this.data_source_selected.name
      );
    },
    import_start_time: function (new_value) {
      if (
        !this.import_end_time ||
        Date.parse(new_value) > Date.parse(this.import_end_time)
      )
        this.import_end_time = new Date(Date.parse(new_value));
    },
    batch_import_list: async function (new_value) {
      if (!new_value.text) {
        return;
      }
      const requiredFields = ['title', 'project', 'experiment', 'filename'];

      let data = await new_value.text();
      data = csv.toObjects(data);
      // Validate
      for (let d of data) {
        for (let field of requiredFields) {
          if (Object.keys(d).indexOf(field) == -1 ||
              _.isEmpty(d[field])
              ){
                this.$buefy.dialog.alert({
                    title: "Parsing error",
                    message: "Please check csv format. It must contain fields: " + requiredFields,
                    type: "is-danger",
                    hasIcon: true,
                    icon: "times-circle",
                    iconPack: "fa",
                    ariaRole: "alertdialog",
                    ariaModal: true,
                  });
              return false;
          }
        }
      }

      this.raw_import = data;

      this.import_raw_table_checked_rows = [];
      this.import_raw_table_rows = [];
      this.import_raw_table_cols = [];
      this.import_start_time = null;
      this.import_end_time = null;
      this.is_raw_import_modal_active = false;
    },
    "namespace.connected": function (new_value) {
      if (new_value === true) {
        // handlers for for external notifications:
        this.namespace.on("acquisition_started", (value) =>
          this.be.import_one_way_binding_prop(
            "acquisition_started",
            value.value
          )
        );
        this.namespace.on("acquisition_finished", (value) =>
          this.be.import_one_way_binding_prop(
            "acquisition_finished",
            value.value
          )
        );
        this.namespace.on("acquisition_status", (value) =>
          this.be.import_one_way_binding_prop("acquisition_status", value.value)
        );
        this.namespace.on("acquisition_progress", (value) =>
          this.be.import_one_way_binding_prop(
            "acquisition_progress",
            value.value.progress,
            true
          )
        );
        this.namespace.on("instrument_status", (value) =>
          this.be.import_two_way_binding_prop("instrument_status", value.value)
        );
        this.namespace.on("service_error", (value) =>
          this.be.import_two_way_binding_prop("service_error", value.value)
        );
        this.namespace.on("raw_samples", (value) =>
          this.be.import_one_way_binding_prop("raw_samples", value.value)
        );
        this.namespace.on("raw_import_status_data", (value) =>
          this.be.import_one_way_binding_prop(
            "raw_import_status_data",
            value.value
          )
        );
        this.acquisition_control_label =
          "Import " + this.data_source_selected.name;
        this.be.declare_endpoints(this.endpoints);
      }
    },
  },
};
</script>
