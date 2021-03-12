<template>
    <section>
        <div class="columns">
            <div class="column is-on-third">
            </div>
            <div class="column is-on-third">
                <b-field
                    label="URL"
                    :type="url_connected ? 'is-success' : 'is-danger'">
                    <b-input
                        v-model="url"
                        lazy>
                    </b-input>
                </b-field>
            </div>
            <div class="column is-on-third">
            </div>
        </div>
    </section>
</template>

<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from 'vuex'
import Buefy from "buefy";

import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';

Vue.use([Buefy]);

export default {
    name: "ConfigVue",
    components: {
    },
    props: [
    ],
    computed: {
        ...mapState([
            'root_namespace',
        ]),
        url: {
            get() {
                return this.$store.state.url;
            },
            set(value) {
                this.$store.commit('url', value);
            }
        },
    },
    data: function() {
        return {
            url_connected: false,
        }
    },
    watch: {
        'root_namespace.connected': function(new_value) {
            this.url_connected = new_value;
        }
    }
}

</script>
