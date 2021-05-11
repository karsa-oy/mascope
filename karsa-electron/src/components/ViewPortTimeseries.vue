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
                                    v-model="annotation_timestamp"
                                    :value="annotation_timestamp">
                                </b-numberinput>
                            </b-field>

                            <b-field label="Annotation text">
                                <b-input type="input"
                                    v-model="annotation_text"
                                    :value="annotation_text"
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
        <!-- End of modals -->

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
import MetaDataForm from "./MetaDataForm.vue"

Vue.use([Buefy]);

// var fs = require('fs');
// var Plotly = require('plotly.js-dist');
// var _ = require('underscore');


export default {
    // name: "ViewPort",
    components: {
        MetaDataForm
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
            is_modal_add_annotation_active: false,
            annotation_timestamp: null,
            annotation_text: "",
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