<template>
    <div>
    <!-- Modals -->
        <!--- Add log entry modal--> 
        <section class="add-log-entry-modal">
            <b-modal :active.sync="is_modal_add_log_entry_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px;">
                    <!-- Main content -->
                    <div>
                        <header class="modal-card-head">
                            <p class="modal-card-title">
                                Add instrument log entry
                            </p>
                        </header>
                        <section class="modal-card-body">
                            <b-field label="Datetime">
                                <b-datetimepicker
                                    v-model="log_entry_datetimestamp"
                                    icon="calendar-today"
                                    :timepicker="{'hour-format': '24'}"
                                    horizontal-time-picker>
                                </b-datetimepicker>
                            </b-field>
                            <MetaDataForm
                                :default_template="log_entry_default_template"
                                :editable="true"
                                :template_path="log_entry_template_path"
                                @metaDataUpdated="log_entry_fields=$event"
                                >
                            </MetaDataForm>
                            <div><br></div>
                        </section>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button
                            @click="writeInstrumentLogEntry()"
                            :type="log_entry_save_button_type">
                            Save
                        </b-button>
                        <b-button
                            is-dark
                            @click="is_modal_add_log_entry_active=false;
                                    is_modal_instrument_log_active=true">
                            Cancel
                        </b-button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of add log entry modal-->

        <!--- Show log modal--> 
        <section class="instrument-log-modal">
            <b-modal :active.sync="is_modal_instrument_log_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="false"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px;">
                    <!-- Main content -->
                    <div>
                        <header class="modal-card-head">
                            <p class="modal-card-title">
                                Instrument log
                            </p>
                        </header>
                        <section class="modal-card-body">
                            <b-table
                                :data="instrument_log_rows">
                                <template v-for="column in instrument_log_cols">
                                    <b-table-column :key="column.id" v-bind="column">
                                        <template
                                            #searchable="props">
                                            <b-input
                                                v-model="props.filters[props.column.field]"
                                                placeholder="Search..."
                                                icon="magnify"
                                                size="is-small" />
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
                        <b-button
                            type="is-success"
                            @click="onButtonInstrumentLogEntry()">
                            New entry
                        </b-button>
                        <b-button
                            is-dark
                            @click="is_modal_instrument_log_active=false;">
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
                :active.sync="is_modal_desorption_step_active"
                has-modal-card
                trap-focus
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <!-- <header class="modal-card-head">
                            <p class="modal-card-title">Scenthound parameters</p>
                        </header> -->
                        <section class="modal-card-body idparams-edit-body">
                            <b-field label="time [s]">
                                <b-input
                                    v-model="desorption_step_modal_time"
                                    placeholder="seconds">
                                </b-input>
                            </b-field>

                            <b-field label="Temperature [C]">
                                <b-input
                                    v-model="desorption_step_modal_temperature"
                                    placeholder="Temperature">
                                </b-input>
                            </b-field>

                            <b-field label="Cassette in">
                                <b-switch
                                    v-model="desorption_step_modal_filter_in">
                                </b-switch>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                @click="editDesorptionCycle()"
                                :disabled="!(desorption_step_modal_temperature && desorption_step_modal_time)">
                                Save
                            </b-button>
                            <b-button
                                @click="is_modal_desorption_step_active=false">
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
                <b-collapse
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
                            {{ data_source_selected.name }}
                        </p>
                        <a class="card-header-icon">
                            <b-icon
                                :icon="props.open ? 'menu-down' : 'menu-up'">
                            </b-icon>
                        </a>
                    </div>
                    <div class="card-content">
                        <div class="content">
                            <!-- Instrument status display -->
                            <div style="text-align:center; margin-top:.4rem; margin-bottom:1rem">
                                <h1 class="acquisition-parameters-h1">
                                    Instrument status: {{ scenthound_status }}
                                </h1>
                            </div>
                            <!-- End of instrument status display -->
                            <!-- Acquisition progress bar -->
                            <div style="margin-left:1rem; margin-right:1rem; margin-bottom:1rem">
                                <b-progress
                                    v-bind:value="acquisition_progress"
                                    show-value
                                    format="percent"
                                    :precision="1"
                                    type="is-primary"
                                    size="is-large">
                                </b-progress>
                            </div>
                            <!-- End of acquisition progress bar -->
                            <!-- Controls -->
                            <div style="text-align: center">
                                <div v-if="method.tofdaq.acquisition_mode==='manual'">
                                    <b-button
                                        v-bind:icon-left="acquisition_status=='starting' || 
                                                        acquisition_status=='stopping' ||
                                                        instrument_status=='not_ready' ? 'flattr' : ''"
                                        :type="acquisition_button_type"
                                        :disabled="method.tofdaq.acquisition_mode=='triggered' ||
                                                instrument_status=='not_ready'"
                                        @click="on_button_change_acquisition_status()">
                                        {{ acquisition_control_label }}
                                    </b-button>
                                    <div><br></div>
                                </div>
                                <b-button
                                    type="is-primary"
                                    :disabled="!control_mode_active"
                                    @click="onButtonShowInstrumentLog()">
                                    Instrument log
                                </b-button>
                                <div><br></div>

                            </div>
                            <!-- End of controls -->
                        </div>
                        <section style="width:100%; padding:0.5rem;">
                            <!-- Method collapsable -->
                            <b-collapse
                                class="card"
                                animation="slide"
                                aria-id="contentIdForA11y3">
                                <div
                                    slot="trigger" 
                                    slot-scope="props"
                                    class="card-header"
                                    style="background-color:transparent"
                                    role="button"
                                    aria-controls="contentIdForA11y3">
                                    <p class="card-header-title">
                                        Method
                                    </p>
                                    <a class="card-header-icon">
                                        <b-icon
                                            :icon="props.open ? 'menu-down' : 'menu-up'">
                                        </b-icon>
                                    </a>
                                </div>
                                <div
                                    class="card-content"
                                    style="background-color:#3f3f48">
                                    <div class="content">
                                        <!-- TofDaq section -->
                                        <section style="width:100%;padding:0.5rem;">
                                            <div
                                                class="card-content"
                                                style="background-color:#50505a">
                                                <div
                                                    class="box"
                                                    style="background-color:inherit">
                                                    <h1 style="font-size:16px; text-align:center;">
                                                        <p><b>TofDaq</b>
                                                        </p>
                                                    </h1>
                                                    <b-field label="Acquisition mode">
                                                        <div style="text-align:center; color:white">
                                                            <b-radio
                                                                type="is-white"
                                                                v-model="method.tofdaq.acquisition_mode"
                                                                native-value="triggered">
                                                                Triggered
                                                            </b-radio>
                                                            <b-radio
                                                                type="is-white"
                                                                v-model="method.tofdaq.acquisition_mode"
                                                                native-value="manual">
                                                                Manual
                                                            </b-radio>
                                                        </div>
                                                    </b-field>
                                                    <b-field label="Sample length [s]">
                                                        <b-input
                                                            size="is-small"
                                                            placeholder="seconds"
                                                            v-model="method.tofdaq.sample_length"
                                                            type="number"
                                                            min="0"
                                                            max="20000"
                                                            lazy>
                                                        </b-input>
                                                    </b-field>
                                                </div>
                                            </div>
                                        </section>
                                        <!-- End of TofDaq section -->
                                        <!-- TPS section -->
                                        <section style="width:100%;padding:0.5rem;">
                                            <div
                                                class="card-content"
                                                style="background-color:#50505a">
                                                <div
                                                    class="box"
                                                    style="background-color:inherit">
                                                    <h1 style="font-size:16px; text-align:center;">
                                                        <p><b>TPS</b>
                                                        </p>
                                                    </h1>
                                                    <div class="">
                                                        <b-field label="TPS settings file">
                                                            <b-input
                                                                size="is-small"
                                                                v-model="method.tps.settings_file"
                                                                lazy>
                                                            </b-input>
                                                        </b-field>
                                                        <b-field label="TPS settings file directory">
                                                            <b-input
                                                                size="is-small"
                                                                v-model="method.tps.settings_file_directory"
                                                                lazy>
                                                            </b-input>
                                                        </b-field>
                                                    </div>
                                                </div>
                                            </div>
                                        </section>
                                        <!-- End of TPS section -->
                                        <!-- CI section -->
                                        <section style="width:100%;padding:0.5rem;">
                                            <div
                                                class="card-content"
                                                style="background-color:#50505a">
                                                <MetaDataForm
                                                    form_title="CI configuration"
                                                    :editable="true"
                                                    :default_template="[{'label': 'Reagent flow',
                                                                            'value': ''
                                                                            },
                                                                        {'label': 'Sample flow',
                                                                            'value': ''
                                                                            },
                                                                        {'label': 'Sheath flow',
                                                                            'value': ''
                                                                            }]"
                                                    :template_path="ci_template_path"
                                                    @metaDataUpdated="method.ci=$event">
                                                </MetaDataForm>
                                            </div>
                                        </section>
                                        <!-- End of CI section -->
                                        <!-- Desorption section -->
                                        <section style="width:100%;padding:0.5rem;">
                                            <div
                                                class="card-content"
                                                style="background-color:#50505a">
                                                <div
                                                    class="box"
                                                    style="background-color:inherit">
                                                    <h1 style="font-size:16px; text-align:center;">
                                                        <p><b>Desorption cycle</b>
                                                        </p>
                                                    </h1>
                                                    <!-- Desorption cycle edot buttons -->
                                                    <div class="desorption-temperature-ramp-controls">
                                                        <b-tooltip
                                                            label="Add step"
                                                            position="is-left"
                                                            :delay="500">
                                                            <b-button
                                                                icon-left="file-document-box-plus-outline"
                                                                size="is-small"
                                                                type="is-dark"
                                                                @click="desorption_table_selected_row=null; launchDesorptionStepModal()"
                                                                outlined
                                                                inverted> 
                                                            </b-button>
                                                        </b-tooltip>
                                                        <b-tooltip
                                                            label="Edit step"
                                                            position="is-left"
                                                            :delay="500">
                                                            <b-button
                                                                icon-left="file-document-edit-outline"
                                                                size="is-small"
                                                                type="is-dark"
                                                                @click="launchDesorptionStepModal()"
                                                                v-if="desorption_table_selected_row !=null"
                                                                outlined
                                                                inverted>
                                                            </b-button>
                                                        </b-tooltip>
                                                        <b-tooltip
                                                            label="Remove step"
                                                            position="is-left"
                                                            :delay="500">
                                                            <b-button
                                                                icon-left="trash-can-outline"
                                                                size="is-small"
                                                                type="is-dark"
                                                                @click="deleteDesorptionCycleStep()"
                                                                v-if="desorption_table_selected_row !=null"
                                                                outlined
                                                                inverted>
                                                            </b-button>
                                                        </b-tooltip>
                                                    </div>
                                                    <!-- End of desorption cycle edot buttons -->
                                                    <div class="">
                                                        <b-table
                                                            class="desorption-temperature-ramp-table desorption-data-table"
                                                            :data="desorption_table_data"
                                                            :columns="desorption_table_columns"
                                                            :selected.sync="desorption_table_selected_row">
                                                        </b-table>
                                                    </div>
                                                    <div id="desorption-chart-holder">
                                                        <div
                                                            class="columns"
                                                            style="margin-left:2px;"
                                                            id="desorption-chart">
                                                        </div>
                                                    </div>
                                                    <br>
                                                </div>
                                            </div>
                                        </section>
                                        <!-- End of Desorption section -->
                                    </div>
                                    <div style="text-align:center; padding:10px">
                                        <b-button
                                            :type="button_save_method_type"
                                            @click="saveMethod();">
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


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from 'vuex'
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';
import { BECom, shallow_copy } from "../karsalib.js"
import MetaDataForm from "./MetaDataForm.vue"


