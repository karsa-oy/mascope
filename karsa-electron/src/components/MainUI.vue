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
            <!-- Experiment tab -->
            <b-tab-item
                icon=""
                :label="this.project_selected.id + '/' + this.experiment_selected.id">
                <!-- :visible="this.experiment_selected.id !== ''"> -->
                <div class="columns">
                    <!-- Left column -->
                    <div class="column is-one-quarter" style="padding-left:2rem">

                        <!-- Namespace selector -->
                        <div style="text-align:center;
                                    margin-top:.4rem;
                                    margin-bottom:1rem;">
                            <b-field label="Data source">
                                <b-select
                                    v-model="data_source_name_selected"
                                    placeholder="Select data source"
                                    expanded>
                                    <option
                                        v-for="source in data_sources"
                                        :value="source.name"
                                        :key="source.name">
                                        {{ source.name }}
                                    </option>
                                </b-select>
                            </b-field>
                        </div>
                        <!-- End of namespace selector -->

                        <H5import
                            v-if="data_source_selected.type && data_source_selected.type.indexOf('h5_streamer') != -1">
                        </H5import>
                        <RAWimport
                            v-if="data_source_selected.type && data_source_selected.type.indexOf('raw_streamer') != -1">
                        </RAWimport>
                        <TOFControl
                            v-if="data_source_selected.type && data_source_selected.type.indexOf('Tofwerk_streamer') != -1">
                        </TOFControl>
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
import H5import from './H5import'
import RAWimport from './RAWimport'
import SampleView from "./SampleView.vue"
import SampleBrowser from "./SampleBrowser.vue"
import TargetBrowser from "./TargetBrowser.vue";
import TOFControl from "./TOFControl.vue"
import store from '../store';
import {BECom, read_dotenv, write_dotenv} from "../karsalib.js"

const _ = require("underscore")

export default {
    name: "MainUi", //used as app_name - keep it unique
    store,
    components: {
        ConfigVue,
        H5import,
        RAWimport,
        SampleBrowser,
        SampleView,
        TargetBrowser,
        TOFControl,
    },
    data() {
        return {
            active_tab: 2,
            dotenv: {},
            be: null,
            room_sid: null,
            // endpoints - list of notifications the MainUI wants to receive
            endpoints: [
                'instrument_data',
                'room_mate_gone',
            ],
            instrument_data: {},
            instrument_data_queue: Promise.resolve(),
            room_mate_gone: null,
            data_source_name_selected: null,
            data_sources: [],
            room_data_sources: 'room_data_sources',

        };
    },
    computed: {
        ...mapState([
            'experiment_selected',
            'project_selected',
            ]),
        root_namespace: {
            get() {
                return this.$store.state.root_namespace;
            },
            set(value) {
                this.$store.commit('root_namespace', value);
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
        data_source_selected: {
            get() {
                return this.$store.state.data_source_selected;
            },
            set(value) {
                this.$store.commit('data_source_selected', value);
            }
        },
    },
    created() {
        this.be = new BECom(this);
        this.dotenv = read_dotenv();
        this.url = this.dotenv.protocol + "//" + this.dotenv.host + ":" + this.dotenv.port;
    },
    methods: {
        filter_data_sources_prop(name, value) {
            return this.data_sources.filter(o => {return o[name] === value});
        },
        on_instrument_data: function(new_value) {
            if ( !new_value.name ||
                 !_.isEmpty(this.filter_data_sources_prop('name', new_value.name)) )
                return false;
            this.data_sources.push(new_value);
        },

    },

    // watchers for internal notifications 
    // watchers also see changes from external notifications, if any
    watch: {
        url: function(new_url) {
            // Connect to new url
            this.be.disconnect(this.root_namespace);
            this.root_namespace = this.be.connect();
            // Parse url into dotenv format and write to file
            let url_obj = new URL(new_url);
            this.dotenv.protocol = url_obj.protocol;
            this.dotenv.host = url_obj.hostname;
            this.dotenv.port = url_obj.port;
            write_dotenv(this.dotenv);
        },
        data_source_name_selected: function(new_value, old_value) {
            if ( new_value === old_value )
                return false;
            this.data_source_selected = this.filter_data_sources_prop('name', new_value)[0];
        },
        instrument_data: function(new_value) {
            var self = this;
            self.instrument_data_queue = self.instrument_data_queue.then(function() {
                return self.on_instrument_data(new_value); }
            );
        },
        room_mate_gone: async function() {
            this.data_sources = [];
            await this.be.emit_client_notification('instrument_data_request',
                                             {},
                                             this.room_data_sources,
                                             this.room_data_sources
                                            );
        },
        'root_namespace.connected': function(new_value) {
            if ( new_value === true )
            {
                // handlers for for external notifications:
                this.root_namespace.on("instrument_data", (value) => this.be.import_one_way_binding_prop("instrument_data", value.value));
                this.root_namespace.on("room_mate_gone", (value) => this.be.import_one_way_binding_prop("room_mate_gone", {...value.value, 'uid': Math.random()}));
                this.be.subscribe(this.endpoints, this.room_data_sources);
            }
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
.detail-container {
    color: black;
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
.menu-label {
    color: white;
}
.menu-list a{
    color: #ababab;
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
    font-size: 15px;
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
ul {
    list-style: none;
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
