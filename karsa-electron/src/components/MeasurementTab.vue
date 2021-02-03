<template src = "../templates/MeasurementTab.vue"></template>

<script type = "text/javascript" >
"use strict";

import Vue from "vue";
import { mapState } from 'vuex';
import Buefy from "buefy";
import Multiselect from "vue-multiselect";
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';

Vue.use([Buefy]);

var fs = require('fs');
// var path = require('path');
// var dialog = require("electron").remote.dialog;
// var remote = require('electron').remote;
// var dot_env_vars = remote.getGlobal('dot_env_vars');
var _ = require('underscore');

export default {
    name: "MeasurementTab",
    components: {
        // using third party multiselect component
        Multiselect,
    },
    props: {
        msg: String
    },
    data() {
        return {
            // variables for modal / Popup boxes
            
        }
    },
    computed: {
        ...mapState([
                    'acquisition_started',
                    'acquisition_status',
                    'figure_ranges',
                    'instrument_status',
                    ]),


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
                // var t = document.getElementsByClassName("desorption-temperature-ramp-table");
                // try {
                //     t[0]["children"][0]["children"][0]["children"][0]["children"][0]["children"][2].innerHTML = "Filters";
                // } catch (e) {
                //     console.log(e);
                // }
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
        
        async read_config_and_init_ui() {
            try {
                if (fs.existsSync('configs/measurementtab_config.json')) {
                    var measurementtab_config = JSON.parse(fs.readFileSync('configs/measurementtab_config.json', 'utf8'));
                    this.acquisition_mode = measurementtab_config.AcquisitonParameters.acquisition_mode;
                    this.sample_length = measurementtab_config.AcquisitonParameters.sample_length;

                    // var data = measurementtab_config.DesorptionTemperatureRamp.data;
                    // this.desorption_table_data = data.sort(function(a, b) {
                    //     return a.time - b.time;
                    // });

                    // this.desorption_table_checked_rows = [];
                    // for (var j = 0; j < measurementtab_config.DesorptionTemperatureRamp.checked_rows.length; j++) {
                    //     this.desorption_table_checked_rows.push(this.desorption_table_data[measurementtab_config.DesorptionTemperatureRamp.checked_rows[j]]);
                    // }
                    // this.draw_desorption_chart()
                }
            } catch (err) {
                console.error(err)
            }
        },
        
        write_to_config_file(data) {
            fs.writeFileSync('configs/measurementtab_config.json', data);
        },
        
    },
    watch: {
        
        sample_length: function(new_value, old_value) {
            if (new_value === old_value) {
                return false;
            }
            if (this.data_updated_from_loading === false) {
                this.save_all_values_to_configuration_file();
            }
        },

    },
}
</script>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"> </style>
<style src = "../assets/css/MeasurementTab.css"> </style>