<template>
    <div>

        <!-- Main content  area-->
        <section>
            <div :id="id"></div>
        </section>

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
    },
    data: function() {
        return {
            figure_traces_default: [
                {
                    'name': "Found peaks",
                    'legendgroup': "Found peaks",
                    x: [0],
                    y: [0],
                    'mode': 'lines',
                    'line': {'color': '#ffffff',
                             'width': 1},
                    'visible': 'legendonly',
                    'showlegend': true,
                }
            ],
        }
    },

    created: function(){
    },

    mounted: function() {
    },

    methods: {
    },

    watch: {
        sample_annotations: function(new_value) {
            for (let i in new_value) {
                let annotation = {
                    'text': new_value[i].text,
                    'yref': 'y',
                    'y': new_value[i].timestamp,
                    'xref': 'paper',
                    'x': 1,
                    'axref': 'paper',
                    'ax': 0,
                    'ay': 0,
                    };
                this.figure_annotations.push(annotation);
            }
            // Update figure
            Plotly.relayout(this.id, {annotations: this.figure_annotations});
        },
    },
};
</script>