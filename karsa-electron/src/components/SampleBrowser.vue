<template>
    <div>
    <!-- Modals -->
        <!-- Landing modal -->
        <section class="landing-modal">
            <b-modal :active.sync="is_landing_modal_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="false"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">
                                Select project and experiment
                            </p>
                        </header>
                        <section class="modal-card-body">
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

                            <b-button
                                expanded
                                @click="LaunchNewProjectModal()">
                                New Project
                            </b-button>

                            <div><br></div>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    v-model="sample_experiment"
                                    :disabled="!sample_project"
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments_ui"
                                        :value="e.id"
                                        :key="e.id">
                                        {{ e.id }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-button
                                expanded
                                @click="LaunchNewExperimentModal()"
                                :disabled="!sample_project">
                                New Experiment
                            </b-button>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                @click="is_landing_modal_active=false"
                                is-dark
                                :disabled="!(sample_project.length && sample_experiment.length)">
                                Proceed
                            </b-button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>     
        <!-- End of landing modal -->
        <!--- New project modal--> 
        <section class="project-attribute-modal">
            <b-modal :active.sync="is_modal_new_project_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px">
                    <!-- Main content -->
                    <div class="columns">
                        <!-- Left side -->
                        <div class="column">
                            <header class="modal-card-head">
                                <p class="modal-card-title">
                                    New project
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <b-field label="Project title">
                                    <b-input type="input"
                                        v-model="project.title"
                                        :value="project.title"
                                        maxlength="50"
                                        required
                                        validation-message="Only numbers, letters and _ allowed in the title"
                                        :pattern="valid_pattern.toString().slice(1, -1)">
                                    </b-input>
                                </b-field>
                                <b-field label="Description">
                                    <b-input
                                        v-model="project.description"
                                        :value="project.description"
                                        maxlength="200"
                                        type="textarea">
                                    </b-input>
                                </b-field>
                            </section>
                        </div>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <button
                            class="button"
                            type="button"
                            @click="SetProject()"
                            is-dark>
                            Create
                        </button>
                        <button
                            class="button"
                            type="button"
                            is-dark
                            @click="CancelNewProject()">
                            Cancel
                        </button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of new project modal--> 

        <!--- New experiment modal--> 
        <section class="experiment-attribute-modal">
            <b-modal :active.sync="is_modal_new_experiment_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal
            >
                <div class="modal-card" style="width: 500px">
                    <div class="columns">
                        <div class="column">
                            <header class="modal-card-head">
                                <p class="modal-card-title">
                                    New experiment
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <!-- <b-field label="Experiment title">
                                    <b-input type="input"
                                        v-model="experiment.title"
                                        :value="experiment.title"
                                        maxlength="50"
                                        required
                                        validation-message="Only numbers, letters and _ allowed in the title"
                                        :pattern="valid_pattern.toString().slice(1, -1)">
                                    </b-input>
                                </b-field> -->
                                <!-- <b-field label="Description">
                                    <b-input 
                                        v-model="experiment.description" 
                                        :value="experiment.description"
                                        maxlength="200" 
                                        type="textarea">
                                    </b-input>
                                </b-field> -->
                                <MetaDataForm
                                    form_title="Experiment attributes"
                                    :default_template="experiment_attributes_default_template"
                                    :editable="true"
                                    :template_path="experiment_attributes_template_path">
                                </MetaDataForm>
                                <div><br></div>
                                <MetaDataForm
                                    form_title="Sample attribute template"
                                    :default_template="sample_attributes_default_template"
                                    :editable="true"
                                    :template_path="sample_attributes_template_path">
                                </MetaDataForm>
                            </section>
                        </div>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <button 
                            class="button" 
                            type="button" 
                            @click="SetExperiment" 
                            is-dark>
                            Create
                        </button>
                        <button 
                            class="button" 
                            type="button" 
                            is-dark 
                            @click="CancelNewExperiment">
                            Cancel
                        </button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of new experiment modal-->

        <!-- Modal for sample attributes -->
        <section class="sample-attribute-modal">
            <b-modal :active.sync="is_sample_attribute_modal_active"
                has-modal-card
                trap-focus
                :can-cancel="false"
                :destroy-on-hide="true"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">{{ sample_file }}</p>
                        </header>
                        <section class="modal-card-body write_sample_attribute">                            
                            
                            <MetaDataForm
                                form_title="Sample attributes"
                                :default_template="sample_attributes_default_template"
                                :initial_template="sample_attributes_template"
                                :template_path="sample_attributes_template_path"
                                @metaDataUpdated="sample_attributes_fields=$event">
                            </MetaDataForm>

                            <div><br></div>
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
                                        v-for="e in experiments_ui"
                                        :value="e.id"
                                        :key="e.id">
                                        {{ e.id }}
                                    </option>
                                </b-select>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                :type="sample_attributes_save_button_type"
                                @click="write_sample_attributes"
                                is-dark
                                :disabled="!sample_title.length">
                                Save
                            </b-button>
                            <b-button
                                @click="is_sample_attribute_modal_active=false">
                                Close
                            </b-button>
                            <div style="position:absolute; right:20px">
                                <b-tooltip
                                    label="Remove sample from this experiment"
                                    position="is-left"
                                    :delay="1000">
                                    <b-button
                                        type="is-danger"
                                        icon-left="delete"
                                        @click="remove_sample">
                                    </b-button>
                                </b-tooltip>
                            </div>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of Modal for sample edit -->

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
                                <!-- Sample browser tree -->
                                <b-menu>
                                    <!-- Projects -->
                                    <b-menu-list label="Projects">
                                        <!-- Project item -->
                                        <b-menu-item
                                            v-for="p in projects"
                                            :key="p.id"
                                            :active.sync="p.active"
                                            :expanded.sync="p.active"
                                            @click="project.title=p.id; SetProject()">
                                            <template #label>
                                                {{p.id}}
                                            </template>
                                            <!-- Experiments -->
                                            <b-menu-list
                                                label="Experiments"
                                                v-if="p.id === project_selected.id">
                                                <!-- Experiment item -->
                                                <b-menu-item 
                                                    v-for="e in experiments_ui"
                                                    :key="e.id"
                                                    :active.sync="e.active"
                                                    :expanded.sync="e.active"
                                                    @click="experiment.title=e.id; SetExperiment()">
                                                    <template #label>
                                                        {{e.id}}
                                                    </template>
                                                    <p class="menu-label">
                                                        Samples
                                                    </p>
                                                    <!-- Sample table -->
                                                    <b-table 
                                                        id="samples-datatable"
                                                        style="height:100%; width:100%"
                                                        :data="sample_table_rows"
                                                        :sticky-header="true"
                                                        :checkable="true"
                                                        :header-checkable="false"
                                                        :checked-rows.sync="sample_table_checked_rows"
                                                        detailed
                                                        detail-key="title"
                                                        :show-detail-icon="false"
                                                        v-if="e.id === experiment_selected.id">
                                                        <!-- Columns -->
                                                        <b-table-column field="title" label="" v-slot="props">
                                                            <a @click="props.toggleDetails(props.row)">
                                                                {{ props.row.title }}
                                                            </a>
                                                        </b-table-column>
                                                        <!-- End of columns -->
                                                        <!-- Details view -->
                                                        <template #detail="props">
                                                            <div>
                                                                <p>
                                                                    <strong>{{ props.row.title }}</strong>
                                                                    <br>
                                                                    {{ props.row.description }}
                                                                    <br>
                                                                    <small style="color: #ababab;">{{ props.row.id }}</small>
                                                                </p>
                                                                <b-button
                                                                    type="is-dark"
                                                                    @click="LaunchSampleAttributeModal(props.row)"
                                                                    outlined
                                                                    size="is-small">
                                                                    Edit
                                                                </b-button>
                                                            </div>
                                                        </template>
                                                        <!-- End of details view -->
                                                    </b-table>
                                                    <!-- End of sample table -->
                                                    <!-- Import sample item -->
                                                    <b-menu-item
                                                        icon="plus"
                                                        :active="is_import_sample_modal_active"
                                                        @click="LaunchSampleImport()">
                                                    </b-menu-item>
                                                    <!-- End of import sample item -->
                                                </b-menu-item>
                                                <!-- End of experiment item -->
                                                <!-- New experiment item -->
                                                <b-menu-item
                                                    icon="plus"
                                                    :active="is_modal_new_experiment_active"
                                                    @click="LaunchNewExperimentModal()">
                                                </b-menu-item>
                                                <!-- End of new experiment item -->
                                            </b-menu-list>
                                            <!-- End of experiments -->
                                        </b-menu-item>
                                        <!-- End of project item -->
                                        <!-- New project item -->
                                        <b-menu-item
                                            icon="plus"
                                            :active="is_modal_new_project_active"
                                            @click="LaunchNewProjectModal()">
                                        </b-menu-item>
                                        <!-- End of new project item -->
                                    </b-menu-list>
                                    <!-- End of projects -->
                                </b-menu>
                                <!-- End of sample browser tree -->
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
import { BECom } from "../karsalib.js"
import MetaDataForm from "./MetaDataForm.vue"

Vue.use([Buefy]);

var _ = require('underscore');

export default {
    name: "SampleBrowser",
    components: {
        MetaDataForm,
    },
    props: {
    },
    computed: {
        ...mapState([
            // 'h5_samples',
            // 'h5_streamer_status',
            // 'importable_samples',
            'new_file',
            // 'samples',
            'root_namespace',
        ]),

        experiments: {
            get() {
                return this.$store.state.experiments;
            },
            set(value) {
                this.$store.commit('experiments', value);
            }
        },
        experiment_selected: {
            get() {
                return this.$store.state.experiment_selected;
            },
            set(value) {
                this.$store.commit('experiment_selected', value);
            }
        },
        projects: {
            get() {
                return this.$store.state.projects;
            },
            set(value) {
                this.$store.commit('projects', value);
            }
        },
        project_selected: {
            get() {
                return this.$store.state.project_selected;
            },
            set(value) {
                this.$store.commit('project_selected', value);
            }
        },
        sample_annotations: {
            get() {
                return this.$store.state.sample_annotations;
            },
            set(value) {
                this.$store.commit('sample_annotations', value);
            }
        },
        sample_to_display: {
            get() {
                return this.$store.state.sample_to_display;
            },
            set(value) {
                this.$store.commit('sample_to_display', value);
            }
        },
    },
    data: function() {
        return {
            // Communication
            be: null,
            namespace: null,
            room_experiment: null,
            room_project: null,
            room_sid: null,
            endpoints: [
                'experiments',
                'importable_samples',
                'projects',
                'samples',
            ],
            // acquisition_started: false,
            // Project / experiment title validation
            valid_pattern: RegExp(/^\w+$/),
            // Modal active variables
            is_landing_modal_active: true,
            is_modal_new_project_active: false,
            is_modal_new_experiment_active: false,
            is_import_sample_modal_active: false,
            is_sample_attribute_modal_active: false,
            // variables for import modals
            import_start_time: null,
            import_end_time: null,
            import_min_datetime: null,
            import_max_datetime: new Date(),
            // variables for sample import modal
            importable_samples: {},
            import_sample_table_loading: true,
            import_sample_table_rows: [],
            import_sample_table_cols: [],
            import_sample_table_checked_rows: [],
            import_sample_table_datetime_range: {},
            // Project metadata
            project: {
                title: "",
                description: ""
                },
            // Experiment metadata
            experiment_attributes_default_template: [
                {'label': "Experiment title",
                 'value': "",
                 'required': true},
                {'label': "Experiment description",
                 'value': ""},
            ],
            experiment_attributes_template_path: "../metadata_templates/experiment_templates",
            experiments_ui: [],
            experiment: {
                title: "",
                description: ""
                },
            // Sample metadata for selected sample
            samples: [],
            sample_file: "",
            sample_title: "",
            sample_description: "",
            sample_project: "",
            sample_experiment: "",
            // variables for sample table
            sample_table_rows: [],
            sample_table_cols: [],
            sample_table_checked_rows: [],
            sample_attributes: {},
            sample_attributes_default_template: [
                {'label': "Sample title",
                 'value': "",
                 'required': true},
                {'label': "Sample description",
                 'value': ""},
            ],
            sample_attributes_template: this.sample_attributes_default_template,
            sample_attributes_fields: [],
            sample_attributes_save_button_type: "is-success",
            sample_attributes_template_path: "../metadata_templates/sample_templates",
        }
    },
    created: function() {
        this.be = new BECom(this);

    },
    mounted: function() {
    },
    methods: {
        log: function(...args) {
            console.log('[' + this.name + ']',  ...args);
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
        LaunchSampleAttributeModal(sample_table_row) {
            this.sample_file = sample_table_row.id;
            this.sample_title = sample_table_row.title;
            this.sample_description = sample_table_row.description;
            this.sample_attributes_template = [
                {'label': "Sample title",
                 'value': sample_table_row.title},
                {'label': "Sample description",
                 'value': sample_table_row.description},
            ];
            this.is_sample_attribute_modal_active = true;
        },
        LaunchSampleImport() {
            // Request list of samples from FileService
            this.import_sample_table_datetime_range = Math.random();
            // Set loading state
            this.import_sample_table_loading = true;
            // Launch modal
            this.is_import_sample_modal_active = true;
        },
        remove_sample: function() {
            let sample = {
                'id': this.sample_file,
                'attributes': {
                    'remove': true,
                    'project': this.sample_project,
                    'experiment': this.sample_experiment
                    }
            };
            this.sample_attributes = sample;
            this.is_sample_attribute_modal_active = false;
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
                    'title': this.sample_title,
                    'description': this.sample_description,
                    'project': this.sample_project,
                    'experiment': this.sample_experiment
                    }
            };
            this.sample_attributes = sample;
            this.is_sample_attribute_modal_active = false;
        },
        isValidFilename(str) {
            return this.valid_pattern.test(str);
        },

        LaunchNewProjectModal() {
            // Clear fields
            this.project.title = "";
            this.project.description = "";

            this.is_modal_new_project_active = true;
        },

        CancelNewProject() {
            // Reset project
            this.project_selected = {'id': ""};
            this.project.title = "";
            this.project.description = "";
            // Reset experiment
            this.experiment_selected = {'id': ""};
            this.experiment.title = "";
            this.experiment.description = "";

            this.is_modal_new_project_active = false;
        },

        SetProject() {
            if ( !this.isValidFilename(this.project.title) ) {
                // Project title contains illegal characters
                return
            }
            // Find project description
            for (let i in this.projects) {
                if(this.projects[i].id === this.project.title){
                    this.project.description = this.projects[i].attributes.description;
                    this.projects[i].active = true;
                } else {
                    this.projects[i].active = false;
                }
            }
            // Set project_selected
            this.project_selected = {'id': this.project.title,
                                     'attributes': {
                                        'title': this.project.title,
                                        'description': this.project.description
                                        }
                                     };
            // Reset experiment
            this.experiment_selected = {'id': ""};
            this.experiment.title = "";
            this.experiment.description = "";

            this.is_modal_new_project_active = false;
        },

        LaunchNewExperimentModal() {
            // Clear fields
            this.experiment.title = "";
            this.experiment.description = "";

            this.is_modal_new_experiment_active = true;
        },

        CancelNewExperiment() {
            // Reset experiment
            this.experiment_selected = {'id': ""};
            this.experiment.title = "";
            this.experiment.description = "";

            this.is_modal_new_experiment_active = false;
        },

        SetExperiment() {
            if ( !this.isValidFilename(this.experiment.title) ) {
                // Experiment title contains illegal characters
                return
            }
            // Find experiment description
            for (let i in this.experiments_ui) {
                if(this.experiments_ui[i].id === this.experiment.title){
                    this.experiment.description = this.experiments_ui[i].attributes.description;
                    this.experiments_ui[i].active = true;
                } else {
                    this.experiments_ui[i].active = false;
                }
            }
            this.experiment_selected = {'id': this.experiment.title,
                                        'attributes': {
                                            'title': this.experiment.title,
                                            'project': this.project.title,
                                            'description': this.experiment.description,
                                            'conductor': this.experiment.conductor
                                            }
                                        };
            this.is_modal_new_experiment_active = false;
        },
    },
    watch: {
        experiment_selected: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            // this.sample_file = "";
            // this.sample_title = "";
            // this.sample_description = "";
            this.sample_project = this.project_selected.id;
            this.sample_experiment = new_value.id;

            if ( !_.isEmpty(new_value.id) ) {
                if ( !_.isEmpty(this.room_experiment) )
                    this.be.unsubscribe(['samples'],
                                        this.room_experiment
                                        );
                this.room_experiment = this.project_selected.id + '_' + new_value.id;
                this.be.subscribe(['samples'],
                                  this.room_experiment
                                  );
                return this.be.export_one_way_binding_prop('experiment_selected',
                                                           new_value,
                                                           old_value,
                                                           this.room_sid
                                                           );
            }
        },
        experiments: function(new_value) {
            this.experiments_ui = new_value.experiments;
            this.SetExperiment();
        },
        import_sample_table_datetime_range: function(new_value, old_value) {
            return this.be.export_one_way_binding_prop('import_sample_table_datetime_range',
                                                        new_value, old_value,
                                                        this.room_experiment);
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
        importable_samples: function(new_data){
            for (let i=0; i<new_data.cols.length; i++) {
                new_data.cols[i]['searchable'] = true;
            }
            this.import_sample_table_cols = new_data.cols;
            this.import_sample_table_rows = new_data.rows;
            this.import_sample_table_loading = false;
        },
        new_file: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            this.sample_file = new_value;
            let sample_no = this.sample_table_rows.length + 1;
            this.sample_title = sample_no.toString().padStart(3, '0') + '_';
            this.sample_description = "";
            this.is_sample_attribute_modal_active = true;
            this.sample_table_checked_rows = [];
        },
        project_selected: function(new_value, old_value) {
            if ( !_.isEmpty(new_value.id) ) {
                if ( !_.isEmpty(this.room_project) ) {
                    this.be.unsubscribe(['experiments'],
                                        this.room_project
                                        );
                }
                this.room_project = new_value.id;
                this.be.subscribe(['experiments'],
                                  this.room_project
                                  );
                // push new_value of project_selected to corresponding room
                this.be.export_one_way_binding_prop('project_selected',
                                                    new_value,
                                                    old_value,
                                                    this.room_sid
                                                    );
            }
            this.sample_project = new_value.id;
        },
        projects: function() {
            this.SetProject();
        },
        samples: function(new_data){
            this.sample_table_cols = new_data.cols;
            this.sample_table_rows = new_data.rows;
        },
        sample_attributes: function(new_value, old_value) {
            return this.be.export_one_way_binding_prop('sample_attributes',
                                                       new_value,
                                                       old_value,
                                                       this.room_experiment
                                                       );
        },
        sample_attributes_fields: {
            handler(new_value) {
                for (let i in new_value) {
                    if (new_value[i].label == "Sample title") {
                        this.sample_title = new_value[i].value;
                        break;
                    }
                }
                this.sample_attributes_save_button_type = "is-danger";
            },
            deep: true
        },
        sample_experiment: function(new_value) {
            this.experiment.title = new_value;
            this.SetExperiment();
        },
        sample_project: function(new_value) {
            this.project.title = new_value;
            this.SetProject();
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
            if (last_selection) {
                this.sample_file = last_selection.id;
                this.sample_title = last_selection.title || "";
                this.sample_description = last_selection.description || "";
                this.sample_project = last_selection.project;
                this.sample_experiment = last_selection.experiment;
                this.sample_to_display = {
                            'filename': this.sample_file,
                            'title': this.sample_title,
                            'description': this.sample_description,
                            'length': last_selection.length,
                            'range': last_selection.range,
                            };
                this.sample_annotations = [];
            } else {
                this.sample_to_display = {
                            'filename': "",
                            'title': "",
                            'description': "",
                            'length': 0,
                            'range': [0, 0],
                            };
                this.sample_annotations = [];
            }
        },
        sample_title: function() {
            this.sample_attributes_save_button_type = "is-danger";
        },
        'root_namespace.connected': function(new_value) {
            if ( new_value === true )
            {
                this.namespace = this.root_namespace;
                // handlers for for external notifications:
                this.namespace.on('experiments', (value) => this.be.import_two_way_binding_prop('experiments', value.value));
                this.namespace.on("importable_samples", (value) => this.be.import_one_way_binding_prop("importable_samples", value.value));
                this.namespace.on("projects", (value) => this.be.import_two_way_binding_prop("projects", value.value));
                this.namespace.on("samples", (value) => this.be.import_one_way_binding_prop("samples", value.value));

                this.room_sid = this.root_namespace.id;
                this.be.subscribe(this.endpoints, this.room_sid);
                this.be.subscribe(['projects'], 'projects');
            }
        },
    }
};


</script>
