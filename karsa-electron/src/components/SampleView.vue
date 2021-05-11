<template>
    <div>
        <!-- Modals -->
        <!--- Add annotation modal--> 
        <section class="add-log-entry-modal">
            <b-modal :active.sync="is_modal_add_annotation_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px;">
                    <!-- Main content -->
                    <div>
                        <header class="modal-card-head">
                            <p class="modal-card-title">
                                Add sample annotation
                            </p>
                        </header>
                        <section class="modal-card-body">
                            <b-field label="Timestamp">
                                <b-numberinput
                                    v-model="sample_annotation_timestamp"
                                    :value="sample_annotation_timestamp">
                                </b-numberinput>
                            </b-field>

                            <b-field label="Annotation text">
                                <b-input type="input"
                                    v-model="sample_annotation_text"
                                    :value="sample_annotation_text"
                                    maxlength="50">
                                </b-input>
                            </b-field>

                            <MetaDataForm></MetaDataForm>
                            <div><br></div>
                        </section>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <button
                            class="button"
                            type="button"
                            @click="is_modal_add_annotation_active=false; add_sample_annotation();"
                            is-dark>
                            Save
                        </button>
                        <button
                            class="button"
                            type="button"
                            is-dark
                            @click="is_modal_add_annotation_active=false">
                            Cancel
                        </button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of add annotation modal--> 
        <!--- Add log entry modal--> 
        <section class="add-log-entry-modal">
            <b-modal :active.sync="is_modal_add_log_entry_active"
                has-modal-card
                trap-focus
                :can-cancel="true"
                aria-role="dialog"
                aria-modal>
                <div class="modal-card" style="width: 500px">
                    <!-- Main content -->
                    <div>
                        <header class="modal-card-head">
                            <p class="modal-card-title">
                                Add sample log entry
                            </p>
                        </header>
                        <section class="modal-card-body">
                            <b-field label="Datetime">
                                {{ log_entry_datetimestamp }}
                            </b-field>
                            <b-field label="DAQ time [s]">
                                <b-numberinput
                                    type="is-dark"
                                    min="0"
                                    v-model="log_entry_daq_timestamp">
                                </b-numberinput>
                            </b-field>
                            <b-field label="Text">
                                <b-input
                                    v-model="log_entry_text"
                                    maxlength="255"
                                    type="textarea">
                                </b-input>
                            </b-field>
                        </section>
                    </div>
                    <!-- Footer -->
                    <footer class="modal-card-foot">
                        <button
                            class="button"
                            type="button"
                            @click="writeSampleLogEntry()"
                            is-dark>
                            Save
                        </button>
                        <button
                            class="button"
                            type="button"
                            is-dark
                            @click="cancelSampleLogEntry()">
                            Cancel
                        </button>
                    </footer>
                </div>
            </b-modal>
        </section>
        <!--- End of add log entry modal--> 
        <!-- End of modals -->

        <!-- Main content  area-->
        <section>
            <div style="text-align:center;">
                <h1 style="color:white; font-size:24px;">
                    {{ sample_to_display.title  }}
                </h1>
                <p style="color:#ababab; font-size:16px;">
                    {{ sample_to_display.description }}
                </p>
            </div>
            <div class="columns">
                <!-- Left side -->
                <div class="column is-half">
                    <!-- Heatmap section -->
                    <section class="heatmap-section">
                        <div class="column datashader-heatmap">
                            <ViewPortSpectrogram id="spectrogram">
                            </ViewPortSpectrogram>
                        </div>                                    
                    </section>
                    <!-- End of heatmap section-->
                    <!-- Multiselect section -->
                    <section class="multiselect-section">
                        <div>
                            <br>
                        </div>
<div hidden>
                        <div class="column tps-multiselect">
                            <h2 class="multiselect-title">Select parameter to display</h2>
                            <multiselect 
                            v-model="tps_parameters_selected_ui"
                            tag-placeholder="Add this as new tag" 
                            placeholder="Search or add a tag" 
                            label="label" 
                            track-by="value" 
                            :options="tps_parameters" 
                            :multiple="true" 
                            :taggable="true">
                            </multiselect>
                        </div>   
</div>
                    </section>
                    <!-- End of multiselect section -->
                    <!-- Timeseries section -->
                    <section class="timeseries-section">
                        <div class="column tps-chart"> 
                            <ViewPortTimeseries id="timeseries">
                            </ViewPortTimeseries>
                        </div>                                    
                    </section>
                    <!-- End of timeseries -->
                </div>

                <!-- Right side -->
                <div class="column is-half">
                    <!-- Spec stack section -->
                    <section class="spect-stack-section">
                        <div class="column spec-stack-holder">
                            <ViewPortWaterfall id="waterfall">
                            </ViewPortWaterfall>
                        </div>                            
                    </section>
                    <!-- End of spec stack -->
                </div>

            </div>
        </section>

    </div>
