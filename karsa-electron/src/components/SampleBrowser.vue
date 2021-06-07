<template>
    <div>
    <!-- Modals -->
        <!-- Landing modal -->
        <section class="landing-modal">
            <b-modal :active.sync="is_modal_landing_active"
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
                                    @input="selectProject($event)"
                                    required
                                    expanded>
                                    <option
                                        v-for="p in projects"
                                        :value="p.title"
                                        :key="p.title">
                                        {{ p.title }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-button
                                expanded
                                @click="launchProjectAttributesModal('new')">
                                New Project
                            </b-button>

                            <div><br></div>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    @input="selectExperiment($event)"
                                    :disabled="!project_selected.title"
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments"
                                        :value="e.title"
                                        :key="e.title">
                                        {{ e.title }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-button
                                expanded
                                @click="launchNewExperimentModal()"
                                :disabled="!project_selected.title">
                                New Experiment
                            </b-button>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                @click="is_modal_landing_active=false"
                                is-dark
                                :disabled="!(project_selected.title.length && experiment_selected.title.length)">
                                Proceed
                            </b-button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>     
        <!-- End of landing modal -->
        
        <!--- Project attributes modal--> 
        <section class="project-attribute-modal">
            <b-modal :active.sync="is_modal_project_attributes_active"
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
                                    {{project_form_props.title}}
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <MetaDataForm
                                    form_title="Project attributes"
                                    :default_template="project_form_props.default_template"
                                    :editable="project_form_props.editable"
                                    :initial_template="project_form_props.initial_template"
                                    :template_path="project_form_props.template_path"
                                    @metaDataUpdated="project_attributes_fields=$event">
                                </MetaDataForm>
                            </section>
                        </div>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button
                            :disabled="false"
                            @click="saveProject()">
                            Save
                        </b-button>
                        <b-button
                            @click="cancelNewProject()">
                            Cancel
                        </b-button>
                        <div
                            v-if="project_form_props.initial_template"
                            style="position:absolute; right:20px">
                            <b-tooltip
                                label="Delete project"
                                position="is-left"
                                :delay="1000">
                                <b-button
                                    disabled
                                    type="is-danger"
                                    icon-left="delete"
                                    @click="deleteProject(project_form_props.initial_template[0].value)">
                                </b-button>
                            </b-tooltip>
                        </div>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of project attributes modal--> 

        <!--- New experiment modal--> 
        <section class="experiment-attribute-modal">
            <b-modal
                :active.sync="is_modal_new_experiment_active"
                has-modal-card
                trap-focus
                :can-cancel="true">
                <div class="modal-card" style="width: 500px">
                    <div class="columns">
                        <div class="column">
                            <header class="modal-card-head">
                                <p class="modal-card-title">
                                    New experiment
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <MetaDataForm
                                    form_title="Experiment attributes"
                                    :default_template="experiment_attributes_default_template"
                                    :editable="true"
                                    :template_path="experiment_attributes_template_path"
                                    @metaDataUpdated="experiment_attributes_fields=$event">
                                </MetaDataForm>
                                <div><br></div>
                                <MetaDataForm
                                    form_title="Sample attribute template"
                                    :default_template="sample_attributes_default_template"
                                    :editable="true"
                                    :fillable="false"
                                    :template_path="sample_attributes_template_path"
                                    @metaDataUpdated="sample_attributes_fields=$event">
                                </MetaDataForm>
                            </section>
                        </div>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button 
                            @click="saveExperiment()">
                            Save
                        </b-button>
                        <b-button 
                            @click="cancelNewExperiment()">
                            Cancel
                        </b-button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of new experiment modal-->

        <!--- Edit experiment modal--> 
        <section class="experiment-attribute-modal">
            <b-modal :active.sync="is_modal_experiment_attributes_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px">
                    <div class="columns">
                        <div class="column">
                            <header class="modal-card-head">
                                <p class="modal-card-title">
                                    Edit experiment
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <MetaDataForm
                                    form_title="Experiment attributes"
                                    :initial_template="experiment_edit_form_props.attributes"
                                    :editable="true"
                                    @metaDataUpdated="experiment_attributes_fields=$event">
                                </MetaDataForm>
                                <div><br></div>
                                <MetaDataForm
                                    form_title="Sample attribute template"
                                    :initial_template="experiment_edit_form_props.sample_attributes_template"
                                    :editable="false"
                                    :fillable="false">
                                </MetaDataForm>
                            </section>
                        </div>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <b-button 
                            :disabled="false"
                            @click="saveExperiment()">
                            Save
                        </b-button>
                        <b-button 
                            @click="is_modal_experiment_attributes_active=false">
                            Cancel
                        </b-button>
                        <div style="position:absolute; right:20px">
                            <b-button
                                @click="launchPrefillSampleAttributesModal()">
                                Prefill
                            </b-button>
                            <b-tooltip
                                label="Delete experiment"
                                position="is-left"
                                :delay="1000">
                                <b-button
                                    disabled
                                    type="is-danger"
                                    icon-left="delete"
                                    @click="deleteExperiment(experiment_edit_form_props.attributes[0].value)">
                                </b-button>
                            </b-tooltip>
                        </div>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of edit experiment modal-->

        <!-- Modal for sample attributes -->
        <section class="sample-attribute-modal">
            <b-modal :active.sync="is_modal_sample_attributes_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="true"
                aria-role="dialog"
                aria-modal>
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">{{ sample_form_props.filename }}</p>
                        </header>
                        <section class="modal-card-body write_sample_attribute">                            
                            
                            <MetaDataForm
                                :form_title="sample_form_props.title"
                                :default_template="sample_form_props.attributes"
                                :initial_template="sample_form_props.attributes"
                                :load_template_path="sample_form_props.load_template_path"
                                @metaDataUpdated="sample_attributes_fields=$event">
                            </MetaDataForm>

                            <div><br></div>
                            <b-field label="Project">
                                <b-select
                                    placeholder="Select a project"
                                    v-model="project_selected.title"
                                    @input="selectProject($event)"
                                    disabled
                                    required
                                    expanded>
                                    <option
                                        v-for="p in projects"
                                        :value="p.title"
                                        :key="p.title">
                                        {{ p.title }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    v-model="experiment_selected.title"
                                    @input="selectExperiment($event)"
                                    disabled
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments"
                                        :value="e.title"
                                        :key="e.title">
                                        {{ e.title }}
                                    </option>
                                </b-select>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                :type="sample_attributes_save_button_type"
                                @click="saveSample()"
                                :disabled="false">
                                Save
                            </b-button>
                            <b-button
                                @click="is_modal_sample_attributes_active=false">
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
                                        @click="removeSample(sample_form_props.filename)">
                                    </b-button>
                                </b-tooltip>
                            </div>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of Modal for sample edit -->

        <!-- Modal for prefilling sample attributes -->
        <section class="sample-attribute-modal">
            <b-modal :active.sync="is_modal_prefill_sample_attributes_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="true">
                <div class="columns">
                    <div class="modal-card" style="width: auto">
                        <header class="modal-card-head">
                            <p class="modal-card-title">Prefill sample information</p>
                        </header>
                        <section class="modal-card-body write_sample_attribute">                            
                            
                            <MetaDataForm
                                form_title="Prefill sample attributes"
                                :initial_template="experiment_edit_form_props.sample_attributes_template"
                                :template_path="experiment_edit_form_props.prefilled_templates_path">
                            </MetaDataForm>

                            <div><br></div>
                            <b-field label="Project">
                                <b-select
                                    placeholder="Select a project"
                                    v-model="project_selected.title"
                                    @input="selectProject($event)"
                                    disabled
                                    required
                                    expanded>
                                    <option
                                        v-for="p in projects"
                                        :value="p.title"
                                        :key="p.title">
                                        {{ p.title }}
                                    </option>
                                </b-select>
                            </b-field>

                            <b-field label="Experiment">
                                <b-select
                                    placeholder="Select an experiment"
                                    v-model="experiment_selected.title"
                                    @input="selectExperiment($event)"
                                    disabled
                                    required
                                    expanded>
                                    <option
                                        v-for="e in experiments"
                                        :value="e.title"
                                        :key="e.title">
                                        {{ e.title }}
                                    </option>
                                </b-select>
                            </b-field>

                        </section>
                        <footer class="modal-card-foot">
                            <b-button
                                @click="is_modal_prefill_sample_attributes_active=false">
                                Close
                            </b-button>
                        </footer>
                    </div>
                </div>
            </b-modal>
        </section>
        <!-- End of modal for prefilling sample edit -->

        <!-- Sample table modal -->
        <section class="sample-table-modal">
            <b-modal :active.sync="is_modal_sample_table_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                :destroy-on-hide="false"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: auto">
                    <header class="modal-card-head">
                        <p class="modal-card-title">
                            Project experiment samples
                        </p>
                    </header>
                    <section class="modal-card-body">
                        
                        <!-- Sample table -->
                        <b-table 
                            id="samples-datatable"
                            style="height:100%; width:100%"
                            :data="sample_table_rows"
                            :sticky-header="true"
                            detailed
                            detail-key="title"
                            :show-detail-icon="false">
                            <!-- Columns -->
                            <b-table-column
                                v-for="(col, i) in sample_table_cols"
                                :key="i"
                                :field="col.field"
                                :label="col.label"
                                v-slot="props">
                                <a @click="props.toggleDetails(props.row)">
                                    {{ props.row[col.field] }}
                                </a>
                            </b-table-column>
                            <!-- End of columns -->
                            <!-- Details view -->
                            <template #detail="props">
                                <div>
                                    <p @contextmenu.prevent="rightClickSample(props.row.filename)">
                                        <strong>{{ props.row.title }}</strong>
                                        <br>
                                        {{ props.row.description }}
                                        <br>
                                        <small style="color: #ababab;">{{ props.row.filename }}</small>
                                    </p>
                                </div>
                            </template>
                            <!-- End of details view -->
                        </b-table>
                        <!-- End of sample table -->

                    </section>
                    <footer class="modal-card-foot">
                        <b-button
                            @click="is_modal_sample_table_active=false"
                            is-dark>
                            Close
                        </b-button>
                    </footer>
                </div>
            </b-modal>
        </section>     
        <!-- End of sample table modal -->

        <!-- Modal for sample import -->
        <section class="sample-import-modal">
            <b-modal :active.sync="is_modal_sample_import_active"
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
                                @click="importSamples()"
                                is-dark
                                :disabled="!import_sample_table_checked_rows.length">
                                Import
                            </button>
                            <button
                                class="button"
                                type="button"
                                is-dark
                                @click="is_modal_sample_import_active=false">
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
            <b-notification
                :active="!experiment_selected.title.length"
                :closable="false"
                type="is-danger"
                role="alert">
                <p style="font-size:20px">
                    Please select project and experiment.
                </p>
            </b-notification>
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
                                            :key="p.title"
                                            :active.sync="p.active"
                                            :expanded.sync="p.active"
                                            @click="selectProject(p.title)">
                                            <template #label>
                                                 <b-tooltip
                                                    :delay=500
                                                    position="is-right"
                                                    type="is-light"
                                                    multilined
                                                    append-to-body>
                                                    <!-- Menu item content -->
                                                    <div :id="p.title"
                                                         @contextmenu.prevent="rightClickProject($event)">
                                                        {{p.title}}
                                                    </div>
                                                    <template v-slot:content>
                                                        <!-- Tooltip html content -->
                                                        <div
                                                            v-html="prettyPrintAttributes(p.attributes)"
                                                            style="text-align:center;">
                                                        </div>
                                                    </template>
                                                </b-tooltip>
                                            </template>
                                            <!-- Experiments -->
                                            <b-menu-list
                                                label="Experiments"
                                                v-if="p.title === project_selected.title">
                                                <!-- Experiment item -->
                                                <b-menu-item 
                                                    v-for="e in experiments"
                                                    :key="e.title"
                                                    :active.sync="e.active"
                                                    :expanded.sync="e.active"
                                                    @click="selectExperiment(e.title)">
                                                    <template #label>
                                                        <b-tooltip
                                                            :delay=500
                                                            position="is-right"
                                                            type="is-light"
                                                            multilined
                                                            append-to-body>
                                                            <!-- Menu item content -->
                                                            <div :id="e.title"
                                                                @contextmenu.prevent="rightClickExperiment($event)">
                                                                {{e.title}}
                                                            </div>
                                                            <template v-slot:content>
                                                                <!-- Tooltip html content -->
                                                                <div
                                                                    v-html="prettyPrintAttributes(e.attributes)"
                                                                    style="text-align:center;">
                                                                </div>
                                                            </template>
                                                        </b-tooltip>
                                                    </template>
                                                    <p class="menu-label">
                                                        Samples
                                                    </p>
                                                    <!-- Sample table -->
                                                    <div style="text-align:right;">
                                                        <b-button
                                                            icon-left="magnify"
                                                            class="tag is-dark"
                                                            outlined
                                                            @click="is_modal_sample_table_active=true">
                                                        </b-button>
                                                        <b-dropdown
                                                            aria-role="menu"
                                                            type="is-dark"
                                                            position="is-top-right"
                                                            trap-focus
                                                            multiple
                                                            append-to-body>
                                                            <b-button
                                                                icon-left="menu"
                                                                class="tag is-dark"
                                                                slot="trigger"
                                                                outlined>
                                                            </b-button>
                                                            <b-field grouped group-multiline>
                                                                <div v-for="(col, i) in sample_table_cols"
                                                                    :key="i"
                                                                    class="control">
                                                                    <b-checkbox v-model="col.visible">
                                                                        {{ col.label }}
                                                                    </b-checkbox>
                                                                </div>
                                                            </b-field>
                                                        </b-dropdown>
                                                    </div>
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
                                                        v-if="e.title === experiment_selected.title">
                                                        <!-- Columns -->
                                                        <b-table-column
                                                            v-for="(col, i) in sample_table_cols"
                                                            :key="i"
                                                            :field="col.field"
                                                            :label="col.label"
                                                            :visible="col.visible || false"
                                                            v-slot="props">
                                                            <a @click="props.toggleDetails(props.row)">
                                                                {{ props.row[col.field] }}
                                                            </a>
                                                        </b-table-column>
                                                        <!-- End of columns -->
                                                        <!-- Details view -->
                                                        <template #detail="props">
                                                            <div>
                                                                <p @contextmenu.prevent="rightClickSample(props.row.filename)">
                                                                    <strong>{{ props.row.title }}</strong>
                                                                    <br>
                                                                    {{ props.row.description }}
                                                                    <br>
                                                                    <small style="color: #ababab;">{{ props.row.filename }}</small>
                                                                </p>
                                                            </div>
                                                        </template>
                                                        <!-- End of details view -->
                                                    </b-table>
                                                    <!-- End of sample table -->
                                                    <!-- Import sample item -->
                                                    <!-- <b-menu-item
                                                        icon="plus"
                                                        :active="is_modal_sample_import_active"
                                                        @click="launchSampleImport()">
                                                    </b-menu-item> -->
                                                    <!-- End of import sample item -->
                                                </b-menu-item>
                                                <!-- End of experiment item -->
                                                <!-- New experiment item -->
                                                <b-menu-item
                                                    icon="plus"
                                                    :active="is_modal_new_experiment_active"
                                                    @click="launchNewExperimentModal()">
                                                </b-menu-item>
                                                <!-- End of new experiment item -->
                                            </b-menu-list>
                                            <!-- End of experiments -->
                                        </b-menu-item>
                                        <!-- End of project item -->
                                        <!-- New project item -->
                                        <b-menu-item
                                            icon="plus"
                                            :active="is_modal_project_attributes_active"
                                            @click="launchProjectAttributesModal('new')">
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
import { BECom, isValidFilename, shallow_copy } from "../karsalib.js"
import MetaDataForm from "./MetaDataForm.vue"

Vue.use([Buefy]);

var _ = require('underscore');
var fs = require('fs');


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
        sample_selected: {
            get() {
                return this.$store.state.sample_selected;
            },
            set(value) {
                this.$store.commit('sample_selected', value);
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
            auto_save_new_sample: true,
            // Project / experiment title validation
            // Modal active variables
            is_modal_landing_active: true,
            is_modal_experiment_attributes_active: false,
            is_modal_prefill_sample_attributes_active: false,
            is_modal_project_attributes_active: false,
            is_modal_new_experiment_active: false,
            is_modal_sample_import_active: false,
            is_modal_sample_attributes_active: false,
            is_modal_sample_table_active: false,
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
            project_attributes_default_template: [
                {'label': "Title",
                 'value': "",
                 'required': true},
                {'label': "Description",
                 'value': ""},
            ],
            project_attributes_fields: [],
            project_attributes_template_path: "../metadata_templates/project_templates",
            project_form_props: {},

            // Experiment metadata
            experiment_attributes_default_template: [
                {'label': "Title",
                 'value': "",
                 'required': true},
                {'label': "Description",
                 'value': ""},
            ],
            experiment_attributes_fields: [],
            experiment_attributes_template_path: "../metadata_templates/experiment_templates",
            experiment_edit_form_props: {},
            // Sample metadata for selected sample
            samples: [],
            // variables for sample table
            sample_table_rows: [],
            sample_table_cols: [],
            sample_table_checked_rows: [],
            sample_attributes: {},
            sample_attributes_default_template: [
                {'label': "Title",
                 'value': "",
                 'required': true},
                {'label': "Description",
                 'value': ""},
            ],
            sample_attributes_fields: [],
            sample_attributes_save_button_type: "is-success",
            sample_attributes_template_path: "../metadata_templates/sample_templates",
            sample_form_props: {},
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
        cancelNewExperiment() {
            this.is_modal_new_experiment_active = false;
        },
        cancelNewProject() {
            this.is_modal_project_attributes_active = false;
        },
        deleteExperiment(title) {
            this.is_modal_experiment_attributes_active = false;
            const experiment_to_delete = this.getExperiment(title);
            return this.be.export_one_way_binding_prop(
                                            'delete_experiment',
                                            {'project': experiment_to_delete.project,
                                             'experiment': experiment_to_delete.title},
                                            );
        },
        deleteProject(title) {
            this.is_modal_project_attributes_active = false;
            return this.be.export_one_way_binding_prop(
                                            'delete_project',
                                            {'project': title},
                                            );
        },
        getExperiment(experiment_title) {
            for (let i in this.experiments) {
                if(this.experiments[i].title === experiment_title){
                    return shallow_copy(this.experiments[i]);
                }
            }
        },
        getPrefilledTemplatePath(project_title, experiment_title, make_if_missing=false) {
            const template_path = "../metadata_templates/prefilled_templates/" + ([project_title, experiment_title].join("_"));
            if (!fs.existsSync(template_path)) {
                if (make_if_missing) {
                    fs.mkdirSync(template_path);
                } else {
                    return null
                }
            }
            return template_path
        },
        getProject(project_title) {
            for (let i in this.projects) {
                if(this.projects[i].title === project_title){
                    return shallow_copy(this.projects[i]);
                }
            }
        },
        getSample(sample_filename) {
            for (let i in this.samples) {
                if(this.samples[i].filename === sample_filename){
                    return shallow_copy(this.samples[i]);
                }
            }
        },
        importSamples() {
            // TODO: Needs an update

            let to_import = this.import_sample_table_checked_rows[0];
            // Preserve sample id, title and description
            // Set project and experiment to the selected ones
            let sample = {
                'title': to_import.title,
                'experiment': this.experiment_selected.title,
                'project': this.project_selected.title,
                'attributes': {
                    'title': to_import.title,
                    'description': to_import.description,
                    }
                };
            // Export sample attributes to link into current experiment
            this.sample_attributes = sample;
            this.is_modal_sample_import_active = false;
        },
        launchExperimentAttributesModal(experiment) {
            this.experiment_edit_form_props = {};
            this.experiment_edit_form_props.project = experiment.project;
            this.experiment_edit_form_props.experiment = experiment.title;
            this.experiment_edit_form_props.attributes = experiment.attributes;
            this.experiment_edit_form_props.sample_attributes_template = experiment.sample_attributes_template;
            this.is_modal_experiment_attributes_active = true;
        },
        launchNewExperimentModal() {
            this.is_modal_new_experiment_active = true;
        },
        launchPrefillSampleAttributesModal() {
            const experiment_title = this.experiment_edit_form_props.experiment;
            const project = this.experiment_edit_form_props.project;
            this.experiment_edit_form_props.prefilled_templates_path = this.getPrefilledTemplatePath(project, experiment_title, true);
            this.is_modal_prefill_sample_attributes_active = true;
        },
        launchProjectAttributesModal(mode, initial_template=null) {
            switch (mode) {
                case "new":
                    this.project_form_props = {
                        'title': "New Project",
                        'initial_template': initial_template,
                        'default_template': this.project_attributes_default_template,
                        'editable': true,
                        'template_path': this.project_attributes_template_path,
                    };
                    break;
                case "edit":
                    this.project_form_props = {
                        'title': "Edit project",
                        'initial_template': initial_template,
                        'default_template': [],
                        'editable': true,
                        'template_path': null,
                    };
                    break;
            }
            this.is_modal_project_attributes_active = true;
        },
        launchSampleAttributeModal() {
            this.is_modal_sample_attributes_active = true;
        },
        launchSampleImport() {
            // Request list of samples from FileService
            this.import_sample_table_datetime_range = Math.random();
            // Set loading state
            this.import_sample_table_loading = true;
            // Launch modal
            this.is_modal_sample_import_active = true;
        },
        prettyPrintAttributes(form_fields) {
            let pretty_text = "";
            for (let i in form_fields) {
                let label = form_fields[i].label;
                let value = form_fields[i].value;
                pretty_text += ("<b>"+label+"</b>"+"<br>" + value + "<br>");
            }
            return pretty_text
        },
        removeSample(filename) {
            this.is_modal_sample_attributes_active = false;
            const sample_to_remove = this.getSample(filename);
            return this.be.export_one_way_binding_prop(
                                            'delete_sample',
                                            sample_to_remove,
                                            );
        },
        rightClickExperiment(event) {
            const title = event.path[0].id;
            let experiment = this.getExperiment(title);
            // Disabled title editing
            experiment.attributes[0].disabled = true;
            this.launchExperimentAttributesModal(experiment);
        },
        rightClickProject(event) {
            const title = event.path[0].id;
            let project = this.getProject(title);
            // Disabled title editing
            project.attributes[0].disabled = true;
            this.launchProjectAttributesModal('edit', project.attributes);
        },
        rightClickSample(sample_filename) {
            const sample = this.getSample(sample_filename);
            this.sample_form_props = sample;
            this.sample_form_props.title = "Edit sample attributes";
            this.launchSampleAttributeModal();
        },
        saveExperiment() {
            let title = this.experiment_attributes_fields[0].value;
            if ( !isValidFilename(title) ) {
                // Title contains illegal characters
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "The title must contain only numbers, letters and _",
                    type: 'is-danger'
                });
                return
            }
            const new_experiment = {
                    'title': title,
                    'project': this.project_selected.title,
                    'attributes': this.experiment_attributes_fields,
                    'sample_attributes_template': this.sample_attributes_fields,
                    };
            this.is_modal_new_experiment_active = false;
            return this.be.export_one_way_binding_prop('save_experiment',
                                                        new_experiment,
                                                        );
        },
        saveProject() {
            let title = this.project_attributes_fields[0].value;
            if ( !isValidFilename(title) ) {
                // Title contains illegal characters
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "The title must contain only numbers, letters and _",
                    type: 'is-danger'
                });
                return
            }
            const new_project = {
                    'title': title,
                    'attributes': this.project_attributes_fields
                    };
            this.is_modal_project_attributes_active = false;
            return this.be.export_one_way_binding_prop('save_project',
                                                        new_project,
                                                        );
        },
        saveSample() {
            if ( !(this.project_selected.title.length && this.experiment_selected.title.length) ) {
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "Project and experiment must be selected to store sample attributes.",
                    type: 'is-danger'
                })
                return
            }
            let sample_to_save = {
                'filename': this.sample_form_props.filename,
                'experiment': this.sample_form_props.experiment,
                'project': this.sample_form_props.project,
                'attributes': this.sample_attributes_fields,
            };
            // this.sample_attributes = sample;
            this.is_modal_sample_attributes_active = false;
            return this.be.export_one_way_binding_prop('save_sample',
                                                       sample_to_save,
                                                       );
        },
        selectExperiment(experiment_title) {
            // Set experiment active in sample tree
            for (let i in this.experiments) {
                if(this.experiments[i].title === experiment_title){
                    this.experiments[i].active = true;
                } else {
                    this.experiments[i].active = false;
                }
            }
            this.experiment_selected = this.getExperiment(experiment_title);
            this.is_modal_new_experiment_active = false;
            this.is_modal_experiment_attributes_active = false;
            this.is_modal_landing_active = false;
        },
        selectProject(project_title) {
            // Set project active in the sample tree
            for (let i in this.projects) {
                if(this.projects[i].title === project_title){
                    this.projects[i].active = true;
                } else {
                    this.projects[i].active = false;
                }
            }
            this.project_selected = shallow_copy(this.getProject(project_title));
            // Reset experiment
            this.experiment_selected = {
                'title': "",
                'project': "",
                'attributes': [],
                'sample_attributes_template': [],
                };
            this.is_modal_project_attributes_active = false;
        },
    },
    watch: {
        experiments: function() {
            if (this.experiment_selected.title) {
                this.selectExperiment(this.experiment_selected.title);
            }
        },
        projects: function() {
            if (this.project_selected.title) {
                let experiment_selected_title = this.experiment_selected.title;
                this.selectProject(this.project_selected.title);
                if (experiment_selected_title)
                    this.selectExperiment(experiment_selected_title);
            }
        },
        experiment_selected: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if ( !_.isEmpty(new_value.title) ) {
                if ( !_.isEmpty(this.room_experiment) )
                    this.be.unsubscribe(['samples'],
                                        this.room_experiment
                                        );
                this.room_experiment = this.project_selected.title + '_' + new_value.title;
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
            if ( !(this.project_selected.title.length &&
                   this.experiment_selected.title.length) ) {
                return false;
            }
            this.sample_form_props = {};
            this.sample_form_props.filename = new_value;
            this.sample_form_props.project = this.project_selected.title;
            this.sample_form_props.experiment = this.experiment_selected.title;
            this.sample_form_props.attributes = shallow_copy(this.experiment_selected.sample_attributes_template);
            this.sample_form_props.title = "New sample attributes";
            this.sample_form_props.load_template_path = this.getPrefilledTemplatePath(this.project_selected.title, this.experiment_selected.title);
            // Set title prefix
            let sample_no = this.samples.length + 1;
            const sample_title_prefix = sample_no.toString().padStart(3, '0') + '_';
            this.sample_form_props.attributes[0].value = sample_title_prefix;
            if (this.auto_save_new_sample) {
                this.saveSample();
            }
            this.launchSampleAttributeModal();
        },
        project_selected: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if ( !_.isEmpty(new_value.title) ) {
                if ( !_.isEmpty(this.room_project) ) {
                    this.be.unsubscribe(['experiments'],
                                        this.room_project
                                        );
                }
                this.room_project = new_value.title;
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
        },
        samples: function(new_value, old_value){
            // Format data to sample table
            let samples = new_value;
            if ( _.isEmpty(new_value) && !_.isEmpty(old_value) ) {
                // refresh current sample table
                samples = old_value;
                this.selectExperiment(samples[0].experiment)
            }
            let rows = [];
            let cols = [];
            for (const i in samples) {
                let sample = samples[i];
                let row = {};
                // Unpack attributes
                for (let i in sample.attributes) {
                    let attr = sample.attributes[i];
                    if (rows.length == 0) {
                        let col = {
                            'field': attr.label.toLowerCase(),
                            'label': attr.label,
                            };
                        if (col.field == 'title') {
                            col.visible = true;
                        }
                        cols.push(col);
                    }
                    row[attr.label.toLowerCase()] = attr.value.toString(); // TODO: prettify
                }
                // Unpack properties
                for (const prop in sample.properties) {
                    if (rows.length == 0) {
                        cols.push({
                            'field': prop.toLowerCase(),
                            'label': prop,
                            });
                    }
                    row[prop.toLowerCase()] = sample.properties[prop];
                }
                // Hard-coded attributes
                row['filename'] = sample.filename;
                row['project'] = sample.project;
                row['experiment'] = sample.experiment;
                
                if (rows.length == 0) {
                    cols.concat([
                        {
                        'field': "filename",
                        'label': "Filename",
                        },
                        {
                        'field': "project",
                        'label': "Project",
                        },
                        {
                        'field': "experiment",
                        'label': "Experiment",
                        }
                    ]);
                }

                rows.push(row);
                
                if (row['filename'] == this.sample_selected.filename) {
                    this.sample_table_checked_rows = [row,];
                }
            }
            this.sample_table_cols = cols;
            this.sample_table_rows = rows;
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
                // Sample selected
                let filename = last_selection.filename;
                const sample = this.getSample(filename);
                this.sample_selected = {'title': last_selection.title,
                                        ...sample
                                        };
            } else {
                // Sample deselected
                this.sample_selected = {
                            'filename': "",
                            'title': "",
                            'properties': {
                                'length': 0,
                                'range': [0, 0],
                                },
                            };
            }
            this.sample_annotations = [];
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
