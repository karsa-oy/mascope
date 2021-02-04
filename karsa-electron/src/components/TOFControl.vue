<template>
    <div>
<!-- Modals -->
        <!-- Modal for edit temperature ramp datatable values -->
        <section class="modal-edit-temperature-ramp-data-table-row">
            <b-modal :active.sync="is_edit_temperature_ramp_modal_active"
                has-modal-card
                trap-focus
                aria-role="dialog"
                aria-modal
            >
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <!-- <header class="modal-card-head">
                            <p class="modal-card-title">Scenthound parameters</p>
                        </header> -->
                        <section class="modal-card-body idparams-edit-body">
                            <b-field label="t(s)">
                                <b-input
                                    v-model="edit_dialog_time"
                                    :value="edit_dialog_time"
                                    placeholder="seconds"
                                >
                                </b-input>
                            </b-field>

                            <b-field label="Temperature">
                                <b-input
                                    v-model="edit_dialog_temperature"
                                    :value="edit_dialog_temperature"
                                    placeholder="Temperature"
                                >
                                </b-input>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="edit_row_in_config_desorption_table()">
                                Save
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_edit_temperature_ramp_modal_active=false">
                                Close
                            </button>
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
                <b-collapse
                    class="card"
                    animation="slide"
                    aria-id="contentIdForA11y3"
                    :open.sync="acquisition_control_active">
                    <div
                        slot="trigger" 
                        slot-scope="props"
                        class="card-header"
                        role="button"
                        aria-controls="contentIdForA11y3">
                        <p class="card-header-title">
                            Acquisition
                        </p>
                        <a class="card-header-icon">
                        <b-icon
                            :icon="props.open ? 'menu-down' : 'menu-up'">
                        </b-icon>
                        </a>
                    </div>
                    <div class="card-content">
                        <div class="content">
                            <div style="text-align:center; margin-top:.4rem; margin-bottom:1rem">
                                <h1 class="acquisition-parameters-h1">
                                    Scenthound status: {{ scenthound_status }}
                                </h1>
                            </div>
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
                            <div style="text-align: center">
                                <b-button
                                    v-bind:icon-left="acquisition_status=='starting' || 
                                                    acquisition_status=='stopping' ||
                                                    instrument_status=='not_ready' ? 'flattr' : ''"
                                    :type="acquisition_button_type"
                                    :disabled="acquisition_mode=='triggered' ||
                                            instrument_status=='not_ready'"
                                    @click="on_button_change_acquisition_status()">
                                    {{ acquisition_control_label }}
                                </b-button>
                                <div><br></div>
                            </div>
