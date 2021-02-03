<template>
    <div>
<!-- Modals -->
        <!-- Modal for sample attributes -->
        <section class="sample-attribute-modal">
            <b-modal :active.sync="is_sample_attribute_modal_active"
                has-modal-card
                trap-focus
                :can-cancel="false"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">{{ sample_file }}</p>
                        </header>
                        <section class="modal-card-body write_sample_attribute">
                            
                            <b-field label="Sample title">
                                <b-input type="input"
                                    v-model="sample_name"
                                    :value="sample_name"
                                    maxlength="50">
                                </b-input>
                            </b-field>

                            <b-field label="Description">
                                <b-input
                                    v-model="sample_description"
                                    :value="sample_description"
                                    maxlength="200"
                                    type="textarea">
                                </b-input>
                            </b-field>

                            <b-field label="Project">
                                <b-select
                                    placeholder="Select a project"
                                    v-model="sample_project"
                                    required
                                    expanded>
                                    <option
                                        v-for="p in projects"
                                        :value="p.id"
                                        :key="p.id">
                                        {{ p.id }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    v-model="sample_experiment"
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments"
                                        :value="e.id"
                                        :key="e.id">
                                        {{ e.id }}
                                    </option>
                                </b-select>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                @click="write_sample_attributes"
                                is-dark>
                                Save
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_sample_attribute_modal_active=false">
                                Close
                            </button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of Modal for sample edit -->

        <!-- Modal for h5 import -->
        <section class="h5-import-modal">
            <b-modal :active.sync="is_import_h5_modal_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: 500px; height: 700px">
                        <header class="modal-card-head">
                            <p class="modal-card-title">Import h5 files</p>
                        </header>
                        <section class="modal-card-body">
                            <b-field label="Start">
                                <b-datetimepicker
                                    v-model="import_start_time"
                                    placeholder="Start datetime"
                                    :timepicker="{'hour-format': '24'}"
                                    :min-datetime="import_min_datetime"
                                    :max-datetime="import_max_datetime">
                                </b-datetimepicker>
                            </b-field>
                            <b-field label="End">
                                <b-datetimepicker
                                    v-model="import_end_time"
                                    placeholder="End datetime"
                                    :timepicker="{'hour-format': '24'}"
                                    :min-datetime="import_start_time"
                                    :max-datetime="import_max_datetime">
                                </b-datetimepicker>
                            </b-field>
                            <button
                                class="button"
                                type="button"
                                @click="FetchH5s()"
                                is-dark
                                :disabled="(h5_streamer_status==='not_ready' ||
                                            import_start_time === null ||
                                            import_end_time === null
                                            ) ? true : false">
                                Fetch h5 list
                            </button>
                            <div><br></div>
                            <b-table 
                                id="h5-samples-table"
                                :columns="import_h5_table_cols"
                                :data="import_h5_table_rows"
                                :checkable="true"
                                :checked-rows.sync="import_h5_table_checked_rows">
                            </b-table>
                            <div><br></div>
                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                @click="ImportH5s()"
                                is-dark
                                :disabled="(!import_h5_table_checked_rows.length ||
                                            import_start_time === null ||
                                            import_end_time === null
                                            ) ? true : false">
                                Import
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_import_h5_modal_active=false">
                                Cancel
                            </button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of h5 import modal -->

        <!-- Modal for sample import -->
        <section class="sample-import-modal">
            <b-modal :active.sync="is_import_sample_modal_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: 500px; height: 700px">
                        <header class="modal-card-head">
                            <p class="modal-card-title">Import samples</p>
                        </header>
                        <section class="modal-card-body">
                            <b-table 
                                id="import-sample-table"
                                :columns="import_sample_table_cols"
                                :data="import_sample_table_rows"
                                :checkable="true"
                                :header-checkable="false"
                                :checked-rows.sync="import_sample_table_checked_rows">
                            </b-table>
                            <div><br></div>
                        </section>
                        <footer class="modal-card-foot">
                            <button
                                class="button"
                                type="button"
                                @click="ImportSamples()"
                                is-dark
                                :disabled="!import_sample_table_checked_rows.length">
                                Import
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_import_sample_modal_active=false">
                                Cancel
                            </button>
                        </footer>
                    </div>
                </div>
            <b-loading
                :is-full-page="false"
                v-model="import_sample_table_loading">
            </b-loading>
            </b-modal>
        </section>
        <!-- End of sample import modal -->
