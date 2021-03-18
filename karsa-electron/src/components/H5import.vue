<template>
    <div>
        <!-- Modals -->
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
        <!-- End of modals -->

        <!-- Main content area -->
        <section>
            <!-- Acquisiton parameters collapsable -->
            <section>
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
                            H5 import
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
                                    H5 streamer status: {{ h5_streamer_status }}
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
                                    type="is-dark"
                                    @click="is_import_h5_modal_active=true"
                                    outlined
                                    inverted
                                    :disabled="(h5_streamer_status=='ready'
                                                ) ? false : true">
                                    Import h5 file
                                </b-button>
                                <div><br></div>
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

<script type="text/javascript">
"use strict";
import Vue from "vue";
import { mapState } from 'vuex';
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';
import {BECom} from "../karsalib.js"

Vue.use([Buefy]);

var _ = require('underscore');


export default {
    name: "H5import", //used as app_name - keep it unique
    components: {
    },
    computed: {
        ...mapState([
            'url',
            'data_source_selected',
        ]),
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
            be: null,
            namespace: null,
            room_sid: null,
            endpoints: [
                'acquisition_progress',
                'acquisition_started',
                // 'acquisition_status',
                'h5_streamer_status'
            ],
            // h5 streamer
            acquisition_progress: 0,
            acquisition_started: {},
            is_import_h5_modal_active: false,
            h5_samples: [],
            h5_streamer_status: "not_ready",		// not_ready/ready
            h5_to_import: [],
            // variables for h5 import modal
            import_start_time: null,
            import_end_time: null,
            import_min_datetime: null,
            import_max_datetime: new Date(),
            import_h5_table_rows: [],
            import_h5_table_cols: [],
            import_h5_table_checked_rows: [],
            import_h5_table_datetime_range: {},
        }
    },
    created: function() {
        this.be = new BECom(this);
        this.h5_namespace = this.be.connect(this.url + '/' + this.data_source_selected.name);
        // this.be.subscribe(null, this.h5_namespace); // TODO: subscribe or not to
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
    },
    watch: {
        acquisition_started: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            this.new_file = new_value.filename;
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
        h5_to_import: function(new_value, old_value) {
            return this.be.export_one_way_binding_prop('h5_to_import',
                                                        new_value,
                                                        old_value,
                                                        null,
                                                        null,
                                                        this.h5_namespace,
                                                        );
        },
        import_h5_table_datetime_range: function(new_value, old_value) {
            return this.be.export_one_way_binding_prop('import_h5_table_datetime_range',
                                                        new_value,
                                                        old_value,
                                                        this.room_sid,
                                                        null,
                                                        this.h5_namespace,
                                                        );
        },
        'namespace.connected': function(new_value) {
            if ( new_value === true )
            {
                // handlers for for external notifications:
                this.namespace.on("acquisition_started", (value) => this.be.import_one_way_binding_prop("acquisition_started", value.value));
                // this.namespace.on("acquisition_status", (value) => this.be.import_one_way_binding_prop("acquisition_status", value.value));
                this.namespace.on("acquisition_progress", (value) => this.be.import_one_way_binding_prop("acquisition_progress", value.value.progress, true));
                this.h5_namespace.on("h5_streamer_status", (value) => this.be.import_two_way_binding_prop("h5_streamer_status", value.value));
                this.h5_namespace.on("h5_samples", (value) => this.be.import_one_way_binding_prop("h5_samples", value.value));

                this.be.subscribe(this.endpoints,
                                  null // room set to null to subscribe to endpoints directly
                                  );
            }
        },
    },
};

</script>
