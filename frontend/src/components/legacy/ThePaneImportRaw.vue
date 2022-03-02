<template>
  <div>
    <!-- Modals -->
    <!-- Modal for raw import -->
    <!-- End of raw import modal -->
    <!-- Modal for raw import status-->
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
              {{ dataSourceSelected.name }} import
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
                  {{ dataSourceSelected.type }} streamer status:
                  {{ instrumentStatus }}
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
                  v-bind:value="acquisitionProgress"
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
                  @click="onButtonAcquisitionControl()"
                  outlined
                  inverted
                  :disabled="instrumentStatus == 'ready' ? false : true"
                >
                  {{ acquisitionControlLabel }}
                </b-button>
                <b-button
                  type="is-dark"
                  @click="onButtonAcquisitionStatus()"
                  outlined
                  inverted
                  :disabled="instrumentStatus == 'ready' ? false : true"
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
import csv from "jquery-csv";
import { mapState } from "vuex";

const _ = require("underscore");

export default {
  name: "BaseImportRaw",
  components: {},
  computed: {
    ...mapState(["dataSourceSelected", "url"]),
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
      be: null,
      namespace: null,
      roomSid: null,
      endpoints: [
        "acquisitionProgress",
        "acquisitionStarted",
        "acquisitionFinished",
        "acquisitionStatus",
        "instrumentStatus",
        "rawImportStatusData",
        "serviceError",
      ],
      // raw streamer
      acquisitionControlLabel: null,
      acquisitionProgress: 0,
      acquisitionInProgress: false,
      acquisitionStarted: {},
      acquisitionFinished: {},
      isRawImportModalActive: false,
      rawSamples: [],
      instrumentStatus: "notReady", // notReady/ready
      serviceError: "",
      rawImport: [],
      // variables for import modal
      importStartTime: null,
      importEndTime: null,
      importMinDatetime: null,
      importMaxDatetime: new Date(),
      importRawTableRows: [],
      importRawTableCols: [],
      importRawTableCheckedRows: [],
      importRawTableDatetimeRange: {},
      batchImportList: {},
      // raw import status vars
      isRawImportStatusModalActive: false,
      isRawImportDataModified: false,
      rawImportStatusData: {},
      rawImportStatusRows: [],
      rawImportStatusCols: [],
      rawImportStatusCheckedRows: [],
      // raw import status dialog vars
      draggingRow: null,
      draggingRowIndex: null,
    };
  },
  created: function () {
    this.be = new BECom(this);
    this.namespace = this.be.connect(
      this.url + "/" + this.dataSourceSelected.name
    );
  },
  methods: {
    fetchSamples() {
      if (this.importStartTime == null || this.importEndTime == null) {
        this.$buefy.toast.open({
          duration: 3000,
          message: "You must select datetime range first!",
          type: "is-danger",
          queue: false,
        });
        return;
      }
      // Revert automatic timezone adjustment
      let dt0 = new Date(this.importStartTime.getTime()); // copy
      let startHoursDiff = dt0.getHours() - dt0.getTimezoneOffset() / 60;
      dt0.setHours(startHoursDiff);

      let dt1 = new Date(this.importEndTime.getTime()); // copy
      let endHoursDiff = dt1.getHours() - dt1.getTimezoneOffset() / 60;
      dt1.setHours(endHoursDiff);

      // Request list of raw files in given range
      let fetchRequest = {
        dt0: dt0.toJSON(),
        dt1: dt1.toJSON(),
      };
      this.importRawTableDatetimeRange = fetchRequest;
    },
    importSamples() {
      this.rawImport = this.importRawTableCheckedRows;
      this.isRawImportModalActive = false;
      this.importRawTableCheckedRows = [];
    },
    onButtonAcquisitionControl() {
      if (this.acquisitionInProgress) {
        // Interrupt import
        this.acquisitionControlLabel = "Stopping...";
        this.be.emitClientNotification("stopRawImport", this.rawImport);
      } else {
        // pop up FetchSamples dialog
        this.isRawImportModalActive = true;
      }
    },
    onButtonAcquisitionStatus() {
      this.be.emitClientNotification("rawImportStatus", {});
      this.isRawImportDataModified = false;
      this.rawImportStatusCheckedRows = [];
      this.isRawImportStatusModalActive = true;
    },
    dragStart(payload) {
      this.draggingRow = payload.row;
      this.draggingRowIndex = payload.index;
      payload.event.dataTransfer.effectAllowed = "move";
    },
    dragOver(payload) {
      payload.event.dataTransfer.dropEffect = "move";
      payload.event.target.closest("tr").classList.add("is-selected");
      payload.event.preventDefault();
    },
    dragLeave(payload) {
      payload.event.target.closest("tr").classList.remove("is-selected");
      payload.event.preventDefault();
    },
    dragDrop(payload) {
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
      this.ArrayMoveRow(this.rawImportStatusRows, iFrom, iTo);
      this.isRawImportDataModified = true;
    },
    removeCheckedRows() {
      let rows = this.rawImportStatusCheckedRows;
      this.rawImportStatusCheckedRows = [];
      this.$buefy.toast.open({
        message: `Removed ${rows.length} items from import list`,
        type: "is-success",
        duration: 3000,
      });
      rows.forEach((row) =>
        this.rawImportStatusRows.splice(
          this.rawImportStatusRows.indexOf(row),
          1
        )
      );
      this.isRawImportDataModified = true;
    },
    arrayMoveRow(a, iFrom, iTo) {
      let e = a[iFrom];
      a.splice(iFrom, 1);
      a.splice(iTo, 0, e);
    },
  },
  watch: {
    acquisitionStarted: function (newValue) {
      // if (newValue === oldValue) {
      //     return false;
      // }
      this.newFile = newValue;
      this.acquisitionControlLabel = "Stop Import";
      this.acquisitionInProgress = true;
    },
    acquisitionFinished: function () {
      // if (newValue === oldValue) {
      //     return false;
      // }
      this.acquisitionControlLabel = "Import " + this.dataSourceSelected.name;
      this.acquisitionInProgress = false;
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
    rawSamples: function (newData, oldData) {
      if (_.isEqual(newData, oldData)) {
        return false;
      }
      this.importRawTableCols = newData.cols;
      this.importRawTableRows = newData.rows;
    },
    rawImportStatusData: function (newData) {
      // // data left for debugging:
      // newData = {
      //     progress: [
      //         {filename: '1-DataFile_2021.08.02-01h01m00s.h5', targetFilename: 'H5Data_1-DataFile_2021.08.02-01h01m00s.h5',
      //          datetime: '2021.08.02 01h01m00s', filesize: 2.96, path: 'test\\system\\TestData\\DataPool\\H5\\2021.08.02', progress: 30.0, ackProgress: 16.67},
      //     ],
      //     queue: {
      //         context: { clientRoom: 'ZbRWlHlHocoMPKrwAABP', room: null, noLogging: false, noDataLogging: true, cookies: {srcSid: ['ZbRWlHlHocoMPKrwAABP']} },
      //         files: [
      //             {filename: '2-DataFile_2021.08.02-01h01m00s.h5', datetime: '2021.08.02 01h01m00s', filesize: 2.96, path: 'test\\system\\TestData\\DataPool\\H5\\2021.08.02'},
      //             {filename: '3-DataFile_2021.08.02-01h01m00s.h5', datetime: '2021.08.02 01h01m00s', filesize: 2.96, path: 'test\\system\\TestData\\DataPool\\H5\\2021.08.02'},
      //             {filename: '4-DataFile_2021.08.02-01h01m00s.h5', datetime: '2021.08.02 01h01m00s', filesize: 2.96, path: 'test\\system\\TestData\\DataPool\\H5\\2021.08.02'},
      //         ]
      //     }
      // };

      this.rawImportStatusRows = newData.progress.concat(
        newData.queue.files || []
      );
      let titles = new Set([]);
      this.rawImportStatusRows.forEach(
        (r) => (titles = new Set([...titles, ...Object.keys(r)]))
      );
      let cols = [];
      titles.forEach((t) => (cols = cols.concat({ field: t, label: t })));
      this.rawImportStatusCols = [...cols];
    },
    rawImport: function (newValue, oldValue) {
      return this.be.exportOneWayBindingProp(
        "rawImport",
        newValue,
        oldValue,
        null,
        null,
        this.namespace
      );
    },
    importRawTableDatetimeRange: function (newValue, oldValue) {
      return this.be.exportOneWayBindingProp(
        "importRawTableDatetimeRange",
        newValue,
        oldValue,
        this.roomSid,
        null,
        this.namespace
      );
    },
    dataSourceSelected: function (newValue, oldValue) {
      if (_.isEqual(newValue, oldValue)) {
        return false;
      }
      // TODO: this is to refresh the datetimepicker, but it doesn't re-render it: why?
      // this.importStartTime = null;
      // this.importEndTime = null;
      this.importRawTableCols = [];
      this.importRawTableRows = [];
      this.be.disconnect(this.namespace);
      this.namespace = this.be.connect(
        this.url + "/" + this.dataSourceSelected.name
      );
    },
    importStartTime: function (newValue) {
      if (
        !this.importEndTime ||
        Date.parse(newValue) > Date.parse(this.importEndTime)
      )
        this.importEndTime = new Date(Date.parse(newValue));
    },
    batchImportList: async function (newValue) {
      if (!newValue.text) {
        return;
      }
      this.isRawImportModalActive = false;
      this.importRawTableCheckedRows = [];
      this.importRawTableRows = [];
      this.importRawTableCols = [];
      this.importStartTime = null;
      this.importEndTime = null;
      let data = await newValue.text();
      data = csv.toObjects(data);
      this.rawImport = data;
    },
    "namespace.connected": function (newValue) {
      if (newValue === true) {
        // handlers for for external notifications:
        this.namespace.on("acquisitionStarted", (value) =>
          this.be.importOneWayBindingProp("acquisitionStarted", value.value)
        );
        this.namespace.on("acquisitionFinished", (value) =>
          this.be.importOneWayBindingProp("acquisitionFinished", value.value)
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
        this.namespace.on("instrumentStatus", (value) =>
          this.be.importTwoWayBindingProp("instrumentStatus", value.value)
        );
        this.namespace.on("serviceError", (value) =>
          this.be.importTwoWayBindingProp("serviceError", value.value)
        );
        this.namespace.on("rawSamples", (value) =>
          this.be.importOneWayBindingProp("rawSamples", value.value)
        );
        this.namespace.on("rawImportStatusData", (value) =>
          this.be.importOneWayBindingProp("rawImportStatusData", value.value)
        );
        this.acquisitionControlLabel = "Import " + this.dataSourceSelected.name;
        this.be.subscribe(
          this.endpoints,
          null // room set to null to subscribe to endpoints directly
        );
      }
    },
  },
};
</script>
