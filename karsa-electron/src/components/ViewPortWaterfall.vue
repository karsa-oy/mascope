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
// var Plotly = require('plotly.js-dist');
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
    },
};
</script>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"> </style>
<style src = "../assets/css/MeasurementTab.css"> </style>