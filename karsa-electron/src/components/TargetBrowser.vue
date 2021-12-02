<template>
  <div>
    <!-- Modals -->
    <!-- Modal for Excel import -->
    <section class="excel-import-modal">
      <b-modal
        :active.sync="is_excel_clipboard_modal_active"
        has-modal-card
        trap-focus
        :can-cancel="true"
        aria-role="dialog"
        aria-modal
      >
        <div class="columns">
          <div class="modal-card" style="width: 500px; height: 700px">
            <header class="modal-card-head">
              <p class="modal-card-title">Import from Excel clipboard</p>
            </header>
            <section class="modal-card-body" style="text-align: center">
              <b-field label="Paste clipboard">
                <b-input v-model="excel_clipboard_text" type="textarea">
                </b-input>
              </b-field>
              <div><br /></div>
              <b-table
                id="excel-clipboard-table"
                :columns="excel_clipboard_table_cols"
                :data="excel_clipboard_table_rows"
              >
              </b-table>
              <div><br /></div>
            </section>
            <footer class="modal-card-foot">
              <b-button @click="importExcelTargets()"> Import </b-button>
              <b-button @click="is_excel_clipboard_modal_active = false">
                Cancel
              </b-button>
            </footer>
          </div>
        </div>
      </b-modal>
    </section>
    <!-- End of Excel import modal -->
    <!-- Mass calibration modal -->
    <section class="mzcalib-modal">
      <b-modal
        :active.sync="is_mz_calib_modal_active"
        has-modal-card
        trap-focus
        :can-cancel="true"
        aria-role="dialog"
        aria-modal
      >
        <div class="columns">
          <div class="modal-card" style="width: 500px; height: 700px">
            <header class="modal-card-head">
              <p class="modal-card-title">Mass calibration</p>
            </header>
            <section class="modal-card-body" style="text-align: center">
              <b-table
                id="mz-calib-compound-table"
                style="max-height: 400px"
                :columns="mz_calib_compound_table_cols"
                :data="mz_calib_compound_table_rows"
                :sticky-header="true"
                :selected.sync="mz_calib_compound_table_selected_row"
                checkable
                :checked-rows.sync="mz_calib_compound_table_checked_rows"
                focusable
                sortable
              >
              </b-table>
              <div><br /></div>
              <b-table
                id="mz-calib-peak-table"
                style="max-height: 400px"
                :columns="mz_calib_isotope_table_cols"
                :data="mz_calib_isotope_table_rows"
                :sticky-header="true"
                focusable
              >
              </b-table>
              <div><br /></div>
              <b-button @click="fitMzCalibFunction"> Fit </b-button>
            </section>
            <footer class="modal-card-foot"></footer>
          </div>
        </div>
      </b-modal>
    </section>
    <!-- End of mass calibration modal -->
    <!-- End of modals -->

    <!-- Main content area -->
    <section class="tab-content">
        <!-- Target tables -->
        <b-table
            id="targets-datatable"
            :columns="target_table_cols"
            :data="target_table_rows"
            :sticky-header="true"
            :selected.sync="target_table_selected_row"
            detailed
            :show-detail-icon="true"
            detail-key="0"
        >
            <template #detail="props">
            {{ props.row }}
            </template>
        </b-table>
        <!-- Ionization mechanism input -->
        <b-field label="Ionization mechanism" style="text-align: left">
            <b-input v-model="ionization_mechanism" lazy> </b-input>
        </b-field>
        <b-table
            @contextmenu="rightClickPeakTableRow"
            id="isotope-datatable"
            ref="isotope_table"
            style="margin-top: 1em"
            :columns="isotope_table_cols"
            :data="isotope_table_rows"
            :key="isotope_table_key"
            :sticky-header="true"
            :selected.sync="isotope_table_selected_row"
            :header-checkable="false"
            checkable
            :checked-rows.sync="isotope_table_checked_rows"
            :is-row-checkable="(row) => row == isotope_table_selected_row"
            focusable
            sortable
        >
        </b-table>
        <!-- End of target tables -->
        <section style="text-align: right; margin-top: 1em">
            <b-button
            type="is-dark"
            @click="is_excel_clipboard_modal_active = true"
            style="margin-right: 1em"
            >
            Import targets
            </b-button>
            <b-button type="is-dark" @click="mzCalibrateButtonClicked">
            Calibrate m/z
            </b-button>
        </section>
    </section>
    <!-- End of main content area -->
  </div>
</template>


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from "vuex";
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import "@mdi/font/css/materialdesignicons.min.css";
import { BECom } from "../karsalib";

