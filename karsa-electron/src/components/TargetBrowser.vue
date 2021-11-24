<template>
    <div>
<!-- Modals -->
    <!-- Modal for Excel import -->
    <section class="excel-import-modal">
        <b-modal :active.sync="is_excel_clipboard_modal_active"
            has-modal-card
            trap-focus
            :can-cancel="true"
            aria-role="dialog"
            aria-modal>
            <div class="columns">
                <div class="modal-card" style="width: 500px; height: 700px">
                    <header class="modal-card-head">
                        <p class="modal-card-title">Import from Excel clipboard</p>
                    </header>
                    <section class="modal-card-body" style="text-align: center">
                        <b-field label="Paste clipboard">
                            <b-input
                                v-model="excel_clipboard_text"
                                type="textarea">
                            </b-input>
                        </b-field>
                        <b-field label="Use first row as a header" >
                            <b-checkbox v-model="excel_clipboard_use_header" size="is-medium">
                            </b-checkbox>
                        </b-field>
                        <div><br></div>
                        <b-table 
                            id="excel-clipboard-table"
                            :columns="excel_clipboard_table_cols"
                            :data="excel_clipboard_table_rows">
                        </b-table>
                        <div><br></div>
                    </section>
                    <footer class="modal-card-foot">
                        <button
                            class="button"
                            type="button"
                            @click="importExcelTargets()"
                            is-dark>
                            Import
                        </button>
                        <button
                            class="button"
                            type="button"
                            is-dark
                            @click="is_excel_clipboard_modal_active=false">
                            Cancel
                        </button>
                    </footer>
                </div>
            </div>
        </b-modal>
    </section>
    <!-- End of Excel import modal -->
<!-- End of modals -->

<!-- Main content area -->
    <section>
        <!-- Targetlist datatable collapable -->
        <section>
            <b-collapse
                :open="false"
                class="card"
                animation="slide"
                aria-id="contentIdForA11y3">
                <div
                    slot="trigger" 
                    slot-scope="props"
                    class="card-header"
                    role="button"
                    aria-controls="contentIdForA11y3">
                    <p class="card-header-title">
                        Targets
                    </p>
                    <a class="card-header-icon">
                    <b-icon
                        :icon="props.open ? 'menu-down' : 'menu-up'">
                    </b-icon>
                    </a>
                </div>
                <div class="card-content">
                    <div class="content">
                        <div class="left-panel-collapsable">
                            <b-button
                                type="is-dark"
                                @click="is_excel_clipboard_modal_active=true"
                                outlined
                                inverted
                                size="is-small">
                                Import targets
                            </b-button>
                            <div><br></div>
                            <b-table 
                                id="targets-datatable"
                                style="max-height:400px"
                                :columns="target_table_cols"
                                :data="target_table_rows" 
                                :sticky-header="true"
                                :selected.sync="target_table_selected_row" 
                                focusable
                                sortable>
                            </b-table>
                            <div><br></div>
                            <b-table 
                                id="peaks-datatable"
                                style="max-height:400px"
                                :columns="peak_table_cols"
                                :data="peak_table_rows" 
                                :sticky-header="true"
                                :selected.sync="peak_table_selected_row"
                                :header-checkable="false"
                                checkable
                                :checked-rows.sync="peak_table_checked_rows"
                                :is-row-checkable="(row) => row == peak_table_selected_row"
                                focusable
                                sortable>
                            </b-table>
                        </div>
                    </div>
                </div>
            </b-collapse>
        </section>
    </section>
<!-- End of main content area -->
    </div>
</template>


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from 'vuex'
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';
import { BECom } from '../karsalib';

Vue.use([Buefy]);

var _ = require('underscore');
var fs = require('fs');

