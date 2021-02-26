<template>
    <div>
        <b-tabs
            class="tabs-main"
            v-model="active_tab"
            :animated="false"
            type="is-boxed main-tab">
        <!-- Tabs -->
            <!-- Config tab -->
            <b-tab-item
                icon="settings"
                label="">
                <ConfigVue></ConfigVue>
            </b-tab-item>
            <!-- Start tab -->
            <b-tab-item
                icon=""
                label="Start">
                <StartTab></StartTab>
            </b-tab-item>
            <!-- Experiment tab -->
            <b-tab-item
                icon=""
                :label="this.project_selected.id + '/' + this.experiment_selected.id"
                :visible="this.experiment_selected.id !== ''">
                <div class="columns">
                    <!-- Left column -->
                    <div class="column is-one-quarter" style="padding-left:2rem">
                        <TOFControl></TOFControl>
                        <SampleBrowser></SampleBrowser>
                        <TargetBrowser></TargetBrowser>
                    </div>
                    <!-- End of left column -->
                    <!-- Right side content -->
                    <div class="column is-three-quarters" style="padding-right:2rem">
                        <SampleView></SampleView>
                    </div>
                    <!-- End of Right side content -->
                </div>
            </b-tab-item>
        <!-- End of tabs -->
        </b-tabs>
    </div>
</template>

<script type="text/javascript">
import { mapState } from 'vuex';
import ConfigVue from './ConfigVue'; 
import StartTab from "./StartTab.vue";
import TargetBrowser from "./TargetBrowser.vue";
import SampleView from "./SampleView.vue"
import SampleBrowser from "./SampleBrowser.vue"
import TOFControl from "./TOFControl.vue"
import store from '../store';

import {export_one_way_binding_prop,
        export_two_way_binding_prop,
        import_one_way_binding_prop,
        import_two_way_binding_prop,
        log,
        read_dotenv,
        write_dotenv} from "../karsalib.js"

const io = require("socket.io-client");

