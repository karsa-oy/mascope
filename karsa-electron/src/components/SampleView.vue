<template>
    <div>

        <!-- Main content  area-->
        <section>
            <div class="columns">

                <!-- Left side -->
                <div class="column is-half">
                    <!-- Heatmap section -->
                    <section class="heatmap-section">
                        <div class="column datashader-heatmap">
                            <div class="loading-heatmap">
                                <!-- placeholder for headmap loading div -->
                            </div>
                            <div id="heatmap-figure"></div>
                        </div>                                    
                    </section>
                    <!-- End of heatmap section-->
                    <!-- Multiselect section -->
                    <section class="multiselect-section">
                        <div class="column tps-multiselect">
                            <h2 class="multiselect-title">Select parameter to display</h2>
                            <multiselect 
                            v-model="tps_parameters_selected_ui"
                            tag-placeholder="Add this as new tag" 
                            placeholder="Search or add a tag" 
                            label="label" 
                            track-by="value" 
                            :options="tps_parameters" 
                            :multiple="true" 
                            :taggable="true"
                            ></multiselect>
                        </div>                                    
                    </section>
                    <!-- End of multiselect section -->
                    <!-- Timeseries section -->
                    <section class="timeseries-section">
                        <div class="column tps-chart"> 
                            <div id="timeseries-figure"></div>
                        </div>                                    
                    </section>
                    <!-- End of timeseries -->
                </div>

                <!-- Right side -->
                <div class="column is-half">
                    <!-- Spec stack section -->
                    <section class="spect-stack-section">
                        <div class="column spec-stack-holder">
                            <div id="spec-stack-figure"></div>
                        </div>                            
                    </section>
                    <!-- End of spec stack chart -->
                </div>

            </div>
        </section>

    </div>
</template>


<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from 'vuex'
import Buefy from "buefy";
import Multiselect from "vue-multiselect";

import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';

Vue.use([Buefy]);

var fs = require('fs');
var Plotly = require('plotly.js-dist');
var _ = require('underscore');
var mergeImages = require('merge-base64');

//var dialog = require("electron").remote.dialog;
//var remote = require('electron').remote;