</template>


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from 'vuex'
import Buefy from "buefy";
import Multiselect from "vue-multiselect";
import MetaDataForm from "./MetaDataForm.vue"
import ViewPortSpectrogram from "./ViewPortSpectrogram.vue"
import ViewPortTimeseries from "./ViewPortTimeseries.vue"
import ViewPortWaterfall from "./ViewPortWaterfall.vue"
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';
import { BECom } from "../karsalib.js"

Vue.use([Buefy]);

var _ = require('underscore');


export default {
    name: "SampleView",
    components: {
        MetaDataForm,
        // using third party multiselect component
        Multiselect,
        ViewPortSpectrogram,
        ViewPortTimeseries,
        ViewPortWaterfall,
    },
    props: {
        id: String,
    },
    computed: {
        ...mapState([
                    'experiment_selected',
                    'root_namespace',
                    'sample_annotation_timestamp',
                    'sample_to_display',
                    'target_to_display',
                    //  'tps_parameters',
                    ]),
        figure_data: {
            get() {
                return this.$store.state.figure_data;
            },
            set(value) {
                this.$store.commit('figure_data', value);
            }
        },
        figure_ranges: {
            get() {
                return this.$store.state.figure_ranges;
            },
            set(value) {
                this.$store.commit('figure_ranges', value);
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
    },
    data: function() {
        return {
            be: null,   //backend communicator
            namespace: null,

            // UI variables
            is_modal_add_log_entry_active: false,
            is_modal_add_annotation_active: false,
            //

            // Annotation modal variables
            sample_annotation_text: "",
            //

            // Log entry modal variables
            log_entry_text: "",
            log_entry_datetimestamp: null,
            log_entry_daq_timestamp: 0,
            //

            filename: '',

            tps_parameters: [],
            tps_parameters_selected_ui: [],
            tps_parameters_selected: {},

            room_sid: null,
            endpoints: [
                // 'figure_data',
                // 'figure_ranges',
                // 'tps_parameters',
            ],
        }
    },

    created: function(){
        this.be = new BECom(this);
},

    mounted: function() {
    },

    methods: {
        log: function(...args) {
            console.log('[' + this.$options.name + ']',  ...args);
        },

        add_sample_annotation() {
            let annotation = {
                    'text': this.sample_annotation_text,
                    'timestamp': this.sample_annotation_timestamp
                    };
            this.sample_annotations.push(annotation);
        },

    },

    watch: {
        sample_annotation_timestamp: function() {
            this.is_modal_add_annotation_active = true;
        },
        sample_to_display: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            this.filename = new_value.filename;
            this.figure_ranges = {'filename': new_value.filename,
                                  't_range': [0, new_value.length],
                                  'mz_range': new_value.range,
                                  };
        },
        
        tps_parameters: function(new_value, old_value) {
            if ( _.isEmpty(new_value) || _.isEqual(new_value, old_value) ) {
                return false;
            }
        },
        
        tps_parameters_selected_ui: function(value) {
            this.tps_parameters_selected = {'tps_parameters_selected': value, 'figure_ranges': this.figure_ranges};
        },
        
        tps_parameters_selected: function(new_value, old_value) {
            return this.be.export_one_way_binding_prop('tps_parameters_selected',
                                                        new_value, old_value,
                                                        this.room_sid);
        },

        'root_namespace.connected': function(new_value) {
            if ( new_value === true )
            {
                this.namespace = this.root_namespace;
                // handlers for for external notifications:
                // this.namespace.on("figure_ranges", (value) => this.be.import_one_way_binding_prop("figure_ranges", {...value.value, 'uid': Math.random()}));
                // this.namespace.on("tps_parameters", (value) => this.be.import_one_way_binding_prop("tps_parameters", value.value));
                this.namespace.on("figure_data", (value) => this.be.import_one_way_binding_prop("figure_data", value));
                this.namespace.on("loaded_data", (value) => this.be.import_one_way_binding_prop("figure_data", value));

                this.room_sid = this.root_namespace.id;
                // this.be.subscribe(this.endpoints, this.room_sid);
            }
        },
    },
};
</script>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"> </style>
<style src = "../assets/css/MeasurementTab.css"> </style>