Vue.use([Buefy]);

var fs = require('fs');
// var path = require('path');
var Plotly = require('plotly.js-dist');
var _ = require('underscore');

export default {
    name: "TOFControl",
    components: {
        MetaDataForm,
    },
    props: [
    ],
    computed: {
        ...mapState([
            'url',
            'data_source_selected',
            'experiment_selected',
            'tofdaq_log_entry',
        ]),
        acquisition_status: {
            get() {
                return this.$store.state.acquisition_status;
            },
            set(value) {
                this.$store.commit('acquisition_status', value);
            }
        },
        new_file: {
            get() {
                return this.$store.state.new_file;
            },
            set(value) {
                this.$store.commit('new_file', value);
            }
        },

    },
    data: function() {
        return {
            // UI variables
            acquisition_button_type: "is-success",
            acquisition_control_label: "Start Acquisition",
            button_save_method_type: "is-success",
            control_mode_active: false,
            is_modal_add_log_entry_active: false,
            is_modal_desorption_step_active: false,
            is_modal_instrument_log_active: false,
            //
            // Communication
            be: null,
            namespace: null,
            room_sid: null,
            endpoints: [
                'acquisition_progress',
                'acquisition_started',
                'acquisition_status',
                'instrument_status',
            ],
            // TOF variables
            acquisition_progress: 0,
            acquisition_started: {},
            instrument_log: [],
            instrument_log_rows: [],
            instrument_log_cols: [],
            instrument_status: "not_ready",			// not_ready/ready
            scenthound_status: "Offline",       // Offline/Ready/Measuring.../Processing...
            //
            // Method variables
            ci_template_path: "./metadata_templates/ci_templates",
            method: {
                tofdaq: {
                    acquisition_mode: null,
                    sample_length: null,
                },
                ci: [],
                desorption_cycle: [],
                tps: {
                    settings_file: null,
                    settings_file_directory: null,
                },
            },
            method_json: null,
            // 
            // Log entry modal variables
            log_entry: null,
            log_entry_datetimestamp: null,
            log_entry_default_template: [{'label': "Log text",
                                          'value': ""}],
            log_entry_fields: [],
            log_entry_save_button_type: "is-success",
            log_entry_template_path: "./metadata_templates/instrument_templates",
            //
            // variables for desorption config
            desorption_step_modal_filter_in: true,
            desorption_step_modal_time: null,
            desorption_step_modal_temperature: null,

            desorption_chart_data: [],

            desorption_table_data: [],
            desorption_table_columns: [
                {
                    "field": "time",
                    "label": "time [s]"
                },
                {
                    "field": "temperature",
                    "label": "Temp. [C]"
                },
                {
                    "field": "filter_in",
                    "label": "Cassette in"
                },
            ],
            desorption_table_selected_row: null,
            // 
        }
    },
    created: function() {
        this.be = new BECom(this);
        this.confirmAcquisitionControl();        
    },
    mounted: function() {
        this.initializeMethod();
    },
    methods: {
        addDesorptionCycleStep() {
            this.method.desorption_cycle.push({
                "filter_in": this.desorption_step_modal_filter_in,
                "time": this.desorption_step_modal_time,
                "temperature": this.desorption_step_modal_temperature
            });
            this.method.desorption_cycle = this.method.desorption_cycle.sort(function(a, b) {
                return a.time - b.time;
            });
        },
        confirmAcquisitionControl() {
            this.$buefy.dialog.confirm({
                title: 'Instrument control',
                message: `You have requested access to instrument controls.
                          Please proceed only if are willing to operate the instrument.`,
                cancelText: 'Cancel',
                confirmText: 'Proceed',
                type: 'is-danger',
                onCancel: () => this.control_mode_active = false,
                onConfirm: () => { this.$buefy.toast.open({message: 'Instrument control granted',
                                                          type: 'is-success'});
                                   this.be.connect(this.url + '/' + this.data_source_selected.name); }
            })
        },
        deleteDesorptionCycleStep() {
            var delete_index = null;
            for (let i in this.desorption_table_data) {
                if (_.isEqual(this.desorption_table_data[i],
                              this.desorption_table_selected_row
                              )) {
                    delete_index = i;
                }
            }
            if (delete_index) {
                this.method.desorption_cycle.splice(delete_index, 1);
            }
        },
        drawDesorptionTable() {
            this.desorption_table_data = [];
            for (let i in this.method.desorption_cycle) {
                let step = this.method.desorption_cycle[i];
                this.desorption_table_data.push(step);
            }
        },
        drawDesorptionChart() {
            // format the data and draw the chart
            this.desorption_chart_data = [ shallow_copy(desorption_chart_trace) ];
            let filter_in = true;
            for (let i in this.method.desorption_cycle) {
                var step = this.method.desorption_cycle[i];
                if (step.filter_in != filter_in) {
                    filter_in = step.filter_in;
                    let prev_trace = this.desorption_chart_data[this.desorption_chart_data.length-1];
                    prev_trace.x.push(step.time);
                    prev_trace.y.push(step.temperature);
                    let new_trace = shallow_copy(desorption_chart_trace);
                    this.desorption_chart_data.push(new_trace);
                }
                this.desorption_chart_data[this.desorption_chart_data.length-1].x.push(step.time);
                this.desorption_chart_data[this.desorption_chart_data.length-1].y.push(step.temperature);
                if (filter_in) {
                    this.desorption_chart_data[this.desorption_chart_data.length-1].fill = "tozeroy";
                }
                desorption_chart_layout["xaxis"].tickvals.push(step.time);
                desorption_chart_layout["xaxis"].ticktext.push(step.time.toString());
                desorption_chart_layout["yaxis"].tickvals.push(step.temperature);
                desorption_chart_layout["yaxis"].ticktext.push(step.temperature.toString());
            }
            if (step.time < this.sample_length) {
                this.desorption_chart_data[this.desorption_chart_data.length-1].x.push(this.sample_length);
                this.desorption_chart_data[this.desorption_chart_data.length-1].y.push(step.temperature);
            }
            Plotly.react("desorption-chart",
                         this.desorption_chart_data,
                         desorption_chart_layout,
                         desorption_chart_config
                         );
        },
        editDesorptionCycle() {
            if (this.desorption_table_selected_row) {
                this.deleteDesorptionCycleStep();
            }
            this.addDesorptionCycleStep();
            this.is_modal_desorption_step_active = false;
        },
        onButtonInstrumentLogEntry() {
            this.log_entry_datetimestamp = new Date();
            this.is_modal_instrument_log_active = false;
            this.is_modal_add_log_entry_active = true;
        },
        onButtonShowInstrumentLog() {
            this.be.emit_client_notification('instrument_log_request', {});
            this.is_modal_instrument_log_active = true;
        },
        on_button_change_acquisition_status() {
            let next_status = {"not_running": "starting",
                               "starting": "stopping",
                               "running": "stopping",
                               "stopping": "stopping"};
            this.acquisition_status = next_status[this.acquisition_status];
        },
        initializeMethod() {
            try {
                if (fs.existsSync('configs/tofcontrol_config.json')) {
                    let tofcontrol_config = JSON.parse(fs.readFileSync('configs/tofcontrol_config.json', 'utf8'));
                    this.method = tofcontrol_config;
                }
            } catch (err) {
                console.error(err)
            }
            // ===== Initialize Plotly figure =====
            Plotly.newPlot("desorption-chart",
                           [],
                           desorption_chart_layout,
                           desorption_chart_config
                           );
        },
        saveMethod() {
            fs.writeFileSync('configs/tofcontrol_config.json',
                             this.method_json
                             );
            this.button_save_method_type = "is-success";
        },
        launchDesorptionStepModal() {
            this.desorption_step_modal_filter_in = this.desorption_table_selected_row ? this.desorption_table_selected_row.filter_in : true;
            this.desorption_step_modal_time = this.desorption_table_selected_row ? this.desorption_table_selected_row.time : null;
            this.desorption_step_modal_temperature = this.desorption_table_selected_row ? this.desorption_table_selected_row.temperature : null;
            this.is_modal_desorption_step_active = true;
        },
        writeInstrumentLogEntry() {
            var self = this;
                
            // Parse datetime into string
            let dt = self.log_entry_datetimestamp;
            let hours_diff = dt.getHours() - dt.getTimezoneOffset() / 60;
            dt.setHours(hours_diff);
            // Combine timestamp with log entry fields and write to file
            var log_entry_data = {
                    timestamp: dt.toJSON(),
                    entry: self.log_entry_fields
                    }

            self.be.export_one_way_binding_prop(
                                'instrument_log_entry',
                                log_entry_data,
                                self.log_entry,
                                );
            self.log_entry = log_entry_data;
            self.log_entry_save_button_type = "is-success";
            self.is_modal_add_log_entry_active = false;
            self.onButtonShowInstrumentLog();
        },
    },
    watch: {
        data_source_selected: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) )
                return false;
            // this.be.unsubscribe(this.endpoints, null);   //TODO: is it needed?
            this.be.disconnect(this.namespace);
            this.be.connect(this.url + '/' + this.data_source_selected.name);
        },
        acquisition_started: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            this.new_file = {...new_value,
                             "method": this.method,
                             };
        },
        acquisition_status: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            if(new_value === "starting"){
                this.acquisition_control_label = "Starting Acquisition";
                this.acquisition_button_type = "is-danger";
                this.be.emit_client_notification('start_acquisition', {});
            }
            if(new_value === "stopping"){
                this.acquisition_control_label = "Stopping Acquisition";
                this.acquisition_button_type = "is-danger";
                this.scenthound_status = 'Processing...';
                this.be.emit_client_notification('stop_acquisition', {});
            }
            if(new_value === "running"){
                this.sample_table_checked_rows = [];
                this.acquisition_control_label = "Stop Acquisition";
                this.acquisition_button_type = "is-danger";
                this.scenthound_status = 'Measuring...';
            }
            if(new_value === "not_running"){
                this.acquisition_control_label = "Start Acquisition";
                this.acquisition_button_type = "is-success";
                this.scenthound_status = 'Ready';
            }
        },
        instrument_log: function(new_value) {
            if (!new_value.length) {
                this.instrument_log_rows = [];
                this.instrument_log_cols = [];
                return
            }
            let col_fields = [];
            let cols = [
                {'field': "timestamp",
                 'label': "Timestamp",
                 'searchable': true,
                 }
            ];
            let rows = [];
            for (let i in new_value) {
                var row = {};
                const entry_data = new_value[i];
                const timestamp = entry_data.timestamp;
                row.timestamp = timestamp;
                const entry = entry_data.entry;
                for (let j in entry) {
                    const label = entry[j].label;
                    const field = label.toLowerCase();
                    if (col_fields.indexOf(field) == -1) {
                        // Add field
                        col_fields.push(field);
                        cols.push({'field': field,
                                   'label': label,
                                   'searchable': true
                                   });
                    }
                    const value = entry[j].value;
                    row[field] = value;
                }
                rows.push(row);
            }
            this.instrument_log_rows = rows;
            this.instrument_log_cols = cols;

            // Update log entry default template with all existing fields
            let instrument_log_all_fields = [];
            for (let i=1; i<cols.length; ++i) { // Ignore timestamp
                const field = 
                    {'label': cols[i].label,
                     'value': row[cols[i].field] || "" // Value from last entry
                     };
                instrument_log_all_fields.push(field);
            }
            this.log_entry_default_template = instrument_log_all_fields;
        },
        instrument_status: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if (new_value === 'ready') {
                this.scenthound_status = 'Ready';
            }
            else {
                this.scenthound_status = 'Offline';
                this.acquisition_status = 'not_running';
            }
        },
        log_entry_fields: {
            handler() {
                this.log_entry_save_button_type = "is-danger";
            },
            deep: true
        },
        method: {
            handler() {
                this.method_json = JSON.stringify(this.method, null, 4);
                this.button_save_method_type = "is-danger";
            },
            deep: true
        },
        'method.desorption_cycle': function() {
            this.drawDesorptionTable();
            this.drawDesorptionChart();
        },
        tofdaq_log_entry: function(new_value, old_value) {
            let texts = new_value.text.split("<br>").slice(0, -1);
            for (let i in texts){
                texts[i] = texts[i].replace(': ', '=');
            }
            const joint_text = texts.join(', ');
            new_value.text = joint_text.slice(0, 255);

            this.be.export_one_way_binding_prop('tofdaq_log_entry',
                                                new_value,
                                                old_value,
                                                this.room_sid);
        },
        'namespace.connected': function(new_value) {
            if (new_value) {
                // on connect 
                this.control_mode_active = true;
                // handlers for for external notifications:
                this.namespace.on("acquisition_started", (value) => this.be.import_one_way_binding_prop("acquisition_started", value.value));
                this.namespace.on("acquisition_status", (value) => this.be.import_one_way_binding_prop("acquisition_status", value.value));
                this.namespace.on("acquisition_progress", (value) => this.be.import_one_way_binding_prop("acquisition_progress", value.value.progress, true));
                this.namespace.on("instrument_log", (value) => this.be.import_one_way_binding_prop("instrument_log", value.value));
                this.namespace.on("instrument_status", (value) => this.be.import_one_way_binding_prop("instrument_status", value.value));

                this.be.subscribe(this.endpoints,
                                  null // room set to null to subscribe to endpoints directly
                                  );
            } else {
                // on disconnect
                this.control_mode_active = false;
            }
        },
    }
};