export default {
    name: "MainUi", //used as app_name - keep it unique
    store,
    components: {
        ConfigVue,
        StartTab,
        TargetBrowser,
        SampleBrowser,
        SampleView,
        TOFControl,
    },
    data() {
        return {
            // socket: null,
            dotenv: {},
            // rooms - list of notifications the MainUI wants to receive
            rooms: [
                'acquisition_started',
                'acquisition_status',
                'acquisition_progress',
                'experiments',
                'figure_ranges',
                'h5_samples',
                'h5_streamer_status',
                'heatmap_figure_data',
                'importable_samples',
                'instrument_status',
                'projects',
                'sample_length',
                'samples',
                'spec_stack_figure_data',
                'target_table_data',
                'targets',
                'timeseries_figure_data',
                'tps_parameters',
            ],
            external_notifications: [],
        };
    },
    computed: {
        ...mapState([
            'experiment_selected',
            'h5_to_import',
            'import_h5_table_datetime_range',
            'import_sample_table_datetime_range',
            'project_selected',
            'sample_attributes',
            'target_list_request',
            'target_to_display',
            'tps_parameters_selected',
            'visualize_range',
            'stop_visualize_range',
            ]),
        active_tab: {
            get() {
                return this.$store.state.active_tab;
            },
            set(value) {
                this.$store.commit('active_tab', value);
            }
        },
        acquisition_started: {
            get() {
                return this.$store.state.acquisition_started;
            },
            set(value) {
                this.$store.commit('acquisition_started', value);
            }
        },
        acquisition_status: {
            get() {
                return this.$store.state.acquisition_status;
            },
            set(value) {
                this.$store.commit('acquisition_status', value);
            }
        },
        acquisition_progress: {
            get() {
                return this.$store.state.acquisition_progress;
            },
            set(value) {
                this.$store.commit('acquisition_progress', value);
            }
        },
        experiments: {
            get() {
                return this.$store.state.experiments;
            },
            set(value) {
                this.$store.commit('experiments', value);
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
        h5_samples: {
            get() {
                return this.$store.state.h5_samples;
            },
            set(value) {
                this.$store.commit('h5_samples', value);
            }
        },
        h5_streamer_status: {
            get() {
                return this.$store.state.h5_streamer_status;
            },
            set(value) {
                this.$store.commit('h5_streamer_status', value);
            }
        },
        heatmap_figure_data: {
            get() {
                return this.$store.state.heatmap_figure_data;
            },
            set(value) {
                this.$store.commit('heatmap_figure_data', value);
            }
        },
        importable_samples: {
            get() {
                return this.$store.state.importable_samples;
            },
            set(value) {
                this.$store.commit('importable_samples', value);
            }
        },
        instrument_status: {
            get() {
                return this.$store.state.instrument_status;
            },
            set(value) {
                this.$store.commit('instrument_status', value);
            }
        },
        projects: {
            get() {
                return this.$store.state.projects;
            },
            set(value) {
                this.$store.commit('projects', value);
            }
        },
        samples: {
            get() {
                return this.$store.state.samples;
            },
            set(value) {
                this.$store.commit('samples', value);
            }
        },
        sample_length: {
            get() {
                return this.$store.state.sample_length;
            },
            set(value) {
                this.$store.commit('sample_length', value);
            }
        },
        socket: {
            get() {
                return this.$store.state.socket;
            },
            set(value) {
                this.$store.commit('socket', value);
            }
        },
        spec_stack_figure_data: {
            get() {
                return this.$store.state.spec_stack_figure_data;
            },
            set(value) {
                this.$store.commit('spec_stack_figure_data', value);
            }
        },
        targets: {
            get() {
                return this.$store.state.targets;
            },
            set(value) {
                this.$store.commit('targets', value);
            }
        },
        timeseries_figure_data: {
            get() {
                return this.$store.state.timeseries_figure_data;
            },
            set(value) {
                this.$store.commit('timeseries_figure_data', value);
            }
        },
        tps_parameters: {
            get() {
                return this.$store.state.tps_parameters;
            },
            set(value) {
                this.$store.commit('tps_parameters', value);
            }
        },
        url: {
            get() {
                return this.$store.state.url;
            },
            set(value) {
                this.$store.commit('url', value);
            }
        },
    },
    methods: {
        connect_socket() {
            var self = this;
            log(this.$options.name, "Connecting to url: ", self.url);
            // Global namespace
            self.socket = io.connect(self.url);
            self.socket.on("connect", () => {
                self.socket.emit('subscribe',
                                {'app_name': self.$options.name,
                                 'endpoints': self.rooms,
                                 'room': self.socket.id});
                // handlers for for external notifications:
                // input value as object {name, value, cookies, no_data_logging...}
                self.socket.on("samples", (value) => import_one_way_binding_prop(self, "samples", value.value));
                self.socket.on("h5_samples", (value) => import_one_way_binding_prop(self, "h5_samples", value.value));
                self.socket.on("h5_streamer_status", (value) => import_one_way_binding_prop(self, "h5_streamer_status", value.value));
                self.socket.on("importable_samples", (value) => import_one_way_binding_prop(self, "importable_samples", value.value));
                self.socket.on("target_table_data", (value) => import_one_way_binding_prop(self, "target_table_data", value.value));
                self.socket.on("targets", (value) => import_one_way_binding_prop(self, "targets", value.value));
                self.socket.on("figure_ranges", (value) => import_one_way_binding_prop(self, "figure_ranges", {...value.value, 'uid': Math.random()}));
                self.socket.on("tps_parameters", (value) => import_one_way_binding_prop(self, "tps_parameters", value.value));
                self.socket.on("heatmap_figure_data", (value) => import_one_way_binding_prop(self, "heatmap_figure_data", value.value));
                self.socket.on("timeseries_figure_data", (value) => import_one_way_binding_prop(self, "timeseries_figure_data", value.value));
                self.socket.on("spec_stack_figure_data", (value) => import_one_way_binding_prop(self, "spec_stack_figure_data", value.value));
                self.socket.on("projects", (value) => import_two_way_binding_prop(self, "projects", value.value));
                self.socket.on("experiments", (value) => import_two_way_binding_prop(self, "experiments", value.value));


                self.socket.on("acquisition_started", (value) => import_one_way_binding_prop(self, "acquisition_started", value.value));
                self.socket.on("acquisition_status", (value) => import_two_way_binding_prop(self, "acquisition_status", value.value));
                self.socket.on("acquisition_progress", (value) => import_one_way_binding_prop(self, "acquisition_progress", value.value, true));
                self.socket.on("instrument_status", (value) => import_one_way_binding_prop(self, "instrument_status", value.value));
                self.socket.on("sample_length", (value) => import_two_way_binding_prop(self, "sample_length", value.value));


                // if MainUI was restarted, get latest state variables from other running services
                self.socket.emit('client_notification', {'name': 'service_state', 'value': {}, 'room': self.socket.id});
                this.$buefy.toast.open({
                    message: 'Socket connected!',
                    type: 'is-success'
                })
            });
            // no need to unsubscribe on disconnect - client is unsubscribed by framework
            self.socket.on("disconnect", () => {
                log(this.$options.name, "socket disconnected");
            });
        },

    },

    created() {
        this.dotenv = read_dotenv();
        this.url = this.dotenv.protocol + "//" + this.dotenv.host + ":" + this.dotenv.port;
        this.connect_socket();
    },

    // watchers for internal notifications 
    // watchers also see changes from external notifications, if any
    watch: {
        // /tof namespace notifications
        acquisition_status: function(new_value, old_value) {
            // // TODO: Very hacky way to deal with /tof namespace
            // let ctx = {'external_notifications': this.external_notifications,
            //            'socket': this.socket_tof
            //            };
            // return export_two_way_binding_prop(ctx, 'acquisition_status', new_value, old_value, true);
            return export_two_way_binding_prop(this, 'acquisition_status', new_value, old_value, true);
        },
        sample_length: function(new_value, old_value) {
            // // TODO: Very hacky way to deal with /tof namespace
            // let ctx = {'external_notifications': this.external_notifications,
            //            'socket': this.socket_tof
            //            };
            // return export_two_way_binding_prop(ctx, 'sample_length', new_value, old_value);
            return export_two_way_binding_prop(this, 'sample_length', new_value, old_value);
        },
        // Global namespace notifications
        experiment_selected: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'experiment_selected', new_value, old_value);
        },
        h5_to_import: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'h5_to_import', new_value, old_value);
        },
        import_h5_table_datetime_range: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'import_h5_table_datetime_range', new_value, old_value);
        },
        import_sample_table_datetime_range: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'import_sample_table_datetime_range', new_value, old_value);
        },
        project_selected: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'project_selected', new_value, old_value);
        },
        sample_attributes: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'sample_attributes', new_value, old_value);
        },
        stop_visualize_range: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'stop_visualize_range', {...new_value, 'uid': Math.random()}, old_value);
        },
        target_list_request: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'target_list_request', new_value, old_value);
        },
        target_to_display: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'target_to_display', new_value, old_value);
        },
        tps_parameters_selected: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'tps_parameters_selected', new_value, old_value);
        },
        url: function(new_url) {
            // Connect to new url
            this.socket.disconnect();
            this.connect_socket();
            // Parse url into dotenv format and write to file
            let url_obj = new URL(new_url);
            this.dotenv.protocol = url_obj.protocol;
            this.dotenv.host = url_obj.hostname;
            this.dotenv.port = url_obj.port;
            write_dotenv(this.dotenv);
        },
        visualize_range: function(new_value, old_value) {
            return export_one_way_binding_prop(this, 'visualize_range', {...new_value, 'uid': Math.random()}, old_value);
        },
    }
}
</script>