<div hidden>
                            <h1 class="acquisition-parameters-h1">
                                Measurement Mode
                            </h1>
                            <div class="acquisition-parameters-form">
                                <b-field grouped>
                                    <b-radio
                                        type="is-white"
                                        v-model="acquisition_mode"
                                        native-value="triggered">
                                        Triggered
                                    </b-radio>
                                    <b-radio
                                        type="is-white"
                                        v-model="acquisition_mode"
                                        native-value="continuous">
                                        Continuous
                                    </b-radio> 

                                    <label class="sample-length-label">
                                        Sample length(s)
                                    </label>
                                    <b-input
                                        class="sample-length"
                                        size="is-small"
                                        placeholder="90"
                                        v-model="sample_length"
                                        :value="sample_length"
                                        type="number"
                                        min="0"
                                        max="20000">
                                    </b-input>
                                </b-field>
                            </div>
                            <!-- Desorption collapsable -->
                            <section style="width:100%;padding:0.5rem;">
                                <b-collapse
                                    class="inner-collapsable card"
                                    @open="draw_desorption_chart()"
                                    :open="false"
                                    animation="slide"
                                    aria-id="contentIdForA11y3">
                                    <div
                                        slot="trigger" 
                                        slot-scope="props"
                                        class="inner-collapsable card-header"
                                        role="button"
                                        aria-controls="contentIdForA11y3">
                                        <p class="card-header-title">
                                            Desorption Temperature ramp
                                        </p>
                                        <a class="card-header-icon">
                                        <b-icon
                                            :icon="props.open ? 'menu-down' : 'menu-up'">
                                        </b-icon>
                                        </a>
                                    </div>
                                    <div class="card-content">
                                        <div class="desorption-temperature-ramp-controls">
                                            <b-button
                                                icon-left="file-document-box-plus-outline"
                                                size="is-small"
                                                type="is-dark"
                                                @click="show_add_new_row=true"
                                                outlined
                                                inverted> 
                                            </b-button>
                                            <b-button
                                                icon-left="file-document-edit-outline"
                                                size="is-small"
                                                type="is-dark"
                                                @click="show_desorption_edit_modal()"
                                                v-if="desorption_table_selected_row !=null"
                                                outlined
                                                inverted>
                                            </b-button>
                                            <b-button
                                                icon-left="trash-can-outline"
                                                size="is-small"
                                                type="is-dark"
                                                @click="delete_row_in_config_desorption_table()"
                                                v-if="desorption_table_selected_row !=null"
                                                outlined
                                                inverted>
                                            </b-button>
                                        </div>
                                        <div
                                            class="columns add-new-desorption-row"
                                            v-if="show_add_new_row==true">
                                            <div class="column" style="width:30%"> 
                                                <b-input
                                                    size="is-small"
                                                    v-model="time"
                                                    type="number"
                                                    placeholder="time">
                                                </b-input>
                                            </div>
                                            <div class="column" style="width:30%">
                                                <b-input
                                                    size="is-small"
                                                    v-model="temperature"
                                                    type="number"
                                                    placeholder="temperature">
                                                </b-input>
                                            </div>
                                            <div class="" style="width:40%; padding-top:15px;">
                                                <b-button 
                                                    type="is-dark" 
                                                    size="is-small" 
                                                    @click="save_new_row_in_config_desorption_table()" 
                                                    outlined 
                                                    inverted>
                                                    Save
                                                </b-button>
                                                &nbsp; 
                                                <b-button 
                                                    type="is-dark" 
                                                    size="is-small" 
                                                    @click="show_add_new_row=false;
                                                            time=''; 
                                                            temperature='';"
                                                    outlined 
                                                    inverted>
                                                    Cancel
                                                </b-button>
                                            </div>
                                        </div>
                                        <div class="">
                                            <b-table
                                                class="desorption-temperature-ramp-table desorption-data-table"
                                                :data="desorption_table_data"
                                                :columns="desorption_table_columns"
                                                per-page="5"
                                                current-page.sync="0"
                                                :paginated="true" 
                                                :pagination-simple="false"
                                                :checked-rows.sync="desorption_table_checked_rows"
                                                :selected.sync="desorption_table_selected_row"
                                                checkable
                                                sortable
                                                default-sort-direction="asc"
                                                :default-sort="['time', 'asc']"
                                                checkbox-position="right"
                                                :header-checkable="false"
                                                focusable>
                                            </b-table>
                                        </div>
                                        <div id="desorption-chart-holder">
                                            <div class="columns" style="margin-left:2px;" id="desorption-chart"></div>
                                        </div>
                                        <br>
                                    </div>
                                </b-collapse>
                            </section>
                            <!-- End of Desorption collapsable -->
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


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from 'vuex'
import Buefy from "buefy";

import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';

Vue.use([Buefy]);

var Plotly = require('plotly.js-dist');
var _ = require('underscore');

