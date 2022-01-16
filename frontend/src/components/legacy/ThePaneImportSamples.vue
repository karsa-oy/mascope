<template>
  <div>
    <section class="sample-import">
      <div>
        <b-field label="Data source" custom-class="dark">
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
        </b-field>
        <section class="modal-card-body">
          <b-field label="Start" custom-class="dark">
            <b-datetimepicker
              v-model="importStartTime"
              placeholder="Start datetime"
              :timepicker="{ 'hour-format': '24' }"
              :min-datetime="importMinDatetime"
              :max-datetime="importMaxDatetime"
            >
            </b-datetimepicker>
          </b-field>
          <b-field label="End" custom-class="dark">
            <b-datetimepicker
              v-model="importEndTime"
              placeholder="End datetime"
              :timepicker="{ 'hour-format': '24' }"
              :min-datetime="importStartTime"
              :max-datetime="importMaxDatetime"
            >
            </b-datetimepicker>
          </b-field>
          <button
            class="button"
            type="button"
            @click="fetchSamples()"
            is-dark
            :disabled="
              importStartTime === null || importEndTime === null ? true : false
            "
          >
            Fetch samples
          </button>
          <div><br /></div>
          <b-table
            id="import-sample-table"
            :columns="importSampleTableCols"
            :data="importSampleTableRows"
            :checkable="true"
            :header-checkable="false"
            :checked-rows.sync="importSampleTableCheckedRows"
          >
          </b-table>
          <div><br /></div>
        </section>
      </div>
    </section>
  </div>
</template>


<script>
import { mapState } from "vuex";

const _ = require("underscore");

export default {
  name: "BaseImportSample",
  components: {},
  props: {},
  computed: {
    ...mapState([
      "dataSources",
      "experimentSelected",
      "projectSelected",
      "url",
    ]),
    sampleToLink: {
      get() {
        return this.$store.state.sampleToLink;
      },
      set(value) {
        this.$store.commit("sampleToLink", value);
      },
    },
  },
  data: function () {
    return {
      // Communication
      be: null,
      namespace: null,
      roomSid: null,
      endpoints: ["importedSamples"],
      // variables for import modals
      importStartTime: null,
      importEndTime: null,
      importMinDatetime: null,
      importMaxDatetime: new Date(),
      // variables for sample import modal
      dataSourceNameSelected: null,
      dataSourceSelected: null,
      importedSamples: {},
      importSampleTableRows: [],
      importSampleTableCols: [],
      importSampleTableCheckedRows: [],
      importSampleTableDatetimeRange: {},
      //
    };
  },
  methods: {
    log: function (...args) {
      console.log("[" + this.name + "]", ...args);
    },
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
      this.importSampleTableDatetimeRange = fetchRequest;
    },
    filterDataSourcesProp(name, value) {
      return this.dataSources.filter((o) => {
        return o[name] === value;
      });
    },
    importSamples() {
      let toImport = this.importSampleTableCheckedRows[0];
      if (!toImport) {
        return;
      }
      // Preserve sample metadata
      // Set project and experiment to the selected ones
      toImport.project = this.projectSelected.title;
      toImport.experiment = this.experimentSelected.title;
      this.sampleToLink = toImport;
    },
    launchSampleImport() {
      // Request list of samples from FileService
      this.importSampleTableDatetimeRange = Math.random();
    },
  },
  watch: {
    dataSourceNameSelected: function (newValue, oldValue) {
      if (newValue === oldValue) return false;
      this.dataSourceSelected = this.filterDataSourcesProp("name", newValue)[0];
      this.log(this.dataSourceSelected);
    },
    dataSourceSelected: function (newValue, oldValue) {
      if (_.isEqual(newValue, oldValue)) {
        return false;
      }
      // TODO: this is to refresh the datetimepicker, but it doesn't re-render it: why?
      // this.importStartTime = null;
      // this.importEndTime = null;
      this.importSampleTableCols = [];
      this.importSampleTableRows = [];
      this.be.disconnect(this.namespace);
      this.namespace = this.be.connect(
        this.url + "/" + this.dataSourceSelected.name
      );
    },
    importSampleTableDatetimeRange: function (newValue, oldValue) {
      return this.be.exportOneWayBindingProp(
        "importSampleTableDatetimeRange",
        newValue,
        oldValue
      );
    },
    importSampleTableCheckedRows: function (newValue, oldValue) {
      if (_.isEqual(newValue, oldValue)) {
        return false;
      }
      var lastSelection = [...newValue].pop();
      // force single row selection
      if (this.importSampleTableCheckedRows.length > 1) {
        this.importSampleTableCheckedRows = [lastSelection];
      }
    },
    importedSamples: function (newData) {
      for (let i = 0; i < newData.cols.length; i++) {
        newData.cols[i]["searchable"] = true;
      }
      this.importSampleTableCols = newData.cols;
      this.importSampleTableRows = newData.rows;
    },
    "namespace.connected": function (newValue) {
      if (newValue === true) {
        // handlers for for external notifications:
        this.namespace.on("importedSamples", (value) =>
          this.be.importOneWayBindingProp("importedSamples", value.value)
        );

        this.roomSid = this.namespace.id;
        this.be.subscribe(this.endpoints, null);
      }
    },
  },
};
</script>

<style>
</style>