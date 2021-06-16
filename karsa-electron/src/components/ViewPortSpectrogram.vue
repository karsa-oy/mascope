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
            Plotly.relayout(this.id, {"annotations": annotations})
        },
    },
};
</script>