<template>
    <div>
        <!--- All modals or popups should be here--> 
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
                                    Project details
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
                            Proceed
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
        <section class="sample-attribute-modal">
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
                                    Experiment details
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <b-field label="Experiment title">
                                    <b-input type="input"
                                        v-model="experiment.title"
                                        :value="experiment.title"
                                        maxlength="50"
                                        required
                                        validation-message="Only numbers, letters and _ allowed in the title"
                                        :pattern="valid_pattern.toString().slice(1, -1)">
                                    </b-input>
                                </b-field>
                                <b-field label="Description">
                                    <b-input 
                                        v-model="experiment.description" 
                                        :value="experiment.description"
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
                            @click="SetExperiment" 
                            is-dark>
                            Proceed
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

        <!--- New method modal--> 
        <section class="sample-attribute-modal">
            <b-modal :active.sync="is_modal_new_method_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal
            >
                <div class="modal-card" style="width: 500px">
                    <div class="columns">
                        <!-- Right side -->
                        <div class="column">
                            <header class="modal-card-head">
                                <p class="modal-card-title">
                                    Instrument configuration
                                </p>
                            </header>
                            <section class="modal-card-body">
                                <b-field label="Mass spectrometer">
                                    <b-select 
                                        placeholder="Select MS" 
                                        v-model="instrument.ms"
                                        expanded 
                                        disabled>
                                        <option
                                            v-for="ms in mspecs"
                                            :value="ms.id"
                                            :key="ms.id">
                                            {{ ms.name }}
                                        </option>
                                    </b-select>
                                </b-field>
                                <b-field label="Inlet type">
                                    <b-select 
                                        placeholder="Select inlet" 
                                        v-model="instrument.inlet" 
                                        expanded 
                                        disabled>
                                        <option
                                            v-for="inlet in inlets"
                                            :value="inlet.id"
                                            :key="inlet.id">
                                            {{ inlet.name }}
                                        </option>
                                    </b-select>
                                </b-field>
                                <b-field label="Ion polarity">
                                    <b-select 
                                        placeholder="Select polarity" 
                                        v-model="instrument.polarity" 
                                        expanded 
                                        disabled>
                                        <option value="positive"> Positive </option>
                                        <option value="negative"> Negative </option>
                                    </b-select>
                                </b-field>
                                <b-field label="Ion chemistry">
                                    <b-select 
                                        placeholder="Select reagent" 
                                        v-model="instrument.reagent" 
                                        expanded 
                                        disabled>
                                        <option
                                            v-for="r in reagents"
                                            :value="r.id"
                                            :key="r.id">
                                            {{ r.name }}
                                        </option>
                                    </b-select>
                                </b-field>
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
                            Proceed
                        </button>
                        <button 
                            class="button" 
                            type="button" 
                            is-dark 
                            @click="is_modal_new_experiment_active=false">
                            Cancel
                        </button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of new method modal-->
        <!-- End of Modals -->

        <!-- Main content  area-->
        <section class="main-content">
            <div class="columns">
                <!-- Empty column -->
                <div class="column is-one-third">
                </div>
                <!-- Project / Experiment column -->
                <div class="column is-one-third">
                    <!-- Top row (Project) -->
                    <div class="row">
                        <!-- Header -->
                        <section style="width:100%;">
                            <p class="card-header-title">
                                Project
                            </p>
                        </section>
                        <!-- Container -->
                        <section class="project-section">
                            <div class="columns new-experiment-container">
                                <div class="column">
                                    <div class="row">
                                        <!-- New project -->
                                        <div class="column" style="text-align:center">
                                            <b-button
                                                @click="LaunchNewProjectModal()"
                                                type="is-dark"
                                                size="is-medium"
                                                outlined
                                                inverted>
                                            New project
                                            </b-button>
                                        </div>
                                        <!-- Select project -->
                                        <div class="column">
                                            <b-field label="Select project">
                                                <b-select
                                                    placeholder="Select a project"
                                                    v-model="project.title"
                                                    v-on:input="SetProject"
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
                                            <div><br></div>
                                        </div>
                                    </div>
                                    <div class="row">
                                        <b-field label="Description">
                                            <b-message>
                                                {{project.description}}
                                            </b-message>
                                        </b-field>
                                        <div><br></div>
                                    </div>
                                </div>
                            </div>
                        </section>
                    </div>
                    <!-- End of top row -->
                    <div><br><br><br></div>
                    <!-- Bottom row (Experiment) -->
                    <div class="row">
                        <!-- Header -->
                        <section style="width:100%;">
                            <p class="card-header-title" style=text-align: center>
                                Experiment
                            </p>
                        </section>
                        <!-- Container -->
                        <section style="width:100%;">
                            <div class="columns new-experiment-container">
                                <div class="column">
                                    <div class="row">
                                        <!-- New experiment -->
                                        <div class="column" style="text-align:center">
                                            <b-button 
                                                @click="LaunchNewExperimentModal()" 
                                                :disabled="project_selected==={} || project_selected.id===''"
                                                type="is-dark" 
                                                size="is-medium" 
                                                outlined 
                                                inverted>
                                                New experiment
                                            </b-button>
                                        </div>
                                        <!-- Select box -->
                                        <div class="column">
                                            <b-field label="Select experiment">
                                                <b-select 
                                                    placeholder="Select an experiment" 
                                                    v-model="experiment.title" 
                                                    v-on:input="SetExperiment"
                                                    :disabled="project_selected==={} || project_selected.id===''"
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
                                            <div><br></div>
                                        </div>
                                    </div>
                                    <div class="row">
                                        <b-field label="Description">
                                            <b-message>
                                                {{experiment.description}}
                                            </b-message>
                                        </b-field>
                                        <div><br></div>
                                    </div>
                                </div>
                            </div>
                        </section>
                    </div>
                    <!-- End of bottom row -->
                </div>
                <!-- Empty column -->
                <div class="column is-one-third">
                </div>
            </div>
        </section>
    </div>