<style scoped>
    #app{
        text-align: left; 
    }
</style>

<style>
html{
    background-color:  #29282e!important;
    color: #dfdfdf;  
}
#app {
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  /* text-align: center; */
}
body::-webkit-scrollbar {
    display: none;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    margin: auto;
    font-size: 0.8rem;
    height:90vh;
    /* max-width: 38rem; */
    /* padding: 2rem; */
}
/* Style the tab */
.menubar{
    -webkit-app-region: drag;
}
.tabs{
    padding-top: 5px; 
    /* border-top:15px solid #29282e;  */
}
/* .tabs>ul>li{
    -webkit-app-region: no-drag;
} */
/* Style the buttons that are used to open the tab content */
/* .tab button {
    background-color: inherit;
    float: left;
    border: none;
    outline: none;
    cursor: pointer;
    padding: 14px 16px;
    transition: 0.3s;
} */

/* Change background color of buttons on hover */
/* .tab button:hover {
    background-color: #ddd;
} */

/* Create an active/current tablink class */
/* .tab button.active {
    background-color: #ccc;
} */

/* Style the tab content */
/* .tabcontent {
    display: none;
    padding: 6px 12px;
    border: 1px solid #ccc;
    border-top: none;
    height: 93vh; 
} */
#header-container{
    display:none; 
}
#spacer{
    margin-right:10px;
}
.head{
    background-color: #000;
    color: #dfdfdf;
}
.b-tabs .tabs {
    background-color: #29282e;
}
.tabs a{
    color: #dfdfdf;
    padding: .3em 1em;
}
.tabs li.is-active a {
    /* border-bottom-color: #ccc; */
    color: #000;
}
.columns:not(:last-child){
    margin-bottom: 0px; 
}
.b-tabs .tab-content {
    padding-bottom: 5px;
    padding-left: 5px; 
    /* border-bottom: 1px solid #ccc; */
    padding-top: 10px;
    padding-right:0px;
}
.column{
    padding-bottom: 0px; 
}
#logo{
    padding-left:20px;
    padding-bottom:40px;
}
/* .subtitle{
    color:#dfdfdf;
} */
.label, .gl-container, .ytick, .xtick, span, label{
    user-select:none;
}
.modebar, .modebar--hover, .ease-bg{
    user-select:none;
}
.ytick, .xtick{
    font-size:.3rem;
}
.label {
    display: block;
    font-size: .8rem;
    text-align:center;
    /* font-weight: 600; */
}
.label:not(:last-child) {
    color: #dfdfdf;
    margin-bottom: 0px;
}
.modal-card .label {
    color: #666;
}

