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
                            @click="ImportExcelTargets()"
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
                <b-collapse class="card" animation="slide" aria-id="contentIdForA11y3">
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
import { get_parent_context,
         subscribe,
         import_one_way_binding_prop,
         export_one_way_binding_prop } from '../karsalib';

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
            'socket',
            'socket_connected',
            // 'targets',
        ]),
        // target_list_request: {
        //     get() {
        //         return this.$store.state.target_list_request;
        //     },
        //     set(value) {
        //         this.$store.commit('target_list_request', value);
        //     }
        // },
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
            // variables for excel clipboard import
            is_excel_clipboard_modal_active: false,
            excel_clipboard_text: "",
            excel_clipboard_table_cols: [],
            excel_clipboard_table_rows: [],
            excel_clipboard_use_header: false,
            // Target table
            targets: [],
            target_table_rows: [],
            target_table_cols: [],
            target_table_selected_row: {},
            endpoints: [
                'targets',
            ]
        }
    },
    created: function() {
        get_parent_context(this);

// //==============================
//         get_parent_context(this);
//         var self = this;
//         self.socket.on("connect", () => {
//             // handlers for for external notifications:
//             self.socket.on("targets", (value) => import_one_way_binding_prop("targets", value.value));

//             subscribe();
//         });
// // =============================

    },
    mounted: function() {
        this.ReadTargetsFromFile();
    },
    methods: {
        ImportExcelTargets() {
            this.target_table_cols = this.excel_clipboard_table_cols;
            this.target_table_rows = this.excel_clipboard_table_rows;
            this.is_excel_clipboard_modal_active = false;
            this.WriteTargetsToFile();
        },
        ParseExcelClipboard: function(clipboard_text) {
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
        ReadTargetsFromFile() {
            let target_table_data = JSON.parse(
                                        fs.readFileSync('configs/target_list.json')
                                        );
            this.target_table_cols = target_table_data.cols;
            this.target_table_rows = target_table_data.rows;
        },
        WriteTargetsToFile() {
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
            this.ParseExcelClipboard(new_value);
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
        target_table_selected_row:function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if (new_value != null) {
                let keys = Object.keys(new_value);
                let mz = null;
                for (let i=0; keys.length; i++) {
                    mz = parseFloat( new_value[keys[i]] );
                    if (mz) {
                        this.target_to_display = parseFloat(mz);
                        return
                    }
                }
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
        },
        target_to_display: function(new_value, old_value) {
            return export_one_way_binding_prop('target_to_display', new_value, old_value);
        },
        socket_connected: function(new_value) {
            if ( new_value === true )
            {
                // handlers for for external notifications:
                this.socket.on("targets", (value) => import_one_way_binding_prop("targets", value.value));
                subscribe();
            }
        },
    }
};


</script>

<style src = "../assets/css/MeasurementTab.css"> </style>