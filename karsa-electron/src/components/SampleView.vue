<template>
    <div>
        <!-- Modals -->
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
                    {{ sample_to_load.title  }}
                </h1>
                <p style="color:#ababab; font-size:16px;">
                    {{ sample_to_load.description }}
                </p>
            </div>
            <div class="columns">
                <!-- Left side -->
                <div class="column is-half">
                    <!-- Heatmap section -->
                    <section class="heatmap-section">
                        <div class="column datashader-heatmap">
                            <ViewPort id="spectrogram"></ViewPort>
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
                            <ViewPort id="timeseries"></ViewPort>
                        </div>                                    
                    </section>
                    <!-- End of timeseries -->
                </div>

                <!-- Right side -->
                <div class="column is-half">
                    <!-- Spec stack section -->
                    <section class="spect-stack-section">
                        <div class="column spec-stack-holder">
                            <ViewPort id="waterfall"></ViewPort>
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
import ViewPort from "./ViewPort.vue"
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';
import { BECom } from "../karsalib.js"

Vue.use([Buefy]);

var _ = require('underscore');


export default {
    name: "SampleView",
    components: {
        ViewPort,
        // using third party multiselect component
        Multiselect
    },
    props: {
        id: String,
    },
    computed: {
        ...mapState([
                    'experiment_selected',
                    'root_namespace',
                    'sample_to_load',
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
    },
    data: function() {
        return {
            be: null,   //backend communicator
            namespace: null,

            // UI variables
            is_modal_add_log_entry_active: false,
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
                'figure_data',
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

        beep: function() {
            var snd = new Audio("data:audio/mp3;base64,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\
            sLivwKKigsj8XYlwt/WKi2N4d//uQRCSAAjURNIHpMZBGYiaQPSYyAAABLAAAAAAAACWAAAAApUF/Mg+0aohSI\
            RobBAsMlO//Kk4soosy1JSFRYWaLC4qZBYWFRGZdwqKiwkNBVmoWFSJkWFxX4FFRQWR+LsS4W/rFRb////////\
            //////////////////////////////////////////////////////////////////////////////////////\
            //////////////////////////////////////////////////////////////////////////////////////\
            //////////////////////////////////////////////////////////////////////////////////////\
            //////////////////////////////////////////////////////////////////////////////////////\
            /////////////////////////////////////////////////////////////////VEFHAAAAAAAAAAAAAAAAA\
            AAAAAAAAAAAAAAAAAAAAAAAU291bmRib3kuZGUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
            AAAAAAAAAAAAAAAAAMjAwNGh0dHA6Ly93d3cuc291bmRib3kuZGUAAAAAAAAAACU=");
            snd.play();
        },

        shallow_copy(o) {
            let _o = JSON.stringify(o);
            if ( _.isUndefined(_o) )
                return _o;
            return JSON.parse(_o);
        },

    },

    watch: {
        sample_to_load: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if (old_value.filename) {
                this.be.unsubscribe(this.endpoints, old_value.filename);
            }
            if (new_value.filename) {
                this.be.subscribe(this.endpoints, new_value.filename);
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

                this.room_sid = this.root_namespace.id;
                this.be.subscribe(this.endpoints, this.room_sid);
            }
        },
    },
};
</script>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"> </style>
<style src = "../assets/css/MeasurementTab.css"> </style>