.pagination-previous[disabled], .pagination-next[disabled], .pagination-link[disabled] {
    background-color: #545454;
    border-color: #dbdbdb;
    -webkit-box-shadow: none;
    box-shadow: none;
    color: #7a7a7a;
    opacity: 0.5;
}
a.pagination-link.is-current {
    background-color: transparent;
    border-color: #dbdbdb;
}
.icon>.mdi{
    color:#fff;
}
.icon:hover>mdi{
    color: #414242;
}
.mdi:hover {
    color: #414242;
}
.icon:hover>span {
    color: rgb(94, 94, 94);
}
.main-tab>ul>li.is-active>a>span {
    color: #000;
}
.button:hover>span, .button:hover>.icon, .button:hover>.mdi, .button:hover>:first-child, .button:hover>.icon>.mdi{
    color:#000; 
}
.main-tab>ul>li>a:hover>span {
    color: #000000;
}
.main-tab>ul>li>a>span:hover {
    color: #000000;
}
.tabs li.is-active a {
    border-bottom: 5px solid;
    border-bottom-color: #bfbdc5;
    color: #bfbdc5;
}
.idparams-edit-body>.b-tabs{
    overflow:hidden;
}
.peaklist-edit-data-table>.b-table>.level>.level-right>.level-item>.pagination>.pagination-next {
    background-color: #ababab;
}
.peaklist-edit-data-table>.b-table>.level>.level-right>.level-item>.pagination>.pagination-previous {
    background-color: #ababab;
}
.peaklist-edit-data-table>.b-table>.level>.level-right>.level-item>.pagination>.pagination-list>li>.is-current {
    background-color: #ababab;
}
.edit-peaklist-modal>.b-tabs .tab-content {
    overflow:hidden; 
}
/* .tabs.is-boxed li.is-active a {
    background-color:#29282e!important;
    border-color: #ddd;
}*/
.table {
    background-color:transparent; 
    color: inherit;
}
.table:focus {
    outline: none;
}
.table th{
    background-color: transparent;
}
.b-table .table-wrapper.has-sticky-header tr:first-child th {
    background-color: #29282e;
}
.table tr.is-selected {
    background-color: #7c5bd6;
    color: black;
}
/* tr>th{
    background-color:rgb(51, 50, 50); 
} */
.table thead td:hover, .table thead th:hover {
    color: #666;
}
.table tr:hover {
    color: black;
    background-color: white;
}
th>input{
    color:#dfdfdf; 
}
.table thead td, .table thead th {
    color: inherit;
}