export default {
    name: "SampleView",
    components: {
        // using third party multiselect component
        Multiselect
    },
    props: {
    },
    computed: {
        ...mapState(['acquisition_status',
                     'data_source_path',
                     'heatmap_figure_data',
                     'sample_to_load',
                     'spec_stack_figure_data',
                     'target_to_display',
                     'timeseries_figure_data',
                     ]),
        figure_ranges: {
            get() {
                return this.$store.state.figure_ranges;
            },
            set(value) {
                this.$store.commit('figure_ranges', value);
            }
        },
        visualize_range: {
            get() {
                return this.$store.state.visualize_range;
            },
            set(value) {
                this.$store.commit('visualize_range', value);
            }
        },
        tps_parameters_selected_ui: {
            get() {
                return this.$store.state.tps_parameters_selected['tps_parameters_selected'];
            },
            set(value) {
                let new_value = {'tps_parameters_selected': value, 'figure_ranges': this.figure_ranges};
                this.$store.commit('tps_parameters_selected', new_value);
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
    },
    data: function() {
        return {
            // State variables
            cache_index_rank: 0, // actual value calculated in "mounted"
            figure_cache: {'t_maxrange': [0, 0], 'mz_maxrange': [0, 0]},
            figure_layouts: {},
            filename: '',
            grid_spacing: 0.0049,
            heatmap_data: [],
            heatmap_layout: {},
            heatmap_queue: Promise.resolve(),
            spec_stack_data: [],
            spec_stack_layout: {},
            timeseries_data: [],
            timeseries_layout: {},
            zoom_stack: [],
        }
    },
    created: function(){
    },

    mounted: function() {
        this.init_figures();
        this.cache_index_rank = Math.floor(-Math.log10(this.grid_spacing));
    },

    methods: {
        log: function(...args) {
            console.log('[' + this.$options.name + ']',  ...args);
        },
        beep: function() {
            var snd = new Audio("data:audio/mp3;base64,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\
            sLivwKKigsj8XYlwt/WKi2N4d//uQRCSAAjURNIHpMZBGYiaQPSYyAAABLAAAAAAAACWAAAAApUF/Mg+0aohSI\
            RobBAsMlO//Kk4soosy1JSFRYWaLC4qZBYWFRGZdwqKiwkNBVmoWFSJkWFxX4FFRQWR+LsS4W/rFRb////////\
            //////////////////////////////////////////////////////////////////////////////////////\
            //////////////////////////////////////////////////////////////////////////////////////\
            //////////////////////////////////////////////////////////////////////////////////////\
            //////////////////////////////////////////////////////////////////////////////////////\
            /////////////////////////////////////////////////////////////////VEFHAAAAAAAAAAAAAAAAA\
            AAAAAAAAAAAAAAAAAAAAAAAU291bmRib3kuZGUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
            AAAAAAAAAAAAAAAAAMjAwNGh0dHA6Ly93d3cuc291bmRib3kuZGUAAAAAAAAAACU=");
            snd.play();
        },
        init_figures() {
            // This function reads figure layouts from config file, creates
            // the Plotly figures and configures event handlers

            var self = this;
            // Read layouts from config file
            if (fs.existsSync('configs/figure_layouts.json')) {
                self.figure_layouts = JSON.parse(fs.readFileSync('configs/figure_layouts.json', 'utf8'));
                self.figure_config = self.shallow_copy(self.figure_layouts.figure_config);
                self.heatmap_layout = self.shallow_copy(self.figure_layouts.heatmap_layout);
                self.timeseries_layout = self.shallow_copy(self.figure_layouts.timeseries_layout);
                self.spec_stack_layout = self.shallow_copy(self.figure_layouts.spec_stack_layout);
            }

            // Common config for all figures
            var init_data = [{x: [0, 1],
                              y: [0, 1],
                              type: "scattergl",
                              mode: 'markers',
                              marker: {opacity: 0.0},
                              hoverinfo: 'skip',
                              }];

            // ===== Initialize Plotly figures =====
            // ---- Heatmap -----
            var heatmap_figure = document.getElementById("heatmap-figure");
            Plotly.newPlot(heatmap_figure,
                           init_data,
                           self.heatmap_layout,
                           {...self.figure_config, "doubleClick": false}
                           );
            // Relayout event
            heatmap_figure.on("plotly_relayout", function(eventData) {
                if ( _.isEmpty(eventData) ) {
                    // Likely a double-click event
                    return;
                }
                if ( _.isEqual(eventData, {'autosize': true}) ) {
                    // Figure resize event
                    return;
                }

                if ( Object.keys(eventData).length ) {
                    // zoom_in

                    let prev_ranges = self.shallow_copy(self.zoom_stack.slice(-1)[0]);
                    let x0 = eventData["xaxis.range[0]"];
                    let x1 = eventData["xaxis.range[1]"];
                    let y0 = eventData["yaxis.range[0]"];
                    let y1 = eventData["yaxis.range[1]"];
                    if( _.isUndefined(prev_ranges) &&
                        _.isUndefined(x0) && _.isUndefined(x1) &&
                        _.isUndefined(y0) && _.isUndefined(y1) )
                        return;

                    x0 = (x0 === undefined) ? prev_ranges.t_range[0] : x0;
                    x1 = (x1 === undefined) ? prev_ranges.t_range[1] : x1;
                    y0 = (y0 === undefined) ? prev_ranges.mz_range[0] : y0;
                    y1 = (y1 === undefined) ? prev_ranges.mz_range[1] : y1;
                    let ranges = {};
                    ranges.t_range = [x0, x1];
                    ranges.mz_range = [y0, y1];

                    self.visualize_range_on_zoom_in(prev_ranges, ranges);
                }
            });

            // Double click event
            heatmap_figure.on('plotly_doubleclick', function(){
                // Zoom one step out
                self.visualize_range_on_zoom_out();
            });

            // Right click event
            heatmap_figure.addEventListener('contextmenu', function(ev) {
                ev.preventDefault();
                this.log("Right click event....");
                return false;
            }, false);
            // ----- End of heatmap -----


            // ----- Spec stack -----
            var spec_stack_figure = document.getElementById("spec-stack-figure");
            Plotly.newPlot(spec_stack_figure,
                           init_data,
                           self.spec_stack_layout,
                           {...self.figure_config, "doubleClick": false}
                           );
            // Relayout event
            spec_stack_figure.on("plotly_relayout", function(eventData) {
                if ( _.isEmpty(eventData) ) {
                    // Likely a double-click event
                    return;
                }
                if ( _.isEqual(eventData, {'autosize': true}) ) {
                    // Figure resize event
                    return;
                }
                if ( Object.keys(eventData).length ) {
                    // zoom_in
                    let prev_ranges = self.shallow_copy(self.zoom_stack.slice(-1)[0]);
                    let x0 = eventData["xaxis.range[0]"];
                    let x1 = eventData["xaxis.range[1]"];
                    let y0 = eventData["yaxis.range[0]"];
                    let y1 = eventData["yaxis.range[1]"];
                    if( _.isUndefined(prev_ranges) &&
                        _.isUndefined(x0) && _.isUndefined(x1) &&
                        _.isUndefined(y0) && _.isUndefined(y1) )
                        return;

                    x0 = (x0 === undefined) ? prev_ranges.mz_range[0] : x0;
                    x1 = (x1 === undefined) ? prev_ranges.mz_range[1] : x1;
                    y0 = (y0 === undefined) ? prev_ranges.t_range[0] : y0;
                    y1 = (y1 === undefined) ? prev_ranges.t_range[1] : y1;
                    let ranges = {};
                    ranges.mz_range = [x0, x1];
                    ranges.t_range = [y0, y1];

                    self.visualize_range_on_zoom_in(prev_ranges, ranges);
                }
            });
            // Double click event
            spec_stack_figure.on('plotly_doubleclick', function(){
                // On double-click, zoom one step out
                self.visualize_range_on_zoom_out();
            });
            // Right click event
            spec_stack_figure.addEventListener('contextmenu', function(ev) {
                ev.preventDefault();
                this.log("Right click event....");
                return false;
            }, false);

            // ----- Timeseries figure -----
            Plotly.newPlot("timeseries-figure",
                        self.timeseries_data,
                        self.timeseries_layout,
                        self.figure_config
                        );
        },


        async _on_figure_ranges(new_value, old_value) {
            // if ( !_.isEmpty(this.filename) && this.filename != new_value.filename ) {
            //     this.log("Error: figure_ranges notification for invalid file:", new_value.filename)
            //     return false;
            // }
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if ( this.filename != new_value.filename ) {
                this.filename = new_value.filename;
                this.reset_figures();
                this.reset_figure_cache();
            }

            let t0 = new_value.t_range[0];
            t0 = (!_.isNull(t0)) ? t0 : old_value.t_range[0];
            let t1 = new_value.t_range[1];
            t1 = (!_.isNull(t1)) ? t1 : old_value.t_range[1];
            let mz0 = new_value.mz_range[0];
            mz0 = (!_.isNull(mz0)) ? mz0 : old_value.mz_range[0];
            let mz1 = new_value.mz_range[1];
            mz1 = (!_.isNull(mz1)) ? mz1 : old_value.mz_range[1];

            [mz0, mz1, t0, t1] = this.adjust_ranges_to_grid_spacing(mz0, mz1, t0, t1);

            this.figure_cache.t_maxrange[0] = Math.min(t0, this.figure_cache.t_maxrange[0]);
            this.figure_cache.t_maxrange[1] = Math.max(t1, this.figure_cache.t_maxrange[1]);
            this.figure_cache.mz_maxrange[0] = Math.min(mz0, this.figure_cache.mz_maxrange[0]);
            this.figure_cache.mz_maxrange[1] = Math.max(mz1, this.figure_cache.mz_maxrange[1]);

            this.figure_cache_add_ref([mz0, mz1]);
            this.zoom_stack.push(new this.ZoomStackItem([t0, t1], [mz0, mz1]));
            let cur_zoom = this.shallow_copy(this.zoom_stack.slice(-1)[0]);
            this.update_figures(cur_zoom);
        },

        on_figure_ranges(new_value, old_value) {
            var self = this;
            self.heatmap_queue = self.heatmap_queue.then(function() {
                return self._on_figure_ranges(new_value, old_value); }
            );
        },


        async _on_heatmap_figure_data(json_data) {
            var self = this;
            if ( _.isEmpty(json_data) ) {
                // reset the figure
                self.heatmap_layout = self.shallow_copy(self.figure_layouts.heatmap_layout);
                self.heatmap_data = [];
                await Plotly.react("heatmap-figure", self.heatmap_data, self.heatmap_layout);
                return;
            }
            else {
                // if ( self.filename != json_data.filename )
                //     return;

                var x0 = json_data.t_range[0]; // float
                var x1 = json_data.t_range[1]; // float
                var y0 = json_data.mz_range[0]; // float
                var y1 = json_data.mz_range[1]; // float
                var img = json_data.img; // base64 png
                var traces = json_data.traces; // array

                let chunk = {
                    "source": img,
                    "xref": "x",
                    "yref": "y",
                    "x": x0,
                    "y": y0,
                    "sizex": x1 - x0,
                    "sizey": y1 - y0,
                    "xanchor": "left",
                    "yanchor": "bottom",
                    "sizing": "stretch",
                    "layer": "below"
                };

                [x0, x1, y0, y1] = self.adjust_ranges_to_grid_spacing(x0, x1, y0, y1);

                let mz_range = [y0, y1];
                var cache_item = self.get_figure_cache_item(mz_range);
                if ( _.isUndefined(cache_item) ) {
                    self.beep();
                    self.log('on_heatmap_figure_data: retired frame skipped for mz_range', mz_range, this.figure_cache, this.zoom_stack);
                    return;
                }
                cache_item.heatmap_layout.images.push(chunk);
                cache_item.t_filled_range[0] = Math.min(x0, cache_item.t_filled_range[0]);
                cache_item.t_filled_range[1] = Math.max(x1, cache_item.t_filled_range[1]);

                // if latest zoom stack item updated, then draw the figure
                if ( _.isEqual(cache_item.mz_range,
                               self.to_figure_cache_index(self.zoom_stack.slice(-1)[0].mz_range)) ) {
                    if (traces) {
                        for (let i=0; i<traces.length; i++) {
                            self.heatmap_data.push(traces[i]);
                        }
                    }
                    self.heatmap_layout = cache_item.heatmap_layout;
                    await Plotly.react("heatmap-figure",
                                        self.heatmap_data,
                                        self.heatmap_layout
                                        );
                } else if (_.isEqual(cache_item.mz_range, self.to_figure_cache_index(self.zoom_stack[0].mz_range)) &&
                            self.acquisition_status === "running") {
                    // on newly acquired spectrum (full mz range, acquisition running),
                    // forward request to latest zoom
                    self.visualize_range = {'mz_range': self.zoom_stack.slice(-1)[0].mz_range,
                                            't_range': [x0, x1],
                                            'filename': this.filename};
                }
            }
        },

        on_heatmap_figure_data(json_data) {
            var self = this;
            self.heatmap_queue = self.heatmap_queue.then(function() {
                return self._on_heatmap_figure_data(json_data); }
            );
        },


        async merge_heatmap_layout(nimg, img_to_append) {
        // merge last nimg images from heatmap_layout and append img_to_append
            var self = this;
            let [ , x1, y0, y1, img] = img_to_append;
            let _x = self.heatmap_layout.images.slice(-nimg)[0].x;
            let _sizex = x1 - _x;
            var _y = y0;
            var _sizey = y1 - y0;
            var images = [];
            var prefix = ['data:image/png;base64,', 'data:image/jpeg;base64,'];
            for (let i=0; i<nimg; ++i) {
                let image = self.heatmap_layout.images.pop();
                if ( _.isEmpty(image) )
                    break;
                _y = Math.min(image.y, _y);
                _sizey = Math.max(image.sizey, _sizey);
                images = [image.source.replace(prefix[0], '').replace(prefix[1], ''), ...images];
            }
            images = [...images, img.replace(prefix[0], '').replace(prefix[1], '')];
            let opts = {direction: false, align: 'start'};
            let _source = await mergeImages(images, opts);
            return [_x, _sizex, _y, _sizey, _source];
        },

        async _on_spec_stack_figure_data(json_data) {
            var self = this;
            if ( _.isEmpty(json_data) ) {
                // reset the figure
                self.spec_stack_layout = self.shallow_copy(self.figure_layouts.spec_stack_layout);
                self.spec_stack_data = [];
                await Plotly.react("spec-stack-figure", self.spec_stack_data, self.spec_stack_layout);
            }
            else {
                // if ( self.filename != json_data.filename )
                //     return;

                var x0 = json_data.mz_range[0]; // float
                var x1 = json_data.mz_range[1]; // float
                var y0 = json_data.t_range[0]; // float
                var y1 = json_data.t_range[1]; // float
                var img = json_data.img; // base64 png
                // var traces = json_data.traces; // array

                let chunk = {
                    "source": img,
                    "xref": "x",
                    "yref": "y",
                    "x": x0,
                    "y": y0,
                    "sizex": x1 - x0,
                    "sizey": 1e4,           // number >= actual image height [px]
                    "xanchor": "left",
                    "yanchor": "bottom",
                    "sizing": "contain",    // to display native height
                    "layer": "below",
                };

                [x0, x1, y0, y1] = self.adjust_ranges_to_grid_spacing(x0, x1, y0, y1);

                let mz_range = [x0, x1];
                var cache_item = self.get_figure_cache_item(mz_range);
                if ( _.isUndefined(cache_item) ) {
                    self.beep();
                    self.log('on_spec_stack_figure_data: retired frame skipped for mz_range', mz_range, this.figure_cache, this.zoom_stack);
                    return;
                }
                cache_item.spec_stack_layout.images.push(chunk);
                cache_item.spec_stack_layout.yaxis.tickvals.push(y0);
                cache_item.spec_stack_layout.yaxis.ticktext.push(y0.toFixed(1).toString());

                // if latest zoom stack item updated, then draw the figure
                if ( _.isEqual(self.to_figure_cache_index(mz_range), 
                               self.to_figure_cache_index(self.zoom_stack.slice(-1)[0].mz_range)) ) {
                    // if (traces) {
                    //     for (let i=0; i<traces.length; i++) {
                    //         self.spec_stack_data.push(traces[i]);
                    //     }
                    // }
                    self.spec_stack_layout = cache_item.spec_stack_layout;
                    await Plotly.update("spec-stack-figure",
                                        self.spec_stack_data,
                                        self.spec_stack_layout
                                        );
                }
            }
        },

        on_spec_stack_figure_data(json_data) {
            var self = this;
            self.heatmap_queue = self.heatmap_queue.then(function() {
                return self._on_spec_stack_figure_data(json_data); }
            );
        },


        async _on_timeseries_figure_data(json_data) {
            var self = this;
            if ( _.isEmpty(json_data) ) {
                // reset the figure
                self.timeseries_layout = self.shallow_copy(self.figure_layouts.timeseries_layout);
                self.timeseries_data = [];
                await Plotly.react("timeseries-figure", self.timeseries_data, self.timeseries_layout);
            }
            else {
                let x0 = json_data.xrange && json_data.xrange[0] 
                x0 = (x0 === undefined) ? self.heatmap_layout.xaxis.range[0] : x0;
                let x1 = json_data.xrange && json_data.xrange[1] 
                x1 = (x1 === undefined) ? self.heatmap_layout.xaxis.range[1] : x1;
                self.timeseries_layout.xaxis.range = [x0, x1];
                
                let traces = json_data.traces || [];
                if (!traces.length) {
                    return
                }

                let trace = traces[0]; // TODO: Need to handle multiple traces?

                let mz_range = json_data.mz_range;

                let y0 = mz_range[0];
                let y1 = mz_range[1];
                [x0, x1, y0, y1] = self.adjust_ranges_to_grid_spacing(x0, x1, y0, y1);
                let _mz_range = [y0, y1];

                let cache_item = self.get_figure_cache_item(_mz_range);
                if ( _.isUndefined(cache_item) ) {
                    self.beep();
                    self.log('_on_timeseries_figure_data: retired frame skipped for mz_range', mz_range, this.figure_cache, this.zoom_stack);
                    return;
                }
                if (cache_item.timeseries_data.length) {
                    // Append existing trace
                    // TODO: Now pushing always to the first trace
                    cache_item.timeseries_data[0].x.push.apply(cache_item.timeseries_data[0].x, trace.x);
                    cache_item.timeseries_data[0].y.push.apply(cache_item.timeseries_data[0].y, trace.y);
                } else {
                    // Add new trace
                    cache_item.timeseries_data.push(trace);
                }

                // if latest zoom stack item updated, then draw the figure
                if ( _.isEqual(self.to_figure_cache_index(_mz_range), 
                        self.to_figure_cache_index(self.zoom_stack.slice(-1)[0].mz_range)) ) {
                    self.timeseries_data = cache_item.timeseries_data;
                    await Plotly.update("timeseries-figure", self.timeseries_data, self.timeseries_layout);
                }
            }

        },

        on_timeseries_figure_data(json_data) {
            var self = this;
            self.heatmap_queue = self.heatmap_queue.then(function() {
                return self._on_timeseries_figure_data(json_data); }
            );
        },

        visualize_range_on_zoom_in(prev_ranges, new_ranges, volatile=false) {
            let self = this;
            if ( _.isUndefined(prev_ranges) || _.isUndefined(new_ranges) ) {
                self.log("visualize_range_on_zoom_in: some of the ranges undefined!");
                return
            }
            // Unpack ranges
            let [mz0, mz1] = new_ranges.mz_range;
            let [t0, t1] = new_ranges.t_range;
            let [pmz0, pmz1] = prev_ranges.mz_range;
            let [pt0, pt1] = prev_ranges.t_range;
            // Make sure new ranges are within bounds
            mz0 = Math.max(mz0, self.figure_cache.mz_maxrange[0]);
            mz1 = Math.min(mz1, self.figure_cache.mz_maxrange[1]);
            t0 = Math.max(t0, self.figure_cache.t_maxrange[0]);
            t1 = Math.min(t1, self.figure_cache.t_maxrange[1]);
            // Adjust new ranges to grid spacing
            [mz0, mz1, t0, t1] = self.adjust_ranges_to_grid_spacing(mz0, mz1, t0, t1);
            // Set min significant zoom ranges
            let min_dmz = 10**(-self.cache_index_rank);
            let min_dt = 1;
            // Check if mz_range has changed
            let mz_range_updated = true;
            if ( (Math.abs(mz1-pmz1) < min_dmz && Math.abs(mz0-pmz0) < min_dmz)
                ) {
                // mz_range has not changed significantly, reset to original
                mz0 = pmz0;
                mz1 = pmz1;
                mz_range_updated = false;
            }
            // Check if t_range has changed
            let t_range_updated = true;
            if ( (Math.abs(t1-pt1) < min_dt && Math.abs(t0-pt0) < min_dt)
                ) {
                // t_range has not changed significantly, reset to original
                t0 = pt0;
                t1 = pt1;
                t_range_updated = false;
            }
            if (!mz_range_updated && !t_range_updated) {
                // No need to zoom, reset to original ranges
                self.beep();
                self.update_figures(prev_ranges);
                return
            }
            // Zoom in
            // Check if requested stack item exists in stack already
            let cache_item = self.get_figure_cache_item([mz0, mz1]);
            if ( !_.isUndefined(cache_item) &&
                 _.isEqual(cache_item.t_filled_range, [t0, t1]) ) {
                // Item already in cache, no need to request image update
                mz_range_updated = false;
            }
            // Add figure cache ref and zoom stack item
            self.figure_cache_add_ref([mz0, mz1]);
            self.zoom_stack.push(
                new self.ZoomStackItem([t0, t1], [mz0, mz1], volatile)
                );
            let cur_ranges = self.shallow_copy(self.zoom_stack.slice(-1)[0]);
            // Set new ranges
            self.update_figures(cur_ranges);
            // Request new visualizations if needed
            if (mz_range_updated) {
                this.visualize_range = {...cur_ranges, 'filename': this.filename};
            }
        },

        visualize_range_on_zoom_out() {
            let self = this;
            if ( this.zoom_stack.length <= 1 ) {
                this.log("Zoom stack is empty.");
                this.beep();
                return
            }
            // reset traces
            self.heatmap_data = [];
            self.spec_stack_data = [];
            // remove last zoom and take current zoom into view
            let zoom_stack_item_to_remove = self.zoom_stack.pop();
            let zoom_stack_item_to_restore = self.shallow_copy(self.zoom_stack.slice(-1)[0]);
            // Loop until persistent item found from zoom stack
            while (zoom_stack_item_to_restore.volatile) {
                // Release reference of popped item
                self.figure_cache_release_ref(zoom_stack_item_to_restore.mz_range);
                // Get next item from stack
                self.zoom_stack.pop();
                zoom_stack_item_to_restore = self.shallow_copy(self.zoom_stack.slice(-1)[0]);
            }
            self.log("Zoom stack frames left:", self.zoom_stack.length - 1);
            if ( _.isUndefined(zoom_stack_item_to_remove) || _.isUndefined(zoom_stack_item_to_restore) )
                return;
            self.update_figures(zoom_stack_item_to_restore);
            // visualize missing frames and acquisition frames
            let prev_mz = zoom_stack_item_to_remove.mz_range;
            let cur_mz = zoom_stack_item_to_restore.mz_range;
            let prev_t_filled = this.get_figure_cache_item(prev_mz).t_filled_range;
            let cur_t_filled = this.get_figure_cache_item(cur_mz).t_filled_range;
            // retro-visualization
            let min_t_gap = 1;
            if ( prev_t_filled[1] - cur_t_filled[1] > min_t_gap) {
                this.visualize_range = {'t_range': [cur_t_filled[1], prev_t_filled[1]],
                                        'mz_range': cur_mz,
                                        'filename': this.filename};
            }
            // remove cache item, if not used anymore
            self.figure_cache_release_ref(zoom_stack_item_to_remove.mz_range);
        },

        shallow_copy(o) {
            let _o = JSON.stringify(o);
            if ( _.isUndefined(_o) )
                return _o;
            return JSON.parse(_o);
        },

        ZoomStackItem: function(t_range, mz_range, volatile=false) {
            this.t_range = t_range;
            this.mz_range = mz_range;
            this.volatile = volatile;
        },

        reset_figures() {
            this.heatmap_layout = this.shallow_copy(this.figure_layouts.heatmap_layout);
            this.heatmap_data = [];
            this.spec_stack_layout = this.shallow_copy(this.figure_layouts.spec_stack_layout);
            this.spec_stack_data = [];
            this.timeseries_layout = this.shallow_copy(this.figure_layouts.timeseries_layout);
            this.timeseries_data = [];
        },

        reset_figure_cache() {
            // this.figure_cache = {'t_maxrange': [Number.MAX_SAFE_INTEGER, 0],
            //                      'mz_maxrange': [Number.MAX_SAFE_INTEGER, 0], };
            this.figure_cache = {'t_maxrange': [0, 0],
                                 'mz_maxrange': [0, 0], };
            this.zoom_stack = [];
        },

        adjust_ranges_to_grid_spacing(x0, x1, y0, y1) {
            let _x0_l = x0 - this.grid_spacing;
            let _x0_r = x0 + this.grid_spacing;
            if ( _x0_l.toFixed(this.cache_index_rank) != _x0_r.toFixed(this.cache_index_rank) ) {
                x0 = _x0_l.toFixed(this.cache_index_rank);
                x0 = parseFloat(Math.abs(x0)); // abs to avoid -0
            }
            let _x1_l = x1 - this.grid_spacing;
            let _x1_r = x1 + this.grid_spacing;
            if ( _x1_l.toFixed(this.cache_index_rank) != _x1_r.toFixed(this.cache_index_rank) ) {
                x1 = _x1_r.toFixed(this.cache_index_rank);
                x1 = parseFloat(x1);
            }
            let _y0_l = y0 - this.grid_spacing;
            let _y0_r = y0 + this.grid_spacing;
            if ( _y0_l.toFixed(this.cache_index_rank) != _y0_r.toFixed(this.cache_index_rank) ) {
                y0 = _y0_l.toFixed(this.cache_index_rank)
                y0 = parseFloat(y0);
            }
            let _y1_l = y1 - this.grid_spacing;
            let _y1_r = y1 + this.grid_spacing;
            if ( _y1_l.toFixed(this.cache_index_rank) != _y1_r.toFixed(this.cache_index_rank) ) {
                y1 = _y1_r.toFixed(this.cache_index_rank);
                y1 = parseFloat(y1);
            }
            return [x0, x1, y0, y1];
        },

        async update_figures(zoom_stack_item=null) {
            // the function is destructive for zoom_stack_item - don't use refs
            var self = this;
            if ( !_.isNull(zoom_stack_item) ) {
                let cache_item = self.get_figure_cache_item(zoom_stack_item.mz_range);
                cache_item.heatmap_layout.xaxis.range = zoom_stack_item.t_range;
                cache_item.heatmap_layout.yaxis.range = zoom_stack_item.mz_range;
                self.heatmap_layout = cache_item.heatmap_layout;
                cache_item.spec_stack_layout.xaxis.range = zoom_stack_item.mz_range;
                cache_item.spec_stack_layout.yaxis.range = zoom_stack_item.t_range;
                self.spec_stack_layout = cache_item.spec_stack_layout;
                cache_item.timeseries_layout.xaxis.range = zoom_stack_item.t_range;
                self.timeseries_data = cache_item.timeseries_data || [];
                self.timeseries_layout = cache_item.timeseries_layout;
            }
            await Plotly.react("heatmap-figure",
                                self.heatmap_data,
                                self.heatmap_layout
                                );
            await Plotly.react("spec-stack-figure",
                                self.spec_stack_data,
                                self.spec_stack_layout
                                );
            await Plotly.react("timeseries-figure",
                                self.timeseries_data,
                                self.timeseries_layout
                                );
        },

        to_figure_cache_index(mz_range) {
            return [mz_range[0].toFixed(this.cache_index_rank), mz_range[1].toFixed(this.cache_index_rank)];
        },

        get_figure_cache_item(mz_range) {
            if ( _.isUndefined(mz_range) )
                return mz_range;
            return this.figure_cache[this.to_figure_cache_index(mz_range)];
        },

        figure_cache_add_ref(mz_range) {
            let _mz_range = this.to_figure_cache_index(mz_range);
            if ( Object.keys(this.figure_cache).includes(_mz_range.toString()) ) {
                ++this.figure_cache[_mz_range].ref_count;
                return this.figure_cache[_mz_range];
            }
            this.figure_cache[_mz_range] = {'ref_count': 1,
                                           'mz_range': _mz_range,
                                        //    't_filled_range': [Number.MAX_SAFE_INTEGER, 0],
                                           't_filled_range': [0, 0],
                                           'heatmap_layout': this.shallow_copy(this.figure_layouts.heatmap_layout),
                                           'spec_stack_layout': this.shallow_copy(this.figure_layouts.spec_stack_layout),
                                           'timeseries_layout': this.shallow_copy(this.figure_layouts.timeseries_layout),
                                           'timeseries_data': [], };
            return this.figure_cache[_mz_range];
        },

        figure_cache_release_ref(mz_range) {
            let _mz_range = this.to_figure_cache_index(mz_range);
            let cache_item = this.figure_cache[_mz_range];
            cache_item.ref_count--;
            if ( cache_item.ref_count <= 0 )
                delete this.figure_cache[_mz_range];
        }

    },

    watch: {
        acquisition_status: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            if ( new_value === 'running' ) {
                this.reset_figure_cache();
                this.reset_figures();
            }
        },
        figure_ranges: function(new_value, old_value) {
            this.on_figure_ranges(new_value, old_value);
        },
        heatmap_figure_data: function(new_value) {
            this.on_heatmap_figure_data(new_value);
        },
        timeseries_figure_data: function(new_value) {
            this.on_timeseries_figure_data(new_value);
        },
        spec_stack_figure_data: function(new_value) {
            this.on_spec_stack_figure_data(new_value);
        },
        sample_to_load: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            this.reset_figure_cache();
            this.reset_figures();
            if ( _.isEmpty(new_value) || _.isEmpty(new_value.filename)) {
                this.filename = '';
                this.update_figures();
                return false;
            }
            this.filename = new_value.filename;
            this.visualize_range = {
                'filename': this.filename,
                't_range': null,
                'mz_range': null
                };
        },
        data_source_path: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            this.reset_figure_cache();
            this.reset_figures();
        },
        target_to_display: function(new_value, old_value) {
            if ( _.isEqual(new_value, old_value) || _.isEmpty(this.filename) ) {
                return false;
            }
            if (new_value == null) {
                this.visualize_range_on_zoom_out();
                return
            }
            let mz = new_value;
            let target_mz_range = [mz-.5, mz+.5];
            let prev_ranges = this.shallow_copy(this.zoom_stack.slice(-1)[0]);
            let new_ranges = {'mz_range': target_mz_range,
                              't_range': prev_ranges.t_range};
            // Add target trace
            this.heatmap_data = [{
                            'x': new_ranges.t_range,
                            'y': [mz, mz],
                            'mode': 'lines',
                            'line': {'color': '#8c67ef'}
                            }];
            this.spec_stack_data = [{
                            'x': [mz, mz],
                            'y': new_ranges.t_range,
                            'mode': 'lines',
                            'line': {'color': '#8c67ef'}
                            }];
            // Make volatile zoom-in
            this.visualize_range_on_zoom_in(prev_ranges, new_ranges, true);
        },
        tps_parameters: function(new_value, old_value) {
            if ( _.isEmpty(new_value) || _.isEqual(new_value, old_value) ) {
                return false;
            }
        },
    },
};
</script>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"> </style>
<style src = "../assets/css/MeasurementTab.css"> </style>