var desorption_chart_trace = {
        "name": "",
        "line": {
            "shape": "hv"
        },
        "mode": "lines",
        "type": "scatter",
        "x": [],
        "y": [],
        "hoverinfo": "x,y",
};

var desorption_chart_layout = {
    "width": 280,
    "height": 280,

    "font": {
        "color": "#fff"
    },

    "xaxis": {
        "title": "time [s]",
        "tickmode": "array",
        "tickvals": [],
        "ticktext": [],
        "visible": true,
        "linecolor": "#999",
        "rangemode": "tozero",
        "showgrid": false,
        },

    "yaxis": {
        "title": "Temperature [C]",
        "tickmode": "array",
        "tickvals": [],
        "ticktext": [],
        "visible": true,
        "linecolor": "#999",
        "rangemode": "tozero",
        "showgrid": false,
        },

    "showlegend": false,
    "dragmode": false,
    
    "plot_bgcolor": "transparent",
    "paper_bgcolor": "transparent",

    "margin": {
        "l": 30,
        "r": 20,
        "b": 25,
        "t": 60,
        "pad": 0
    }
};

var	desorption_chart_config = {
    "responsive": true,
    "displaylogo": false,
    "modeBarButtonsToRemove": [
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
        "zoomOut2d"
        ]
};

</script>