export default {
    name: "TOFControl",
    components: {
    },
    props: [
    ],
    computed: {
        ...mapState([
            'instrument_status',
        ]),
        acquisition_control_active: {
            get() {
                return this.$store.state.acquisition_control_active;
            },
            set(value) {
                this.$store.commit('acquisition_control_active', value);
            }
        },
        acquisition_status: {
            get() {
                return this.$store.state.acquisition_status;
            },
            set(value) {
                this.$store.commit('acquisition_status', value);
            }
        },
        acquisition_progress() {
            return this.$store.state.acquisition_progress.progress;
        },
        sample_length: {
            get() {
                return this.$store.state.sample_length;
            },
            set(value) {
                this.$store.commit('sample_length', value);
            }
        },
    },
    data: function() {
        return {
            is_edit_temperature_ramp_modal_active: false,
            // variable for acquisition button style  and progress bar
            acquisition_button_type: "is-primary",
            // variables for desoprtion collapsable
            acquisition_mode: "continuous",
            time: "",
            temperature: "",
            edit_dialog_time: "",
            edit_dialog_temperature: "",
            show_add_new_row: false,
            // variables for desorption table
            desorption_table_data: [],
            desorption_table_columns: [],
            desorption_table_selected_rows: [],
            desorption_table_selected_row: null,
            desorption_table_checked_rows: [],
            desorption_data: [],
            // variables for acquisitions status
            scenthound_status: "Offline",       // Offline/Ready/Measuring.../Processing...
            acquisition_control_label: "Start Acquisition",
            config_file_data: null,
            // flag to separate if data was changed by user or by loading
            // config file in the 
            data_updated_from_loading: true,
            }
    },
    created: function() {
    },
    mounted: function() {
    },
    methods: {
        confirmAcquisitionControl() {
            this.$buefy.dialog.confirm({
                title: 'Instrument control',
                message: `You have requested access to instrument controls.
                          Please proceed only if you know what you are doing.`,
                cancelText: 'Cancel',
                confirmText: 'Proceed',
                type: 'is-danger',
                onCancel: () => this.acquisition_control_active = false,
                onConfirm: () => this.$buefy.toast.open('Instrument control granted')
            })
        },
        delete_row_in_config_desorption_table() {
            var delete_index = 0;
            for (var i = 0; i < this.desorption_table_data.length; i++) {
                if (this.desorption_table_data[i].time == this.desorption_table_selected_row.time && this.desorption_table_data[i].temperature == this.desorption_table_selected_row.temperature) {
                    delete_index = i;
                }
            }
            this.desorption_table_data.splice(delete_index, 1);
            this.save_all_values_to_configuration_file();
        },
        
        draw_desorption_chart() {
            var self = this;
            // format the data and draw the chart
            var x = [];
            var y = [];
            var max_time_length = 0;
            var max_time_temp_value = 0;
            for (var xx = 0; xx < this.desorption_table_data.length; xx++) {
                if (this.desorption_table_data[xx].time > max_time_length) {
                    max_time_length = this.desorption_table_data[xx].time;
                    max_time_temp_value = this.desorption_table_data[xx].temperature;
                }
                x.push(this.desorption_table_data[xx].time);
                y.push(this.desorption_table_data[xx].temperature);
            }
            if (max_time_length < this.sample_length) {
                x.push(this.sample_length);
                y.push(max_time_temp_value);
            }
            this.desorption_data[0].x = x;
            this.desorption_data[0].y = y;
            var layout = desorption_chart_layout;
            layout.width = 0.23 * screen.width;
            var config = {
                responsive: false
            }
            Plotly.react("desorption-chart", self.desorption_data, layout, config);
        },
        edit_row_in_config_desorption_table() {
            var selected_time_for_edit = this.desorption_table_selected_row.time;
            var selected_temperature_for_edit = this.desorption_table_selected_row.temperature;

            for (var i = 0; i < this.desorption_table_data.length; i++) {
                if (parseInt(this.desorption_table_data[i].time) == parseInt(selected_time_for_edit) && parseInt(this.desorption_table_data[i].temperature) == parseInt(selected_temperature_for_edit)) {
                    this.desorption_table_data[i].time = this.edit_dialog_time;
                    this.desorption_table_data[i].temperature = this.edit_dialog_temperature;
                    break;
                }
            }
            this.is_edit_temperature_ramp_modal_active = false;
            this.save_all_values_to_configuration_file();
        },
        on_button_change_acquisition_status() {
            let next_status = {"not_running": "starting",
                               "starting": "stopping",
                               "running": "stopping",
                               "stopping": "stopping"};
            this.acquisition_status = next_status[this.acquisition_status];
        },
        save_all_values_to_configuration_file() {
            // Before saving the desorption table data sort i
            var self = this;
            self.desorption_table_data = self.desorption_table_data.sort(function(a, b) {
                return a.time - b.time;
            });
            var checked_indexes = [];
            for (var i = 0; i < self.desorption_table_data.length; i++) {
                for (var j = 0; j < self.desorption_table_checked_rows.length; j++) {
                    if (self.desorption_table_checked_rows[j].time === self.desorption_table_data[i].time &&
                        self.desorption_table_checked_rows[j].temperature === self.desorption_table_data[i].temperature) {
                        checked_indexes.push(i);
                    }
                }
            }
            var new_configurations = {
                "AcquisitonParameters": {
                    "acquisition_mode": self.acquisition_mode,
                    "sample_length": parseInt(self.sample_length),
                },
                "DesorptionTemperatureRamp": {
                    "data": self.desorption_table_data,
                    "checked_rows": checked_indexes
                },
                "desorption_table_columns": self.desorption_table_columns,
                "desorption_data": self.desorption_data,
            };
            self.write_to_config_file(JSON.stringify(new_configurations, null, 3));
        },
        save_new_row_in_config_desorption_table() {
            // validate data first
            if (this.time == "" || this.temperature == "") {
                this.display_notification("The values entered are invalid.", "is-black");
                return false;
            }
            if (parseInt(this.time) > parseInt(this.sample_length)) {
                this.display_notification("Entered time cannot be greater than sample length, Either lower time value or Increase the sample length", "is-black");
                return false;
            }
            this.desorption_table_data.push({
                "time": this.time,
                "temperature": this.temperature
            });
            this.save_all_values_to_configuration_file();
            this.time = "";
            this.temperature = "";
            this.show_add_new_row = false;
        },
        show_desorption_edit_modal() {
            if (this.desorption_table_selected_row != null) {
                this.edit_dialog_time = this.desorption_table_selected_row.time;
                this.edit_dialog_temperature = this.desorption_table_selected_row.temperature;
                this.is_edit_temperature_ramp_modal_active = true;
            }
        },
    },
    watch: {
        acquisition_control_active: function(new_value) {
            if (new_value) {
                this.confirmAcquisitionControl();
            }
        },
        acquisition_mode: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            if (this.data_updated_from_loading == false) {
                // this.save_all_values_to_configuration_file();
                return // TODO: is there something to do
            }
        },
        acquisition_status: function(new_value, old_value){
            if (new_value === old_value) {
                return false;
            }
            if(new_value === "starting"){
                this.acquisition_control_label = "Starting Acquisition";
                this.acquisition_button_type = "is-danger";
            }
            if(new_value === "stopping"){
                this.acquisition_control_label = "Stopping Acquisition";
                this.acquisition_button_type = "is-danger";
                this.scenthound_status = 'Processing...';
            }
            if(new_value === "running"){
                this.sample_table_checked_rows = [];
                this.acquisition_control_label = "Stop Acquisition";
                this.acquisition_button_type = "is-danger";
                this.scenthound_status = 'Measuring...';
            }
            if(new_value === "not_running"){
                this.acquisition_control_label = "Start Acquisition";
                this.acquisition_button_type = "is-primary";
                this.scenthound_status = 'Ready';
            }
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
    }
};

var desorption_chart_layout = {
    "width": 280,
    "height": 280,
    "legend": {
        "y": 0.5,
        "font": {
            "size": 10
        },
        "traceorder": "reversed",
        "color": "#fff"
    },
    "font": {
        "color": "#fff"
    },
    "xaxis": {
        "visible": true,
        "linecolor": "#999",
        "tickmode": "linear",
        "tick0": 0,
        "dtick": 20
    },
    "yaxis": {
        "visible": true,
        "linecolor": "#999",
        "tickmode": "linear",
        "tick0": 0,
        "dtick": 10,
        "gridcolor": "#676565"
    },
    "showlegend": false,
    "commented_out__dragmode": "select",
    "commented_out__autosize": false,
    "commented_out__autoscale": false,
    "hovermode": "closest",
    "plot_bgcolor": "#29282e",
    "paper_bgcolor": "#29282e",
    "margin": {
        "l": 30,
        "r": 20,
        "b": 25,
        "t": 60,
        "pad": 0
    }
};

</script>

<style src = "../assets/css/MeasurementTab.css"> </style>