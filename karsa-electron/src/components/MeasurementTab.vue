<template src = "../templates/MeasurementTab.vue"></template>

<script type = "text/javascript" >
"use strict";

import Vue from "vue";
import { mapState } from 'vuex';
import Buefy from "buefy";
import Multiselect from "vue-multiselect";
import SampleView from "./SampleView.vue"
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';

Vue.use([Buefy]);

var fs = require('fs');
// var path = require('path');
// var dialog = require("electron").remote.dialog;
var Plotly = require('plotly.js-dist');
// var remote = require('electron').remote;
// var dot_env_vars = remote.getGlobal('dot_env_vars');
var _ = require('underscore');

export default {
    name: "MeasurementTab",
    components: {
        // using third party multiselect component
        Multiselect,
        SampleView
    },
    props: {
        msg: String
    },
    data() {
        return {
            // variables for modal / Popup boxes
            is_edit_temperature_ramp_modal_active: false,
            is_sample_attribute_modal_active: false,
            is_import_h5_modal_active: false,
            is_import_sample_modal_active: false,
            // variables for desoprtion collapsable
            acquisition_mode: "triggered",
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
            // variables for sample table
            sample_table_rows: [],
            sample_table_cols: [],
            sample_table_checked_rows: [],
            // Target table 
            target_table_rows: [],
            target_table_cols: [],
            target_table_checked_rows: [],
            // Sample metadata for selected sample
            sample_file: "",
            sample_name: "",
            sample_description: "",
            sample_project: "",
            sample_experiment: "",
            // variables for acquisitions status
            scenthound_status: "Offline",       // Offline/Ready/Measuring.../Processing...
            acquisition_control_label: "Start Acquisition",
            config_file_data: null,
            // flag to separate if data was changed by user or by loading
            // config file in the 
            data_updated_from_loading: true,
            // data read and write path
            data_read_path: "",
            data_read_path_recursive: true,
            // variable for acquisition button style  and progress bar
            acquisition_button_type: "is-primary",
            // variables for import modals
            import_start_time: null,
            import_end_time: null,
            import_min_datetime: null,
            import_max_datetime: new Date(),
            // variables for sample import modal
            import_sample_table_rows: [],
            import_sample_table_cols: [],
            import_sample_table_checked_rows: [],
            // variables for h5 import modal
            import_h5_table_rows: [],
            import_h5_table_cols: [],
            import_h5_table_checked_rows: [],
        }
    },
    computed: {
        widthSize(col) {
            if (col.id == 1) return '274px';
            return 'unset' / 'auto';
        },
        ...mapState([
                    'acquisition_started',
                    'experiments',
                    'experiment_selected',
                    'figure_ranges',
                    'h5_samples',
                    'h5_streamer_status',
                    'importable_samples',
                    'instrument_status',
                    'projects',
                    'project_selected',
                    'samples',
                    'targets',
                    ]),
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
        import_h5_table_datetime_range: {
            get() {
                return this.$store.state.import_h5_table_datetime_range;
            },
            set(value) {
                this.$store.commit('import_h5_table_datetime_range', value);
            }
        },
        import_sample_table_datetime_range: {
            get() {
                return this.$store.state.import_sample_table_datetime_range;
            },
            set(value) {
                this.$store.commit('import_sample_table_datetime_range', value);
            }
        },
        h5_to_import: {
            get() {
                return this.$store.state.h5_to_import;
            },
            set(value) {
                this.$store.commit('h5_to_import', value);
            }
        },
        sample_length: {
            get() {
                return this.$store.state.sample_length;
            },
            set(value) {
                this.$store.commit('sample_length', value);
            }
        },
        sample_to_load: {
            get() {
                return this.$store.state.sample_to_load;
            },
            set(value) {
                this.$store.commit('sample_to_load', value);
            }
        },
        target_to_load: {
            get() {
                return this.$store.state.target_to_load;
            },
            set(value) {
                this.$store.commit('target_to_load', value);
            }
        },
        sample_attributes: {
            get() {
                return this.$store.state.sample_attributes;
            },
            set(value) {
                this.$store.commit('sample_attributes', value);
            }
        },
   },

    mounted: function() {
        // Hacky trick to use label instead of select all checkbox input in data table
        var self = this;
        // TODO: What do we need from nextTick after we moved away watch part from the mounted section?
        self.$nextTick(async function() {
            await self.init_layout_templates().then(function() {
                //
            });
            await self.read_config_and_init_ui().then(function() {
                self.data_updated_from_loading = false;
                var t = document.getElementsByClassName("desorption-temperature-ramp-table");
                try {
                    t[0]["children"][0]["children"][0]["children"][0]["children"][0]["children"][2].innerHTML = "Filters";
                } catch (e) {
                    console.log(e);
                }
            });
        });
    },
    created: function() {
    },
    methods: {
        log: function(...args) {
            console.log('[' + this.$options.name + ']',  ...args);
        },

        async init_layout_templates() {
            try {
                if (fs.existsSync('configs/measurementtab_config.json')) {
                    var measurementtab_layout = JSON.parse(fs.readFileSync('configs/measurementtab_config.json', 'utf8'));
                    this.desorption_table_columns = measurementtab_layout.desorption_table_columns || [];
                    this.desorption_data = measurementtab_layout.desorption_data || [];
                }
            } catch (err) {
                console.error(err)
            }
        },
        
        display_notification(msg, type = "is-success") {
            this.$buefy.notification.open({
                message: msg,
                type: type,
                duration: 5000,
                position: 'is-bottom-right',
            })
        },
        
        show_desorption_edit_modal() {
            if (this.desorption_table_selected_row != null) {
                this.edit_dialog_time = this.desorption_table_selected_row.time;
                this.edit_dialog_temperature = this.desorption_table_selected_row.temperature;
                this.is_edit_temperature_ramp_modal_active = true;
            }
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
        
        async read_config_and_init_ui() {
            try {
                if (fs.existsSync('configs/measurementtab_config.json')) {
                    var measurementtab_config = JSON.parse(fs.readFileSync('configs/measurementtab_config.json', 'utf8'));
                    this.acquisition_mode = measurementtab_config.AcquisitonParameters.acquisition_mode;
                    this.sample_length = measurementtab_config.AcquisitonParameters.sample_length;

                    var data = measurementtab_config.DesorptionTemperatureRamp.data;
                    this.desorption_table_data = data.sort(function(a, b) {
                        return a.time - b.time;
                    });

                    this.desorption_table_checked_rows = [];
                    for (var j = 0; j < measurementtab_config.DesorptionTemperatureRamp.checked_rows.length; j++) {
                        this.desorption_table_checked_rows.push(this.desorption_table_data[measurementtab_config.DesorptionTemperatureRamp.checked_rows[j]]);
                    }
                    this.draw_desorption_chart()
                }
            } catch (err) {
                console.error(err)
            }
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
        
        write_to_config_file(data) {
            fs.writeFileSync('configs/measurementtab_config.json', data);
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
            var layout = JSON.parse(fs.readFileSync('configs/desorption_chart_layout.json'));
            layout.width = 0.23 * screen.width;
            var config = {
                responsive: false
            }
            Plotly.react("desorption-chart", self.desorption_data, layout, config);
        },
        
        on_button_change_acquisition_status() {
            let next_status = {"not_running": "starting",
                               "starting": "stopping",
                               "running": "stopping",
                               "stopping": "stopping"};
            this.acquisition_status = next_status[this.acquisition_status];
        },
        
        write_sample_attributes: function() {
            if ( !(this.sample_project.length && this.sample_experiment.length) ) {
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "Project and experiment must be selected to store sample attributes.",
                    type: 'is-danger'
                })
                return
            }
            let sample = {
                'id': this.sample_file,
                'attributes': {
                    'title': this.sample_name,
                    'description': this.sample_description,
                    'project': this.sample_project,
                    'experiment': this.sample_experiment
                    }
            };
            this.sample_attributes = sample;
            this.is_sample_attribute_modal_active = false;
        },
        FetchH5s() {
            if (this.import_start_time == null || 
                this.import_end_time == null) {
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "You must select datetime range first!",
                    type: 'is-danger',
                    queue: false,
                })
                return
            }
            // Revert automatic timezone adjustment
            let dt0 = new Date(this.import_start_time.getTime()); // copy
            let start_hours_diff = dt0.getHours() - dt0.getTimezoneOffset() / 60;
            dt0.setHours(start_hours_diff);

            let dt1 = new Date(this.import_end_time.getTime()); // copy
            let end_hours_diff = dt1.getHours() - dt1.getTimezoneOffset() / 60;
            dt1.setHours(end_hours_diff);
            
            // Request list of h5 files in given range
            let fetch_request = {
                'dt0': dt0.toJSON(),
                'dt1': dt1.toJSON()
            }
            this.import_h5_table_datetime_range = fetch_request;
        },
        FetchSamples() {
            if (this.import_start_time == null || 
                this.import_end_time == null) {
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "You must select datetime range first!",
                    type: 'is-danger',
                    queue: false,
                })
                return
            }
            // Revert automatic timezone adjustment
            let dt0 = new Date(this.import_start_time.getTime()); // copy
            let start_hours_diff = dt0.getHours() - dt0.getTimezoneOffset() / 60;
            dt0.setHours(start_hours_diff);

            let dt1 = new Date(this.import_end_time.getTime()); // copy
            let end_hours_diff = dt1.getHours() - dt1.getTimezoneOffset() / 60;
            dt1.setHours(end_hours_diff);
            
            // Request list of h5 files in given range
            let fetch_request = {
                'dt0': dt0.toJSON(),
                'dt1': dt1.toJSON()
            }
            this.import_sample_table_datetime_range = fetch_request;
        },
        ImportH5s() {
            this.h5_to_import = this.import_h5_table_checked_rows;
            this.is_import_h5_modal_active = false;
        },
        ImportSamples() {
            let to_import = this.import_sample_table_checked_rows[0];
            // Preserve sample id, title and description
            // Set project and experiment to the selected ones
            let sample = {
                'id': to_import.id,
                'attributes': {
                    'title': to_import.title,
                    'description': to_import.description,
                    'project': this.project_selected.id,
                    'experiment': this.experiment_selected.id
                    }
                };
            // Export sample attributes to link into current experiment
            this.sample_attributes = sample;
            this.is_import_sample_modal_active = false;
        },
        
    },
    watch: {
        acquisition_mode: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            if (this.data_updated_from_loading == false) {
                this.save_all_values_to_configuration_file();
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
        acquisition_started: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            this.sample_file = new_value.filename;
            let sample_no = this.sample_table_rows.length + 1;
            this.sample_name = sample_no.toString().padStart(3, '0') + '_';
            this.sample_description = "";
            this.is_sample_attribute_modal_active = true;
        },
        h5_table_checked_rows: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            var last_selection = [...new_value].pop();
            // force single row selection
            if ( this.h5_table_checked_rows.length > 1 ) {
                this.h5_table_checked_rows = [last_selection,];
            }
        },
        h5_samples: function(new_data, old_data){
            if ( _.isEqual(new_data, old_data) ) {
                return false;
            }
            this.import_h5_table_cols = new_data.cols;
            this.import_h5_table_rows = new_data.rows;
        },
        import_sample_table_checked_rows: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            var last_selection = [...new_value].pop();
            // force single row selection
            if ( this.import_sample_table_checked_rows.length > 1 ) {
                this.import_sample_table_checked_rows = [last_selection,];
            }
        },
        importable_samples: function(new_data, old_data){
            if ( _.isEqual(new_data, old_data) ) {
                return false;
            }
            for (let i=0; i<new_data.cols.length; i++) {
                new_data.cols[i]['searchable'] = true;
            }
            this.import_sample_table_cols = new_data.cols;
            this.import_sample_table_rows = new_data.rows;
        },
        samples: function(new_data, old_data){
            if ( _.isEqual(new_data, old_data) ) {
                return false;
            }
            this.sample_table_cols = new_data.cols;
            this.sample_table_rows = new_data.rows;
        },
        sample_length: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            if (this.data_updated_from_loading === false) {
                this.save_all_values_to_configuration_file();
            }
        },
        sample_table_checked_rows: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            var last_selection = [...new_value].pop();

            // sample_table_checked_rows manipulates multi-row selection,
            // but by design limitation, it should be a single row selection
            if ( this.sample_table_checked_rows.length > 1 ) {
                this.sample_table_checked_rows = [last_selection,];
            }

            // TODO: clean up figures
            // check if the vuex props should be mapped to local props
            this.$store.commit('heatmap_figure_data', {});
            this.$store.commit('timeseries_figure_data', {});
            this.$store.commit('tps_parameters_selected', []);
            this.$store.commit('tps_parameters', []);
            this.$store.commit('spec_stack_figure_data', {});

            if (last_selection) {
                this.sample_file = last_selection.id;
                this.sample_name = last_selection.title;
                this.sample_description = last_selection.description;
                this.sample_project = last_selection.project;
                this.sample_experiment = last_selection.experiment;
                this.sample_to_load = {'filename': this.sample_file};
            } else {
                this.sample_to_load = {'filename': ""};
            }
        },
        target_table_checked_rows:function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            var last_selection = [...new_value].pop();
            if ( this.selected_target_table_rows.length > 1 ) {
                this.selected_target_table_rows = [last_selection,];
            }
            // TODO: check if the vuex prop should be mapped to local props
            this.target_to_load = [last_selection, ];
        },
        targets: function(new_data, old_data){
            if ( _.isEqual(new_data, old_data) ) {
                return false;
            }
            this.target_table_cols = new_data.cols;
            this.target_table_rows = new_data.rows;
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
        project_selected: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            this.sample_project = new_value.id;
        },
        experiment_selected: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            this.sample_experiment = new_value.id;
        },
    }
}
</script>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"> </style>
<style src = "../assets/css/MeasurementTab.css"> </style>