<!-- End of modals -->

<!-- Main content area -->
        <section>
            <!-- Samples datatable collapsable -->
            <section>
                <b-collapse class="card" animation="slide" aria-id="contentIdForA11y3">
                    <div
                        slot="trigger" 
                        slot-scope="props"
                        class="card-header"
                        role="button"
                        aria-controls="contentIdForA11y3">
                        <p class="card-header-title">
                            Samples
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
                                    @click="is_sample_attribute_modal_active=true"
                                    outlined
                                    inverted
                                    size="is-small">
                                    Sample attributes
                                </b-button>
                                <div><br></div>
                                <b-table 
                                    id="samples-datatable"
                                    :columns="sample_table_cols"
                                    :data="sample_table_rows"
                                    :checkable="(//!acquisition_control_active ||
                                                    acquisition_status=='not_running') ? true : false"
                                    :header-checkable="false"
                                    :checked-rows.sync="sample_table_checked_rows">
                                </b-table>
                                <div><br></div>
                                <b-button
                                    type="is-dark"
                                    @click="LaunchSampleImport()"
                                    size="is-small"
                                    outlined
                                    inverted>
                                    Import sample
                                </b-button>
                                <b-button
                                    type="is-dark"
                                    @click="is_import_h5_modal_active=true"
                                    size="is-small"
                                    outlined
                                    inverted
                                    :disabled="(h5_streamer_status=='ready' && 
                                                (//!acquisition_control_active ||
                                                    acquisition_status=='not_running')
                                                ) ? false : true">
                                    Import h5 file
                                </b-button>
                            </div>
                        </div>
                    </div>
                </b-collapse>
            </section>
            <!-- End of Sample datatable collapable -->
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

var _ = require('underscore');

export default {
    name: "SampleBrowser",
    components: {
    },
    props: {
    },
    computed: {
        ...mapState([
            'acquisition_started',
            'acquisition_status',
            'experiments',
            'experiment_selected',
            'h5_samples',
            'h5_streamer_status',
            'importable_samples',
            'projects',
            'project_selected',
            'samples',
        ]),
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
        sample_attributes: {
            get() {
                return this.$store.state.sample_attributes;
            },
            set(value) {
                this.$store.commit('sample_attributes', value);
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
    },
    data: function() {
        return {
            is_import_sample_modal_active: false,
            is_import_h5_modal_active: false,
            is_sample_attribute_modal_active: false,
            // variables for import modals
            import_start_time: null,
            import_end_time: null,
            import_min_datetime: null,
            import_max_datetime: new Date(),
            // variables for sample import modal
            import_sample_table_loading: true,
            import_sample_table_rows: [],
            import_sample_table_cols: [],
            import_sample_table_checked_rows: [],
            // variables for h5 import modal
            import_h5_table_rows: [],
            import_h5_table_cols: [],
            import_h5_table_checked_rows: [],
            // Sample metadata for selected sample
            sample_file: "",
            sample_name: "",
            sample_description: "",
            sample_project: "",
            sample_experiment: "",
            // variables for sample table
            sample_table_rows: [],
            sample_table_cols: [],
            sample_table_checked_rows: [],
            }
    },
    created: function() {
    },
    mounted: function() {
    },
    methods: {
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
        LaunchSampleImport() {
            // Request list of samples from FileService
            this.import_sample_table_datetime_range = Math.random();
            // Set loading state
            this.import_sample_table_loading = true;
            // Launch modal
            this.is_import_sample_modal_active = true;
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
    },
    watch: {
        acquisition_started: function(new_value, old_value) {
            // if (!this.acquisition_control_active) {
            //     return
            // }
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
            this.import_sample_table_loading = false;
        },
        samples: function(new_data, old_data){
            if ( _.isEqual(new_data, old_data) ) {
                return false;
            }
            this.sample_table_cols = new_data.cols;
            this.sample_table_rows = new_data.rows;
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
};


</script>

<style src = "../assets/css/MeasurementTab.css"> </style>