.b-slider.is-small .b-slider-tick-label {
    color: aliceblue;
}
#page-content .tab-container .tab{
    width: auto;
    padding:10px 25px 10px 25px;  
    border-bottom:0px; 
    /* width: calc(25% / 2);  */
}
#page-content .tab-container .tab--selected{
    border-bottom:0px; 
    /* width: calc(25% / 2);  */
}
#data-label{
    width: auto; 
    float:left; 
    padding-top: 10px;
    padding-right: 20px;
    line-height: 18px;
}
#data-input{
    width: auto;
    max-width: 40%; 
    float:left; 
}
#data-source-button{
    margin-left:10px; 
    float:left;
}
#data-top-row{
    background-color: #d4dedc;
    padding-bottom: 10px; 
    border-bottom:1px solid #a7a7a7; 
    padding-top: 10px;
    padding-left: 5px;
    margin-bottom:10px;
}
#recursive-option{
    float: left;
    padding-top: 7px;
    margin-left:10px;
    margin-right: 20px;
}
#upload-peaklist-button{
    float:left; 
    margin-left:20px; 
}
#state-div{
    float: left; 
    margin-right:20px;
}
#threshold-slider-,
#mz-error-slider,
#isotope-error-ratio-slider,
#isotope-correlation-ration-slider
{
    margin-left: 1%;
    margin-right: 0.5%;
    float: left; 
    width:23.5%; 
    height: 100px;
    color:"white";
    font-size:12px;
    text-align:center;
}
#clear{
    clear:both;
}
#update-peaklist-db{
    margin-top:5px;
    margin-bottom:5px; 
}
.tr.is-dark {
        background: #167df0;
        color: #fff;
}
#data-table, #target-table{
    overflow:hidden; 
    border: 1px solid #a7a7a7;
    margin-bottom: 10px; 
}
#data-bottom-row-left, #data-bottom-row-right{
    padding: 5px; 
}
#data-figures-row-1, #data-figures-row-2{
    clear: both;
}
#data-figures-row-1-col-1, #data-figures-row-1-col-2,
#data-figures-row-2-col-1, #data-figures-row-2-col-2
{
    width: 50%; 
}
#data-figures-row-1-col-1, #data-figures-row-2-col-1{
    float: left; 
}
#data-figures-row-1-col-2, #data-figures-row-2-col-2{
    float: right; 
}
.slider{
    padding-top:0px;
}
#data-source-and-filters{
    border-top: 1px solid #a7a7a7;
    border-bottom: 1px solid #a7a7a7;
    padding-bottom: 0px;
    padding-left: 3px;
    background-color: #303136!important;
}
#process-button-div{
    margin-top: 0px;
    padding-top:0px;
    margin-left: 0px;
    margin-bottom: 5px;  
}
.scenthound-icons{
    margin-right: 5px;
}
#data-left {
    min-width:20%;
    max-width: 20%;
    overflow: hidden;
    margin-top: 20px;
    margin-left: 10px;
    border: 1px solid #a7a7a7;
    border-radius: 5px; 
    padding: 5px;
    /* min-height:70vh; */
}
#data-right{
    min-width:75%;
    max-width:75%;
    height: 780px;
    /* border: 1px solid #a7a7a7; */
    /* margin-top: 20px; */
    margin-left: 10px;
    margin-right: 20px;
    /* min-height:70vh; */
}

.label {
    user-select: none;
    cursor:default; 
}
.b-slider-tick-label{
    user-select: none; 
}
.edit-peaklist-modal>.modal-card-body{
    padding: 0px;
}
.add_edit_peaklistdb_rows_column{
    margin:1px;
}
.add_edit_idparams_rows{
    border: 1px solid rgb(185, 180, 180);
    border-radius: 5px;
    margin:0px; 
    padding:0px; 
    padding-bottom:10px;
    margin-bottom: 5px; 
}
</style>
