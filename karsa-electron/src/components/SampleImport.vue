<template>
  <div>
    <section class="sample-import">
        <div>

            <header class="modal-card-head">
              <p class="modal-card-title">
                Add samples to {{this.project_selected.title}}/{{this.experiment_selected.title}}
              </p>
            </header>

            <section class="modal-card-body">
                <b-field label="Start" custom-class="dark">
                <b-datetimepicker
                    v-model="import_start_time"
                    placeholder="Start datetime"
                    :timepicker="{ 'hour-format': '24' }"
                    :min-datetime="import_min_datetime"
                    :max-datetime="import_max_datetime"
                >
                </b-datetimepicker>
                </b-field>
                <b-field label="End" custom-class="dark">
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
                @click="fetchSamples()"
                is-dark
                :disabled="
                    import_start_time === null ||
                    import_end_time === null
                    ? true
                    : false
                "
                >
                Fetch samples
                </button>
                <div><br /></div>
                <b-table
                id="import-sample-table"
                :columns="import_sample_table_cols"
                :data="import_sample_table_rows"
                :checkable="true"
                :checked-rows.sync="import_sample_table_checked_rows"
                >
                </b-table>
                <div><br /></div>
            </section>
        </div>
    </section>
  </div>
</template>


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from "vuex";
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import "@mdi/font/css/materialdesignicons.min.css";
import { BECom } from "../karsalib.js";

Vue.use([Buefy]);

const _ = require("underscore");
// const fs = require("fs");

export default {
  name: "SampleImport",
  components: {
  },
  props: {},
  computed: {
    ...mapState([
          "data_sources",
          "experiment_selected",
          "project_selected",
          "url",
          ]),
    samples_to_link: {
      get() {
        return this.$store.state.samples_to_link;
      },
      set(value) {
        this.$store.commit("samples_to_link", value);
      },
    },
  },
  data: function () {
    return {
      // Communication
      be: null,
      namespace: null,
      room_sid: null,
      endpoints: ["importable_samples"],
      // variables for import modals
      import_start_time: null,
      import_end_time: null,
      import_min_datetime: null,
      import_max_datetime: new Date(),
      // variables for sample import modal
      importable_samples: {},
      import_sample_table_rows: [],
      import_sample_table_cols: [],
      import_sample_table_checked_rows: [],
      import_sample_table_datetime_range: {},
      // 
    };
  },
  created: function () {
    this.be = new BECom(this);
    this.namespace = this.be.connect(
      this.url + "/"
    );
  },
  mounted: function () {},
  methods: {
    log: function (...args) {
      console.log("[" + this.name + "]", ...args);
    },
    fetchSamples() {
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
      };
      this.import_sample_table_datetime_range = fetch_request;
    },
    filter_data_sources_prop(name, value) {
      return this.data_sources.filter((o) => {
        return o[name] === value;
      });
    },
    importSamples() {
      let to_import = this.import_sample_table_checked_rows;
      if (!to_import) {
        return
      }
      to_import.forEach(
        (row) => {
          row.project = this.project_selected.title;
          row.experiment = this.experiment_selected.title;
          if (!row.attributes || !row.attributes.length) {
            row.attributes = this.experiment_selected.sample_attributes_template;
          }
        }
      )
      this.samples_to_link = to_import;
    },
    launchSampleImport() {
      // Request list of samples from FileService
      this.import_sample_table_datetime_range = Math.random();
    },
  },
  watch: {
    import_sample_table_datetime_range: function (new_value, old_value) {
      return this.be.export_one_way_binding_prop(
        "import_sample_table_datetime_range",
        new_value,
        old_value,
      );
    },
    import_sample_table_checked_rows: function (new_value, old_value) {
      if (_.isEqual(new_value, old_value)) {
        return false;
      }
    },
    importable_samples: function (new_data) {
      for (let i = 0; i < new_data.cols.length; i++) {
        new_data.cols[i]["searchable"] = true;
      }
      this.import_sample_table_cols = new_data.cols;
      this.import_sample_table_rows = new_data.rows;
    },
    "namespace.connected": function (new_value) {
      if (new_value === true) {
        // handlers for for external notifications:
        this.namespace.on("importable_samples", (value) =>
          this.be.import_one_way_binding_prop("importable_samples", value.value)
        );

        this.room_sid = this.namespace.id;
        this.be.declare_endpoints(this.endpoints);
      }
    },
  },
};
</script>

<style>
</style>