</template>

<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import Buefy from "buefy";

import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';

Vue.use([Buefy]);

// var _ = require('underscore');
// var dialog = require("electron").remote.dialog;
//var remote = require('electron').remote;

// List of inlet types. Should be read from file
var inlets = [
    {'id': 'sh',
     'name': 'Scenthound'
     },
     {'id': 'mion',
     'name': 'MION'
     },
     {'id': 'mion2',
     'name': 'MION v2'
     },
     {'id': 'a70',
     'name': 'A70'
     }
    ]

// List of MS types. Should be read from file
var mspecs = [
    {'id': 'ltof',
     'name': 'LTOF'
     },
     {'id': 'orbi',
      'name': 'Orbitrap'
      }
    ]

// List of reagents. Should be read from file
var all_reagents = [
    {'id': 'br',
     'name': 'Br',
     'polarity': 'negative'
     },
     {'id': 'dipa',
      'name': 'DIPA',
      'polarity': 'positive'
      }
    ]

export default {
    name: "WorkflowTab",
    data: function() {
        return {
            // Modal active variables
            is_modal_new_project_active: false,
            is_modal_new_experiment_active: false,
            is_modal_new_method_active: false,
            // Project / experiment title validation
            valid_pattern: RegExp(/^\w+$/),
            // Project metadata
            project: {
                title: "",
                description: ""
                },
            // Experiment metadata
            experiment: {
                title: "",
                description: ""
                },
            // Instrument configuration
            instrument: {
                reagent: "",
                polarity: "",
                inlet: "",
                ms: "",
                },
            inlets: inlets,
            mspecs: mspecs,
            reagents: all_reagents,
        }
    },
    computed: {
        active_tab: {
            get() {
                return this.$store.state.active_tab;
            },
            set(value) {
                this.$store.commit('active_tab', value);
            }
        },
        data_source_path: {
            get() {
                return this.$store.state.data_source_path;
            },
            set(value) {
                this.$store.commit('data_source_path', value);
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
        projects: {
            get() {
                return this.$store.state.projects;
            },
            set(value) {
                this.$store.commit('projects', value);
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
        experiments: {
            get() {
                return this.$store.state.experiments;
            },
            set(value) {
                this.$store.commit('experiments', value);
            }
        },
    },
    watch: {
        'instrument.polarity': function(polarity) {
            this.reagents = all_reagents.filter(function(el){
                return el.polarity === polarity
            });
        },
        'instrument.reagent': function(reagent) {
            for(let i in all_reagents){
                if(all_reagents[i].id === reagent){
                    this.instrument.polarity = all_reagents[i].polarity;
                }
            }
        },
    },
    created() {
        // Initialize project_selected
        this.project_selected = {'id': ""};
    },
    methods: {
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
                }
            }
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
            for (let i in this.experiments) {
                if(this.experiments[i].id === this.experiment.title){
                    this.experiment.description = this.experiments[i].attributes.description;
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
            this.active_tab = 1;
        },
    }
}
  
</script>

<style src = "../assets/css/MeasurementTab.css"> </style>