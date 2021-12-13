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
    <!-- Isotope table modal -->
    <section class="isotope-table-modal">
      <b-modal
        :active.sync="is_modal_isotope_table_active"
        full-screen
        has-modal-card
        trap-focus
        :can-cancel="true"
        :destroy-on-hide="false"
        aria-role="dialog"
        aria-modal
      >
        <div class="modal-card">
          <header class="modal-card-head">
            <p class="modal-card-title">
            </p>
            <b-button
              icon-left="check"
              :type="isotope_table_show_only_checked ? 'is-primary' : 'is-dark'"
              @click="isotope_table_show_only_checked=!isotope_table_show_only_checked;"
            >
            </b-button>
            <!-- Column visibility dropdown -->
            <b-dropdown
              aria-role="menu"
              position="is-bottom-right"
              style="top: 0px"
              trap-focus
              multiple
              append-to-body
            >
              <b-button
                icon-left="menu"
                type="is-dark"
                slot="trigger">
              </b-button>
              <div>
                <div
                  v-for="(col, i) in isotope_table_cols"
                  :key="i"
                  class="control"
                >
                  <b-checkbox v-model="col.visible" size="is-small">
                    {{ col.label }}
                  </b-checkbox>
                </div>
              </div>
            </b-dropdown>
            <!-- Close button -->
            <b-button
              icon-left="close"
              type="is-dark"
              @click="is_modal_isotope_table_active = false"
            >
            </b-button>
          </header>

          <section class="modal-card-body">
            <!-- Sample table -->
            <b-table
              id="samples-datatable"
              :height="760"
              :data="isotope_table_rows"
              :sticky-header="true"
              striped
            >
              <!-- Columns -->
              <b-table-column
                v-for="(col, i) in isotope_table_cols"
                :key="i"
                :field="col.field"
                :label="col.label"
                searchable
                sortable
                :visible="col.visible === null ? true : col.visible"
                v-slot="props"
              >
                {{ props.row[col.field] }}
              </b-table-column>
              <!-- End of columns -->
            </b-table>
            <!-- End of sample table -->
          </section>
          <footer class="modal-card-foot">
            <b-button @click="exportIsotopeTable()"> Export CSV </b-button>
          </footer>
        </div>
      </b-modal>
    </section>
    <!-- End of isotope table modal -->
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
              <!-- Stats figure -->
              <div id="mz-calib-stats-chart">
              </div>
              <!-- End of stats figure -->
              <!-- Stats table -->
              <b-table
                :data="mz_calib_stats_table_rows"
                :columns="mz_calib_stats_table_cols"
              >
              </b-table>
              <!-- End of stats table -->
            </section>
            <footer class="modal-card-foot">
              <b-button
                @click="is_mz_calib_modal_active=false;">
                Cancel
              </b-button>
              <div style="text-align: right;">
                <b-button
                  :disabled="!samples_selected.length"
                  @click="calibrateSelectedSamples()">
                  Apply to selected samples
                </b-button>
              </div>
            </footer>
          </div>
        </div>
      </b-modal>
    </section>
    <!-- End of mass calibration modal -->
    <!-- End of modals -->

    <!-- Main content area -->
    <section class="tab-content">
        <b-button
          type="is-dark"
          @click="is_excel_clipboard_modal_active = true"
          style="margin-right: 1em"
          expanded
          >
          Import
        </b-button>
        <!-- Target compound table -->
        <b-table
            id="targets-datatable"
            :columns="target_table_cols"
            :data="target_table_rows"
			:key="target_table_key"
            :sticky-header="true"
            :selected.sync="target_table_selected_row"
            detailed
			custom-detailed-row
			:opened-detailed="target_table_detailed_rows"
			@details-open="(row, index) => setTargetTableDetails(row)"
            :show-detail-icon="true"
            detail-key="0"
        >
            <template slot="detail" slot-scope="props">
				<tr v-for="item in props.row.items" :key="item['target id']+'/'+item['ion id']">
					<td>{{item['ion composition']}}</td>
                </tr>
            </template>
        </b-table>
		<!-- End of target table -->
        <!-- Ionization mechanism input -->
        <b-field label="Ionization mechanism(s)" style="text-align: left">
            <b-input v-model="ionization_mechanism" lazy> </b-input>
        </b-field>
		<!-- Isotope table -->
		<!-- Buttons above table -->
		<div class="columns">
			<div class="column" style="text-align: left">
				<!-- Identification parameters -->
				<b-dropdown
					aria-role="menu"
					type="is-dark"
					position="is-top-right"
					style="top: 0px;"
					trap-focus
					append-to-body
					>
					<b-button
						icon-left="cogs"
						class="tag is-dark"
						slot="trigger"
						outlined
					>
					</b-button>
					<div style="background-color: #363636; width: 25vw;">
						<section style="padding: 0em 1em 0 1em;">
              <b-field label="peak intensity threshold">
								<b-slider
									type="is-primary"
									v-model="parameter_peak_intensity_threshold"
									:min="-5"
									:max="5"
									:tooltip="false"
									lazy
									indicator
									>
								</b-slider>
							</b-field>
							<b-field label="m/z tolerance [ppm]">
								<b-slider
									type="is-primary"
									v-model="parameter_mz_tolerance"
									:min="0"
									:max="100"
									:tooltip="false"
									lazy
									indicator
									>
								</b-slider>
							</b-field>
							<b-field label="isotope ratio tolerance [%]">
								<b-slider
									type="is-primary"
									v-model="parameter_iso_ratio_tolerance"
									:min="0"
									:max="100"
									:tooltip="false"
									lazy
									indicator
									>
								</b-slider>
							</b-field>
							<b-field label="isotope abundance threshold [%]">
								<b-slider
									type="is-primary"
									v-model="parameter_iso_abu_threshold"
									:min="0"
									:max="100"
									:step="1"
									:tooltip="false"
									lazy
									indicator
									>
								</b-slider>
							</b-field>
						</section>
					</div>
				</b-dropdown>
				<!-- End of identification parameters -->
			</div>
			<div class="column" style="text-align: right">
        <b-button
					icon-left="check"
					class="tag"
					:type="isotope_table_show_only_checked ? 'is-primary' : 'is-dark'"
					outlined
					@click="isotope_table_show_only_checked=!isotope_table_show_only_checked;"
				>
				</b-button>
				<b-button
					icon-left="fullscreen"
					class="tag is-dark"
					outlined
					@click="is_modal_isotope_table_active=true;"
				>
				</b-button>
				<!-- Isotope table column visibility control -->
				<b-dropdown
					aria-role="menu"
					type="is-dark"
					position="is-bottom-right"
					style="top: 0px"
					trap-focus
					multiple
					append-to-body
				>
					<b-button
					icon-left="menu"
					class="tag is-dark"
					slot="trigger"
					outlined
					>
					</b-button>
					<div>
						<div
							v-for="(col, i) in isotope_table_cols"
							:key="i"
							class="control"
						>
							<b-checkbox v-model="col.visible" size="is-small">
							{{ col.label }}
							</b-checkbox>
						</div>
					</div>
				</b-dropdown>
				<!-- End of isotope table column visibility control -->
			</div>
		</div>
		<!-- End of buttons above table -->
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
    <div style="text-align: right;">
      <b-field
        :label="'# identified peaks: ' + isotope_table_checked_rows.length">
      </b-field>
    </div>
    <!-- End of isotope table -->
		<section style="padding: 1em 0 0 0;">
			<b-button
				type="is-dark"
				@click="mzCalibrateButtonClicked"
        :disabled="isotope_table_checked_rows.length < 4"
				expanded>
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
var Plotly = require("plotly.js-dist");

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
      "samples_selected",
    ]),
	compute_target_ions: {
      get() {
        return this.$store.state.compute_target_ions;
      },
      set(value) {
        this.$store.commit("compute_target_ions", value);
      },
    },
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
    mz_calibration: {
      get() {
        return this.$store.state.mz_calibration;
      },
      set(value) {
        this.$store.commit("mz_calibration", value);
      },
    },
    parameter_peak_intensity_threshold: {
      get() {
        return this.$store.state.parameter_peak_intensity_threshold;
      },
      set(value) {
        this.$store.commit("parameter_peak_intensity_threshold", value);
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
    figure_config: {},
		namespace: null,
		// variables for excel clipboard import
		is_excel_clipboard_modal_active: false,
		excel_clipboard_text: "",
		excel_clipboard_table_cols: [],
		excel_clipboard_table_rows: [],
		// Peak table
    is_modal_isotope_table_active: false,
		isotope_table_all_rows: [],
		isotope_table_checked_rows: [],
		isotope_table_cols: [],
		isotope_table_key: Math.random(),
		isotope_table_rows: [],
		isotope_table_selected_row: {},
		isotope_table_show_only_checked: false,
		//
		// Mass calibration
		is_mz_calib_modal_active: false,
		mz_calib_stats_table_cols: [],
		mz_calib_stats_table_rows: [],
		//
		// Identification parameters
		parameter_mz_tolerance: 10,
		parameter_iso_ratio_tolerance: 10,
		parameter_iso_abu_threshold: 1,
		// 
		// Target table
		target_table_rows: [],
		target_table_cols: [],
		target_table_detailed_rows: [],
		target_table_key: Math.random(),
		target_table_selected_row: {},
		target_name_col: null,
		target_composition_col: null,
		targets_to_import: {},
		//
		room_sid: null,
		endpoints: [],
    };
  },
  created: function () {
	this.be = new BECom(this);
  var self = this;
  // Read figure config
  if (fs.existsSync('configs/figure_config.json')) {
      const figure_configs = JSON.parse(fs.readFileSync('configs/figure_config.json', 'utf8'));
      self.figure_config = figure_configs.common_config;
  }
  },
  mounted: function () {
  },
  methods: {
    calibrateSelectedSamples() {
      this.be.export_one_way_binding_prop(
          "mz_calibrate_samples",
          {
            filenames: this.samples_selected,
            fit: this.mz_calibration.fit
          },
          null,
          this.room_sid
        );
      this.is_mz_calib_modal_active = false;
    },
    drawMzCalibStatsFigure() {
      let mz = this.mz_calibration.stats['mz'];
      let pre_calib_dmz = this.mz_calibration.stats['pre_dmz'];
      let post_calib_dmz = this.mz_calibration.stats['post_dmz'];

      let ddmz = new Float32Array(mz.length);
      for (var i=ddmz.length; i-->0;) {
        ddmz[i] = Math.abs(pre_calib_dmz[i])-Math.abs(post_calib_dmz[i]);
      }
      let pre_trace = {x: mz,
                      y: pre_calib_dmz,
                      type: 'bar',
                      name: "Pre"
                      };
      let post_trace = {x: mz,
                        y: post_calib_dmz,
                        type: 'bar',
                        name: "Post"
                        };
      let d_trace = {x: mz,
                    y: ddmz,
                    type: 'line',
                    name: "Diff"
                    };
      
      Plotly.react(
        "mz-calib-stats-chart",
        [pre_trace, post_trace, d_trace],
        {},
        this.figure_config
      );
    },
    exportIsotopeTable() {
      return;
      // const fields = this.isotope_table_cols.map((a) => {
      //   return { label: a.label, value: a.field };
      // });
      // const opts = {
      //   fields: fields,
      // };

      // try {
      //   // Parse CSV
      //   const parser = new Parser(opts);
      //   const csv = parser.parse(this.isotope_table_rows);
      //   const csv_filename =
      //     this.project_selected.title +
      //     "_" +
      //     this.experiment_selected.title +
      //     ".csv";
      //   // Make blob
      //   const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      //   // Create a temporary download link for the blob and "click" it
      //   var link = document.createElement("a");
      //   var url = URL.createObjectURL(blob);
      //   link.setAttribute("href", url);
      //   link.setAttribute("download", csv_filename);
      //   link.style.visibility = "hidden";
      //   document.body.appendChild(link);
      //   link.click();
      //   // Remove the link
      //   document.body.removeChild(link);
      // } catch (err) {
      //   console.error(err);
      // }
    },
    fitMzCalibFunction() {
      let peak_tofs = this.isotope_table_checked_rows.map(
        (row) => row["peak tof"]
      );
      let peak_mzs = this.isotope_table_checked_rows.map((row) => row["peak mz"]);
      let exact_mzs = this.isotope_table_checked_rows.map((row) => row["mz"]);
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
		this.targets_to_import = {
			cols: this.excel_clipboard_table_cols,
			rows: this.excel_clipboard_table_rows,
		};
		this.is_excel_clipboard_modal_active = false;
    },
    mzCalibrateButtonClicked() {
      this.fitMzCalibFunction();
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
						searchable: true
					});
					// Save key fields
					switch (label.toLowerCase()) {
						case "target name": {
							this.target_name_col = j;
							break;
						}
						case "target composition": {
							this.target_composition_col = j;
							break;
						}
					}
				} else {
					// Construct row
					row[j] = clip_rows[i][j];
				}
			}
			// Add row
			if (!_.isEmpty(row) && Object.keys(row).length == cols.length) {
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
                case "target composition": {
                this.target_composition_col = j;
                break;
                }
            }
        }
        this.target_table_rows = target_table_data.rows;
    },
    requestPeakIdentification() {
		let peaks_exist = this.peak_data.mz && this.peak_data.mz.length;
		let targets_exist = this.target_ions.length > 0;
		if (!peaks_exist || !targets_exist) {
			return;
		}
		let parameters = {
					'mz_tolerance': this.parameter_mz_tolerance,
					'iso_abu_tolerance': this.parameter_iso_ratio_tolerance,
					'min_iso_abu': this.parameter_iso_abu_threshold
					};
		this.identify_peaks = {
            peaks: this.peak_data,
            target_ions: this.target_ions,
			parameters: parameters
            };
    },
    requestTargetIons() {
		// Collect compound formula from each row
		let compounds = [];
		for (const j in this.target_table_rows) {
			const row = this.target_table_rows[j];
			compounds.push(row[this.target_composition_col]);
		}
		this.compute_target_ions = {
			ionization_mechanism: this.ionization_mechanism,
			compounds: compounds,
		};
    },
    rightClickPeakTableRow(row) {
		console.log(row);
    },
    setTargetTableDetails(row) {
		this.target_table_detailed_rows = [row['0']];
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
        this.isotope_table_all_rows = rows;
    },
    updateMzCalibStatsTable() {
      this.mz_calib_stats_table_cols = [
        { field: "mz", label: "m/z" },
        { field: "pre_dmz", label: "pre m/z error" },
        { field: "post_dmz", label: "post m/z error" }
      ];
      this.mz_calib_stats_table_rows = [];
      for (let i in this.mz_calibration.stats.mz) {
        let row = {};
        for (let j in this.mz_calib_stats_table_cols) {
          let key = this.mz_calib_stats_table_cols[j].field;
          let value = this.mz_calibration.stats[key][i]; 
          row[key] = Math.round((value + Number.EPSILON) * 1000) / 1000;
        }
        this.mz_calib_stats_table_rows.push(row);
      }
      console.log("this.mz_calib_stats_table_rows: ", this.mz_calib_stats_table_rows);
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
      this.updateIsotopeTableData(this.target_ions);
      this.isotope_table_checked_rows = [];
      let identified_targets = new Set();
      let identified_ions = new Set();
      let first_round = true;
      for (let row_i in new_value) {
        let row = new_value[row_i];
        // Check if columns need to be extended
        if (first_round) {
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
                  'label': field,
                  'visible': true
                  });
            }
          }
          this.isotope_table_cols = [
            ...this.isotope_table_cols,
            ...cols_to_add
            ];
          first_round = false;
        }
        // 
        
        for (let key in row) {
          let value = row[key];
          // Fix precision of numeric fields to 4 decimals
          if (Number(value) && value != 0) {
            value = Math.round((value + Number.EPSILON) * 10000) / 10000;
            row[key] = value;
          }
        }
        this.isotope_table_all_rows[row_i] = row;
        // Add checkmark for identified isotopes
        if (row["peak mz"] > -1) {
          this.isotope_table_checked_rows.push(row);
          identified_targets.add(row['target id']);
          identified_ions.add(row['ion id']);
        }
      }
      // Redraw table
      this.isotope_table_key = Math.random();
      // Add identification indicator to target table
      if (this.target_table_cols.length == 2) {
        this.target_table_cols.push({
                      'field': "2",
                      'label': "",
                      'searchable': true
                      });
      }
      for (let row_i in this.target_table_rows) {
        this.target_table_rows[row_i]['2'] = "0";
      }
      for (let target_index of identified_targets) {
        this.target_table_rows[target_index]['2'] = "1";
      }
      this.target_table_key = Math.random();
    },
    identify_peaks: function (new_value, old_value) {
		if (_.isEqual(new_value, old_value)) {
			return;
		}
		this.be.export_one_way_binding_prop(
			"identify_peaks",
			{...new_value,
				room: this.room_sid,
				uid: Math.random()
				},
			old_value,
			this.room_sid
		);
    },
    isotope_table_all_rows: function() {
		if (this.isotope_table_show_only_checked) {
			this.isotope_table_rows = this.isotope_table_checked_rows;
			return;
		}
		this.isotope_table_rows = this.isotope_table_all_rows;
    },
    mz_calib_compound_table_checked_rows: function () {
		this.updateMzCalibPeaks();
    },
    mz_calibration: function() {
      this.updateMzCalibStatsTable();
      this.drawMzCalibStatsFigure();
    },
    parameter_iso_abu_threshold: function() {
		this.requestPeakIdentification();
    },
    parameter_iso_ratio_tolerance: function() {
		this.requestPeakIdentification();
    },
    parameter_mz_tolerance: function() {
		this.requestPeakIdentification();
    },
    peak_data: function () {
        this.requestPeakIdentification();
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
    isotope_table_show_only_checked: function(new_value) {
		if (new_value) {
			this.isotope_table_rows = this.isotope_table_checked_rows;
			return;
		}
		this.isotope_table_rows = this.isotope_table_all_rows;
    },
    target_ions: function (new_value) {
		// Clear target ions from target table row details
		for (let i in this.target_table_rows) {
			this.target_table_rows[i].items = [];
		}
		// Collect ion compositions per target for row details
		let prev_ion_id = -1;
		for (let i in new_value) {
			let isotope = new_value[i];
			if (isotope['ion id'] == prev_ion_id) {
				continue
			}
			const target_index = isotope['target id'];
			this.target_table_rows[target_index].items.push(isotope);
			prev_ion_id = isotope['ion id'];
		}
		// 
		this.updateIsotopeTableData(new_value);
		this.requestPeakIdentification();
    },
    target_table_rows: function() {
        this.requestTargetIons();
    },
    target_table_selected_row: function(new_value) {
        // Filter isotope table by selected target
        let target_id = this.target_table_rows.indexOf(new_value);
        this.$set(this.$refs.isotope_table.filters, 'target id', String(target_id));
    },
    targets_to_import: function (new_data, old_data) {
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
				this.be.import_one_way_binding_prop("target_ions", value.value)
			);
			this.namespace.on("mz_calibration", (value) =>
				this.be.import_one_way_binding_prop("mz_calibration",
            {
            'fit': value.value.fit,
            'stats': {
							mz: new Float32Array(value.value.stats.mz),
							pre_dmz: new Float32Array(value.value.stats.pre_dmz),
							post_dmz: new Float32Array(value.value.stats.post_dmz)
              }
            })
			);
			this.room_sid = this.root_namespace.id;
			this.be.subscribe(this.endpoints, this.room_sid);

			this.readTargetsFromFile();
		}
    },
  },
};
</script>