export default {
    name: "TargetBrowser",
    components: {
    },
    props: {
    },
    computed: {
        ...mapState([
            'figure_double_click',
            'peak_data',
            'root_namespace',
            'sample_selected',
        ]),
        identified_ions: {
            get() {
                return this.$store.state.identified_ions;
            },
            set(value) {
                this.$store.commit('identified_ions', value);
            }
        },
        identify_peaks: {
            get() {
                return this.$store.state.identify_peaks;
            },
            set(value) {
                this.$store.commit('identify_peaks', value);
            }
        },
        integrate_target_ions: {
            get() {
                return this.$store.state.integrate_target_ions;
            },
            set(value) {
                this.$store.commit('integrate_target_ions', value);
            }
        },
        target_ion_intensities: {
            get() {
                return this.$store.state.target_ion_intensities;
            },
            set(value) {
                this.$store.commit('target_ion_intensities', value);
            }
        },
        target_to_display: {
            get() {
                return this.$store.state.target_to_display;
            },
            set(value) {
                this.$store.commit('target_to_display', value);
            }
        },
    },
    data: function() {
        return {
            be: null,
            namespace: null,
            // variables for excel clipboard import
            is_excel_clipboard_modal_active: false,
            excel_clipboard_text: "",
            excel_clipboard_table_cols: [],
            excel_clipboard_table_rows: [],
            excel_clipboard_use_header: false,
            // Peak table
            peak_table_checked_rows: [],
            peak_table_cols: [],
            peak_table_rows: [],
            peak_table_selected_row: {},
            // 
            // Target table
            targets: [],
            target_table_rows: [],
            target_table_cols: [],
            target_table_selected_row: {},
            //
            room_sid: null,
            endpoints: [
                'targets',
            ]
        }
    },
    created: function() {
        this.be = new BECom(this);
    },
    mounted: function() {
        this.readTargetsFromFile();
    },
    methods: {
        requestTargetIntensities() {
            // Find m/z column, assuming the first numeric column is m/z
            let mz_field = null;
            for (const i in this.target_table_cols) {
                mz_field = this.target_table_cols[i].field;
                let mz = Number( this.target_table_rows[0][mz_field] );
                if (mz) {
                    break
                }
            }
            if (!mz_field) {
                console.log("No mz field found from target table columns");
                return
            }
            // Collect m/z value of each row
            let mzs = [];
            for (const j in this.target_table_rows) {
                const row = this.target_table_rows[j];
                mzs.push(Number(row[mz_field]));
            }
            this.integrate_target_ions = {'filename': this.sample_selected.filename,
                                          'mz': mzs,
                                          't_range': null,
                                          };
        },
        importExcelTargets() {
            this.targets = {'cols': this.excel_clipboard_table_cols,
                            'rows': this.excel_clipboard_table_rows
                            };
            this.is_excel_clipboard_modal_active = false;
        },
        parseExcelClipboard: function(clipboard_text) {
            // Split full text to rows
            let clip_rows = clipboard_text.split(String.fromCharCode(10));
            // Split each row to columns
            for (let i=0; i < clip_rows.length; i++) {
                clip_rows[i] = clip_rows[i].split(String.fromCharCode(9));
            }
            let cols = [];
            let rows = [];
            // Parse into b-table format
            // Loop through rows
            for (let i=0; i < clip_rows.length; i++) {
                let row = {};
                // Loop through row cells
                for (let j=0; j < clip_rows[i].length; j++) {
                    if (i==0) {
                        // New column
                        let field = j.toString();
                        let label = j.toString();
                        if (this.excel_clipboard_use_header) {
                            // Use first row as a header
                            label = clip_rows[i][j];
                        }
                        cols.push({
                            'field': field, 
                            'label': label
                            });
                    }
                    // Construct row
                    row[j] = clip_rows[i][j];
                }
                // Add row
                if (!_.isEmpty(row)) {
                    if (i>0 || !this.excel_clipboard_use_header) {
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
                                        fs.readFileSync('configs/target_list.json')
                                        );
            this.target_table_cols = target_table_data.cols;
            this.target_table_rows = target_table_data.rows;
        },
        writeTargetsToFile() {
            let target_table_data = {"cols": this.target_table_cols,
                                     "rows": this.target_table_rows
                                     };
            fs.writeFileSync('configs/target_list.json',
                             JSON.stringify(target_table_data, null, 3)
                             );
        },
    },
    watch: {
        excel_clipboard_text: function(new_value, old_value) {
            if (new_value === old_value || !new_value.length) {
                return
            }
            this.parseExcelClipboard(new_value);
        },
        excel_clipboard_use_header: function(new_value) {
            if (new_value) {
                let header = this.excel_clipboard_table_rows.slice(0, 1)[0];
                for (let i=0; i<this.excel_clipboard_table_cols.length; i++) {
                    let label = header[i];
                    this.excel_clipboard_table_cols[i]['label'] = label.slice(0);
                }
                this.excel_clipboard_table_rows = this.excel_clipboard_table_rows.slice(1);
            }
        },
        figure_double_click: function() {
            this.peak_table_selected_row = null;
        },
        identified_ions: function(new_value) {
            // Format data to sample table
            let identified_ions = new_value;
            let rows = [];
            let cols = [];
            for (const ion in identified_ions) {
                const identified_ion_peaks = identified_ions[ion];
                for (const peak_i in identified_ion_peaks) {
                    let peak = identified_ion_peaks[peak_i];
                    let row = {};
                    // Unpack attributes
                    let keys = Object.keys(peak);
                    for (let k in keys) {
                        let key = keys[k];
                        let value = peak[key];
                        if (Number(value) && value != 0) {
                            value = Math.round((value + Number.EPSILON) * 10000) / 10000;
                        }
                        if (rows.length == 0) {
                            let col = {
                                'field': key.toLowerCase(),
                                'label': key,
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
                    if (row['peak mz'] > -1) {
                        console.log("push checked row");
                        this.peak_table_checked_rows.push(row);
                    }
                }
            }
            this.peak_table_cols = cols;
            this.peak_table_rows = rows;
        },
        identify_peaks: function(new_value, old_value) {
            if (_.isEqual(new_value, old_value)) {
                return
            }
            this.be.export_one_way_binding_prop('identify_peaks',
                                                {...new_value,
                                                 'room': this.room_sid,
                                                 'uid': Math.random(),
                                                 },
                                                old_value,
                                                this.room_sid
                                                );
        },
        integrate_target_ions: function(new_value, old_value) {
            if (_.isEqual(new_value, old_value)) {
                return
            }
            this.be.export_one_way_binding_prop('integrate_target_ions',
                                                {...new_value,
                                                 'room': this.room_sid,
                                                 'uid': Math.random(),
                                                 },
                                                old_value,
                                                this.room_sid
                                                );
        },
        peak_data: function(new_value) {
            this.identify_peaks = {'peaks': new_value,
                                   'targets': this.targets
                                   };
        },
        target_ion_intensities: function(new_value) {
            this.target_table_cols.push({'field': "intensity",
                                         'label': "Intensity"
                                         });
            for (const i in this.target_table_rows) {
                this.target_table_rows[i]['intensity'] = new_value[i];
            }
        },
        peak_table_selected_row: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if (new_value != null) {
                let mz = new_value['mz'];
                // let keys = Object.keys(new_value);
                // let mz = null;
                // // Loop through columns until find numeric value, assume it to be m/z
                // for (let i=0; keys.length; i++) {
                //     mz = Number( new_value[keys[i]] );
                    if (mz) {
                        this.target_to_display = mz;
                        return
                    }
                // }
            } else {
                this.target_to_display = null;
            }
        },
        targets: function(new_data, old_data){
            if ( _.isEqual(new_data, old_data) ) {
                return false;
            }
            this.target_table_cols = new_data.cols;
            this.target_table_rows = new_data.rows;
            this.writeTargetsToFile();
            this.requestTargetIntensities();
        },
        'root_namespace.connected': function(new_value) {
            if ( new_value === true )
            {
                this.namespace = this.root_namespace;
                // handlers for for external notifications:
                this.namespace.on("identified_ions", (value) => this.be.import_one_way_binding_prop("identified_ions", value.value));
                this.namespace.on("target_ion_intensities", (value) => this.be.import_one_way_binding_prop("target_ion_intensities", value.value));
                this.namespace.on("targets", (value) => this.be.import_one_way_binding_prop("targets", value.value));
                this.room_sid = this.root_namespace.id;
                this.be.subscribe(this.endpoints, this.room_sid);
            }
        },
    }
};


</script>