<template>
    <div>
        <!-- Main content  area-->
        <section>
            <div :id="id"></div>
        </section>
        <!-- End of main content area -->
    </div>
</template>


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
// import { mapState } from 'vuex'
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';
// import { BECom } from "../karsalib.js"
import { viewPortMixin } from "../mixins/viewPortMixin"

Vue.use([Buefy]);

// var fs = require('fs');
var Plotly = require('plotly.js-dist');
// var _ = require('underscore');


export default {
    // name: "ViewPort",
    components: {
    },
    mixins: [
        viewPortMixin
    ],
    props: {
        id: String,
    },
    computed: {
        sample_annotation_timestamp: {
            get() {
                return this.$store.state.sample_annotation_timestamp;
            },
            set(value) {
                this.$store.commit('sample_annotation_timestamp', value);
            },
        },
    },
    data: function() {
        return {
        }
    },

    created: function(){
    },

    mounted: function() {
    },

    methods: {
        on_plotly_click(eventData) {
            // Plotly click event handler
            let timestamp = eventData.points[0].x;
            this.sample_annotation_timestamp = timestamp;
        },
    },

    watch: {
        sample_annotations: function(new_value) {
            let annotations = [];
            for (let i in new_value) {
                let annotation = {
                    'text': new_value[i].text,
                    'xref': 'x',
                    'x': new_value[i].timestamp,
                    'yref': 'paper',
                    'y': 0,
                    'ayref': 'paper',
                    'ay': .9,
                    'ax': 0,
                    };
                annotations.push(annotation);
            }
            // Update figure
            Plotly.relayout(this.id, {annotations: annotations})
        },
    },
};
</script>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"> </style>
<style src = "../assets/css/MeasurementTab.css"> </style>