Vue.use([Buefy]);

var _ = require("underscore");
var fs = require("fs");

export default {
  name: "TargetBrowser",
  components: {},
  props: {},
  computed: {
    ...mapState([
      "figure_double_click",
      "figure_ranges",
      "peak_data",
      "root_namespace",
      "sample_selected",
    ]),
    identified_ions: {
      get() {
        return this.$store.state.identified_ions;
      },
      set(value) {
        this.$store.commit("identified_ions", value);
      },
    },
    identify_peaks: {
      get() {
        return this.$store.state.identify_peaks;
      },
      set(value) {
        this.$store.commit("identify_peaks", value);
      },
    },
    ionization_mechanism: {
      get() {
        return this.$store.state.ionization_mechanism;
      },
      set(value) {
        this.$store.commit("ionization_mechanism", value);
      },
    },
    compute_target_ions: {
      get() {
        return this.$store.state.compute_target_ions;
      },
      set(value) {
        this.$store.commit("compute_target_ions", value);
      },
    },
    target_ions: {
      get() {
        return this.$store.state.target_ions;
      },
      set(value) {
        this.$store.commit("target_ions", value);
      },
    },
    target_to_display: {
      get() {
        return this.$store.state.target_to_display;
      },
      set(value) {
        this.$store.commit("target_to_display", value);
      },
    },
  },
  data: function () {
    return {
      be: null,
      namespace: null,
      // variables for excel clipboard import
      is_excel_clipboard_modal_active: false,
      excel_clipboard_text: "",
      excel_clipboard_table_cols: [],
      excel_clipboard_table_rows: [],
      // Mass calibration
      is_mz_calib_modal_active: false,
      mz_calib_compound_table_checked_rows: [],
      mz_calib_compound_table_cols: [],
      mz_calib_compound_table_rows: [],
      mz_calib_compound_table_selected_row: {},
      mz_calib_isotope_table_cols: [],
      mz_calib_isotope_table_rows: [],
      //
      // Peak table
      isotope_table_checked_rows: [],
      isotope_table_cols: [],
      isotope_table_key: 0,
      isotope_table_rows: [],
      isotope_table_selected_row: {},
      //
      // Target table
      targets: [],
      target_table_rows: [],
      target_table_cols: [],
      target_table_selected_row: {},
      target_name_col: null,
      target_compound_col: null,
      //
      room_sid: null,
      endpoints: [],
    };
  },
  created: function () {
    this.be = new BECom(this);
  },
  mounted: function () {
  },
  methods: {
    fitMzCalibFunction() {
      let peak_tofs = this.mz_calib_isotope_table_rows.map(
        (row) => row["peak tof"]
      );
      let peak_mzs = this.mz_calib_isotope_table_rows.map((row) => row["peak mz"]);
      let exact_mzs = this.mz_calib_isotope_table_rows.map((row) => row["mz"]);
      let mz_calib_data = {
        peak_tofs: peak_tofs,
        peak_mzs: peak_mzs,
        exact_mzs: exact_mzs,
      };
      this.be.export_one_way_binding_prop(
        "fit_mz_calib_function",
        { ...mz_calib_data, room: this.room_sid, uid: Math.random() },
        null,
        this.room_sid
      );
    },
    importExcelTargets() {
      this.targets = {
        cols: this.excel_clipboard_table_cols,
        rows: this.excel_clipboard_table_rows,
      };
      this.is_excel_clipboard_modal_active = false;
    },
    mzCalibrateButtonClicked() {
      // Set up compound table
      this.mz_calib_compound_table_cols = this.isotope_table_cols;
      this.mz_calib_compound_table_rows = this.isotope_table_rows.filter(function (
        row
      ) {
        return row["peak id"] != -1;
      });
      this.mz_calib_compound_table_checked_rows =
        this.mz_calib_compound_table_rows;
      this.updateMzCalibPeaks();
      this.is_mz_calib_modal_active = true;
    },
    parseExcelClipboard: function (clipboard_text) {
      // Split full text to rows
      let clip_rows = clipboard_text.split(String.fromCharCode(10));
      // Split each row to columns
      for (let i = 0; i < clip_rows.length; i++) {
        clip_rows[i] = clip_rows[i].split(String.fromCharCode(9));
      }
      let cols = [];
      let rows = [];
      // Parse into b-table format
      // Loop through rows
      for (let i = 0; i < clip_rows.length; i++) {
        let row = {};
        // Loop through row cells
        for (let j = 0; j < clip_rows[i].length; j++) {
          if (i == 0) {
            // New column
            let field = j.toString();
            let label = clip_rows[i][j];
            cols.push({
              field: field,
              label: label,
            });
            // Save key fields
            switch (label.toLowerCase()) {
              case "target name": {
                this.target_name_col = j;
                break;
              }
              case "target compound": {
                this.target_compound_col = j;
                break;
              }
            }
          } else {
            // Construct row
            row[j] = clip_rows[i][j];
          }
        }
        // Add row
        if (!_.isEmpty(row)) {
          if (i > 0 || !this.excel_clipboard_use_header) {
            rows.push(row);
          }
        }
      }
      this.excel_clipboard_table_cols = cols;
      this.excel_clipboard_table_rows = rows;
      this.excel_clipboard_text = "";
    },
    readTargetsFromFile() {
        let target_table_data = JSON.parse(
            fs.readFileSync("configs/target_list.json")
        );
        this.ionization_mechanism = target_table_data.ionization_mechanism;
        this.target_table_cols = target_table_data.cols;
        for (let j in this.target_table_cols) {
            let label = this.target_table_cols[j].label;
            // Save key fields
            switch (label.toLowerCase()) {
                case "target name": {
                this.target_name_col = j;
                break;
                }
                case "target compound": {
                this.target_compound_col = j;
                break;
                }
            }
        }
        this.target_table_rows = target_table_data.rows;
    },
    requestTargetIons() {
      // Collect compound formula from each row
      let compounds = [];
      for (const j in this.target_table_rows) {
        const row = this.target_table_rows[j];
        compounds.push(row[this.target_compound_col]);
      }
      this.compute_target_ions = {
        ionization_mechanism: this.ionization_mechanism,
        compounds: compounds,
      };
    },
    rightClickPeakTableRow(row) {
      console.log(row);
    },
    updateIsotopeTableData(data) {
        // Format data to isotope table
        let rows = [];
        let cols = [];
        for (let i in data) {
            let isotope = data[i];
            let row = {};
            // Unpack attributes
            let keys = Object.keys(isotope);
            for (let k in keys) {
                let key = keys[k];
                let value = isotope[key];
                if (Number(value) && value != 0) {
                    // Fix precision to 4 decimals
                    value = Math.round((value + Number.EPSILON) * 10000) / 10000;
                }
                if (rows.length == 0) {
                let col = {
                    field: key.toLowerCase(),
                    label: key,
                };
                col.searchable = true;
                if (Number(value) != null) {
                    col.sortable = true;
                }
                col.visible = true;
                cols.push(col);
                }
                row[key.toLowerCase()] = value;
            }
            rows.push(row);
        }
        this.isotope_table_cols = cols;
        this.isotope_table_rows = rows;
    },
    updateMzCalibPeaks() {
      this.mz_calib_isotope_table_cols = [
        { field: "ion composition", label: "Ion composition" },
        { field: "mz", label: "Ion m/z" },
        // {'field': 'peak id', 'label': "Peak ID"},
        { field: "peak mz", label: "Peak m/z" },
        { field: "peak tof", label: "Peak TOF", visible: false },
      ];
      this.mz_calib_isotope_table_rows = [];
      for (let i in this.mz_calib_compound_table_rows) {
        const compound_row = this.mz_calib_compound_table_rows[i];
        if (
          this.mz_calib_compound_table_checked_rows.indexOf(compound_row) == -1
        ) {
          continue;
        }
        let row = {};
        for (let j in this.mz_calib_isotope_table_cols) {
          let key = this.mz_calib_isotope_table_cols[j].field;
          row[key] = compound_row[key];
        }
        this.mz_calib_isotope_table_rows.push(row);
      }
    },
    writeTargetsToFile() {
      let target_table_data = {
        cols: this.target_table_cols,
        rows: this.target_table_rows,
        ionization_mechanism: this.ionization_mechanism
      };
      fs.writeFileSync(
        "configs/target_list.json",
        JSON.stringify(target_table_data, null, 3)
      );
    },
  },
  watch: {
    compute_target_ions: function (new_value, old_value) {
      if (_.isEqual(new_value, old_value)) {
        return;
      }
      this.be.export_one_way_binding_prop(
        "compute_target_ions",
        {...new_value,
        room: this.room_sid,
        uid: Math.random()
        },
        old_value,
        this.room_sid
      );
    },
    excel_clipboard_text: function (new_value, old_value) {
      if (new_value === old_value || !new_value.length) {
        return;
      }
      this.parseExcelClipboard(new_value);
    },
    excel_clipboard_use_header: function (new_value) {
      if (new_value) {
        let header = this.excel_clipboard_table_rows.slice(0, 1)[0];
        for (let i = 0; i < this.excel_clipboard_table_cols.length; i++) {
          let label = header[i];
          this.excel_clipboard_table_cols[i]["label"] = label.slice(0);
        }
        this.excel_clipboard_table_rows =
          this.excel_clipboard_table_rows.slice(1);
      }
    },
    figure_double_click: function() {
        this.target_to_display = null;
        this.isotope_table_selected_row = null;
    },
    identified_ions: function (new_value) {
      let first_round = true;
      for (let row_i in new_value) {
          let row = new_value[row_i];
          if (first_round) {
              // Check if columns need to be extended
              let cols_to_add = [];
              for (let field in row) {
                  let field_exists = false;
                  for (let col_i in this.isotope_table_cols) {
                    let col = this.isotope_table_cols[col_i];
                      if (col.field == field) {
                          field_exists = true;
                          break;
                      }
                  }
                  if (!field_exists) {
                    cols_to_add.push({
                        'field': field,
                        'label': field
                        });
                  }
              }
              this.isotope_table_cols = [
                  ...this.isotope_table_cols,
                  ...cols_to_add
                  ];
              first_round = false;
          }
          // Fix precision of numeric fields to 4 decimals
          for (let key in row) {
            let value = row[key];
            if (Number(value) && value != 0) {
                value = Math.round((value + Number.EPSILON) * 10000) / 10000;
                row[key] = value;
            }
          }
          this.isotope_table_rows[row_i] = row;
          // Add checkmark for identified isotopes
          if (row["peak mz"] > -1) {
            this.isotope_table_checked_rows.push(row);
          }
      }
      // Redraw table
      this.isotope_table_key = Math.random();
    },
    identify_peaks: function (new_value, old_value) {
      let peaks_exist = new_value.peaks.mz;
      let targets_exist = new_value.target_ions.length > 0;
      if (_.isEqual(new_value, old_value) || !peaks_exist || !targets_exist) {
        return;
      }

      this.be.export_one_way_binding_prop(
        "identify_peaks",
        { ...new_value, room: this.room_sid, uid: Math.random() },
        old_value,
        this.room_sid
      );
    },
    mz_calib_compound_table_checked_rows: function () {
      this.updateMzCalibPeaks();
    },
    peak_data: function (new_value) {
        this.identify_peaks = {
            peaks: new_value,
            target_ions: this.target_ions,
            };
    },
    isotope_table_checked_rows: function (new_value) {
      console.log(new_value);
    },
    isotope_table_selected_row: function (new_value, old_value) {
      if (_.isEqual(new_value, old_value)) {
        return false;
      }
      if (new_value != null) {
        let mz = new_value["mz"];
        if (mz) {
          this.target_to_display = mz;
          return;
        }
        // }
      } else {
        this.target_to_display = null;
      }
    },
    target_ions: function (new_value) {
        this.updateIsotopeTableData(new_value);
        this.identify_peaks = {
            peaks: this.peak_data,
            target_ions: new_value,
        };
    },
    target_table_rows: function() {
        this.requestTargetIons();
    },
    target_table_selected_row: function(new_value) {
        // Filter isotope table by selected target
        let target_id = this.target_table_rows.indexOf(new_value);
        this.$set(this.$refs.isotope_table.filters, 'target id', String(target_id));
    },
    targets: function (new_data, old_data) {
      if (_.isEqual(new_data, old_data)) {
        return false;
      }
      this.target_table_cols = new_data.cols;
      this.target_table_rows = new_data.rows;
      this.writeTargetsToFile();
    },
    ionization_mechanism: function (new_data, old_data) {
      if (_.isEqual(new_data, old_data)) {
        return false;
      }
      this.writeTargetsToFile();
      this.requestTargetIons();
    },
    "root_namespace.connected": function (new_value) {
      if (new_value === true) {
        this.namespace = this.root_namespace;
        // handlers for for external notifications:
        this.namespace.on("identified_ions", (value) =>
          this.be.import_one_way_binding_prop("identified_ions", value.value)
        );
        this.namespace.on("target_ions", (value) =>
          this.be.import_one_way_binding_prop(
            "target_ions",
            value.value
          )
        );
        this.namespace.on("targets", (value) =>
          this.be.import_one_way_binding_prop("targets", value.value)
        );
        this.room_sid = this.root_namespace.id;
        this.be.subscribe(this.endpoints, this.room_sid);

        this.readTargetsFromFile();
      }
    },
  },
};
</script>