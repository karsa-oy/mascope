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
import { mapState } from 'vuex'
import Buefy from "buefy";
import "buefy/dist/buefy.css";
import '@mdi/font/css/materialdesignicons.min.css';
import { BECom } from "../karsalib.js"

Vue.use([Buefy]);

var fs = require('fs');
var Plotly = require('plotly.js-dist');
var _ = require('underscore');


export default {
    name: "ViewPort",
    components: {
    },
    props: {
        id: String,
    },
    computed: {
        ...mapState([
                    'root_namespace',
                    'sample_to_load',
                    'target_to_display',
                    ]),
        figure_double_click: {
            get() {
                return this.$store.state.figure_double_click;
            },
            set(value) {
                this.$store.commit('figure_double_click', value);
            },
        },
        figure_ranges: {
            get() {
                return this.$store.state.figure_ranges;
            },
            set(value) {
                this.$store.commit('figure_ranges', value);
            },
        },
    },
    data: function() {
        return {
            be: null,   //backend communicator
            namespace: null,
            room: null,
            room_sid: null,
            endpoints: [
                // 'acquisition_progress',
                'figure_data',
                // 'figure_ranges',
                ],

            
            filename: '',

            figure: {},
            figure_cache: {'t_maxrange': [0, 0], 'mz_maxrange': [0, 0]},
            figure_config: {},
            figure_data: {},
            figure_traces: [],
            figure_layout: {},
            figure_layout_default: {},
            figure_queue: Promise.resolve(),

            mz_precision: 4,
            
            zoom_stack: [],
            
            visualize_range: {},
            stop_visualize_range: {},
        }
    },

    created: function(){
        this.be = new BECom(this);
    },

    mounted: function() {
        this.init_figure();
    },

    methods: {
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

        log: function(...args) {
            console.log('[' + this.$options.name + ']',  ...args);
        },

        figure_cache_add_ref(zoom_stack_item_room) {
            if ( Object.keys(this.figure_cache).includes(zoom_stack_item_room) ) {
                ++this.figure_cache[zoom_stack_item_room].ref_count;
                return this.figure_cache[zoom_stack_item_room];
            }
            this.figure_cache[zoom_stack_item_room] = {
                    'ref_count': 1,
                    't_filled_range': [Number.MAX_SAFE_INTEGER, 0],
                    'figure_layout': this.shallow_copy(this.figure_layout_default),
                    };
            this.be.subscribe(this.endpoints, zoom_stack_item_room);
            return this.figure_cache[zoom_stack_item_room];
        },

        figure_cache_release_ref(zoom_stack_item_room) {
            let cache_item = this.figure_cache[zoom_stack_item_room];
            cache_item.ref_count--;
            if ( cache_item.ref_count <= 0 ) {
                delete this.figure_cache[zoom_stack_item_room];
                this.be.unsubscribe(this.endpoints, zoom_stack_item_room);
            }
        },

        figure_cache_get(zoom_stack_item_room) {
            if ( _.isUndefined(zoom_stack_item_room) )
                return false;
            return this.figure_cache[zoom_stack_item_room];
        },

        zoom_stack_search(mz_range) {
            let min_dmz = 10**(-this.mz_precision);

            for (let i=0; i < this.zoom_stack.length; ++i) {
                let mz_range_item = this.zoom_stack[i].mz_range;
                if (Math.abs(mz_range_item[0] - mz_range[0]) < min_dmz &&
                    Math.abs(mz_range_item[1] - mz_range[1]) < min_dmz) {
                    // Item found from stack
                    return this.zoom_stack[i];
                    }
            }
            return false;
        },

        init_figure() {
            // This function reads figure layouts from config file, creates
            // the Plotly figures and configures event handlers

            let self = this;
            // Read layouts from config file
            if (fs.existsSync('configs/figure_layouts.json')) {
                let figure_layouts = JSON.parse(fs.readFileSync('configs/figure_layouts.json', 'utf8'));
                self.figure_config = self.shallow_copy(figure_layouts.figure_config);
                self.figure_layout_default = self.shallow_copy(figure_layouts[self.id]);
            }

            // Common config for all figures
            let init_data = [{x: [0, 1],
                              y: [0, 1],
                              type: "scattergl",
                              mode: 'markers',
                              marker: {opacity: 0.0},
                              hoverinfo: 'skip',
                              }];

            // ===== Initialize Plotly figure =====
            let figure_div = document.getElementById(self.id);
            Plotly.newPlot(figure_div,
                           init_data,
                           self.figure_layout_default,
                           {...self.figure_config,
                            "doubleClick": false
                            }
                           );
            // Relayout event
            figure_div.on("plotly_relayout", function(eventData) {
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
                    // console.log("prev_ranges: ", prev_ranges);

                    let x0 = eventData["xaxis.range[0]"];
                    let x1 = eventData["xaxis.range[1]"];
                    let y0 = eventData["yaxis.range[0]"];
                    let y1 = eventData["yaxis.range[1]"];
                    if (_.isUndefined(prev_ranges) &&
                        _.isUndefined(x0) && _.isUndefined(x1) &&
                        _.isUndefined(y0) && _.isUndefined(y1)
                        ) {
                        self.beep();
                        self.log("Do we ever end up here?");
                    }
                    let ranges = {'filename': self.filename};
                    // TODO hacky fix for waterfall
                    if (self.figure_layout_default.xaxis.title.text.indexOf('m/z') != -1) {
                        x0 = (x0 === undefined) ? prev_ranges.mz_range[0] : x0;
                        x1 = (x1 === undefined) ? prev_ranges.mz_range[1] : x1;
                        y0 = (y0 === undefined) ? prev_ranges.t_range[0] : y0;
                        y1 = (y1 === undefined) ? prev_ranges.t_range[1] : y1;
                        self.log("x0: ", x0, "x1: ", x1,  "y0: ", y0, "y1: ", y1);
                        ranges.t_range = [y0, y1];
                        ranges.mz_range = [x0, x1];
                    } else {
                        x0 = (x0 === undefined) ? prev_ranges.t_range[0] : x0;
                        x1 = (x1 === undefined) ? prev_ranges.t_range[1] : x1;
                        y0 = (y0 === undefined) ? prev_ranges.mz_range[0] : y0;
                        y1 = (y1 === undefined) ? prev_ranges.mz_range[1] : y1;
                        ranges.t_range = [x0, x1];
                        ranges.mz_range = [y0, y1];
                    }                    
                    // self.log("ranges: ", ranges);
                    self.figure_ranges = ranges;
                    // self.visualize_range_on_zoom_in(prev_ranges, ranges);
                }
            });

            // Double click event
            figure_div.on('plotly_doubleclick', function(){
                // Signal double click to all ViewPorts
                self.figure_double_click = Math.random();
            });

            // Right click event
            figure_div.addEventListener('contextmenu', function(ev) {
                ev.preventDefault();
                this.log("Right click event....");
                return false;
            }, false);
            // ===== Plotly figure initialized =====
        },

        async _on_figure_ranges(new_value, old_value) {
            if (!new_value.filename) {
                this.reset_view();
                this.filename = "";
                return
            }
            if (!_.isEqual(new_value.filename, old_value.filename)) {
                this.log("new sample -> reset_view");
                this.reset_view();
                old_value = {};
            }
            this.filename = new_value.filename;
            let t0 = new_value.t_range[0];
            let t1 = new_value.t_range[1];
            let mz0 = new_value.mz_range[0];
            let mz1 = new_value.mz_range[1];

            this.figure_cache.t_maxrange[0] = Math.min(t0, this.figure_cache.t_maxrange[0]);
            this.figure_cache.t_maxrange[1] = Math.max(t1, this.figure_cache.t_maxrange[1]);
            this.figure_cache.mz_maxrange[0] = Math.min(mz0, this.figure_cache.mz_maxrange[0]);
            this.figure_cache.mz_maxrange[1] = Math.max(mz1, this.figure_cache.mz_maxrange[1]);

            this.visualize_range_on_zoom_in(old_value, new_value);
        },

        on_figure_ranges(new_value, old_value) {
            if (_.isEqual(new_value, old_value)) {
                this.log("Equal figure ranges");
                return
            }
            var self = this;
            self.figure_queue = self.figure_queue.then(function() {
                return self._on_figure_ranges(new_value, old_value); }
            );
        },

        async _on_figure_data(json_data) {
            var self = this;
            if ( _.isEmpty(json_data) ) {
                // reset the figure
                self.figure_layout = self.shallow_copy(self.figure_layout_default);
                self.figure_traces = [];
                await Plotly.react(self.id, self.figure_traces, self.figure_layout);
                return;
            }
            let data = json_data.value;
            let zoom_stack_item_room = json_data.room;

            if ( !Object.keys(this.figure_cache).includes(zoom_stack_item_room) ) {
                // Received something wrong
                self.beep();
                self.log(self.id, ' _on_figure_data: Something went wrong 1: ',
                         this.figure_cache,
                         zoom_stack_item_room
                         );
                    return;
            }

            let x0 = data.t_range[0]; // float
            let x1 = data.t_range[1]; // float
            let y0 = data.mz_range[0]; // float
            let y1 = data.mz_range[1]; // float
            let sizing = "stretch";

            // TODO: Hacky fix for waterfall
            if (self.figure_layout_default.xaxis.title.text.indexOf('m/z') != -1) {
                x0 = data.mz_range[0]; // float
                x1 = data.mz_range[1]; // float
                y0 = data.t_range[0]; // float
                y1 = 1e6;
                sizing = "contain";
            }
            
            let img = data.img; // base64 png
            let traces = data.traces; // array

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
                "sizing": sizing,
                "layer": "below"
            };

            let cache_item = self.figure_cache_get(zoom_stack_item_room);
            if (!cache_item) {
                self.beep();
                self.log(self.id, ' _on_figure_data: Something went wrong 2')
                return;
            }

            cache_item.figure_layout.images.push(chunk);
            cache_item.t_filled_range[0] = Math.min(x0, cache_item.t_filled_range[0]);
            cache_item.t_filled_range[1] = Math.max(x1, cache_item.t_filled_range[1]);

            // if latest zoom stack item updated, then draw the figure
            if ( _.isEqual(zoom_stack_item_room,
                           self.zoom_stack.slice(-1)[0].room) ) {
                if (traces) {
                    for (let i=0; i<traces.length; i++) {
                        self.figure_traces.push(traces[i]);
                    }
                }
                self.figure_layout = cache_item.figure_layout;
                await Plotly.react(self.id,
                                   self.figure_traces,
                                   self.figure_layout
                                   );
            }
        },

        on_figure_data(json_data) {
            var self = this;
            if (!_.isEqual(json_data.value.viz_type, self.id)) {
                self.log("Received figure_data of wrong type!");
                return;
            }
            self.figure_queue = self.figure_queue.then(function() {
                return self._on_figure_data(json_data); }
            );
        },

        reset_view() {
            this.reset_figure_cache();
            this.reset_figure();
            this.update_figure();
        },

        reset_figure() {
            this.figure_layout = this.shallow_copy(this.figure_layout_default);
            this.figure_traces = [];
        },

        reset_figure_cache() {
            // collect client_rooms to cancel for stop_visualize_range call
            let cancel_requests = [];
            // Collect client_rooms to release
            for (let i=0; i<this.zoom_stack.length; ++i) {
                cancel_requests.push(this.shallow_copy(this.zoom_stack[i].room));
            }
            this.stop_visualize_range = {'client_rooms': cancel_requests};
            // Reset figure cache and zoom stack
            this.figure_cache = {'t_maxrange': [0, 0],
                                 'mz_maxrange': [0, 0], };
            this.zoom_stack = [];
        },

        shallow_copy(o) {
            let _o = JSON.stringify(o);
            if ( _.isUndefined(_o) )
                return _o;
            return JSON.parse(_o);
        },

        async update_figure(zoom_stack_item=null) {
            this.log(zoom_stack_item);
            // the function is destructive for zoom_stack_item - don't use refs
            var self = this;
            if ( !_.isNull(zoom_stack_item) ) {
                let cache_item = self.figure_cache_get(zoom_stack_item.room);
                let mz_range = zoom_stack_item.mz_range;
                let t_range = zoom_stack_item.t_range;
                cache_item.figure_layout.xaxis.range = t_range;
                cache_item.figure_layout.yaxis.range = mz_range;
                // Fix for waterfall
                if (self.figure_layout_default.xaxis.title.text.indexOf('m/z') != -1) {
                    cache_item.figure_layout.xaxis.range = mz_range;
                    cache_item.figure_layout.yaxis.range = t_range;
                }
                self.figure_layout = cache_item.figure_layout;
            }
            await Plotly.react(self.id,
                               self.figure_traces,
                               self.figure_layout
                               );
        },

        visualize_range_on_zoom_in(prev_ranges, new_ranges, volatile=false) {
            // this.log("prev_ranges: ", prev_ranges, "new_ranges: ", new_ranges);
            let self = this;
            if ( _.isUndefined(prev_ranges) || _.isUndefined(new_ranges) ) {
                self.log("visualize_range_on_zoom_in: some of the ranges undefined!");
                return
            }
            // Unpack ranges
            let [mz0, mz1] = new_ranges.mz_range;
            let [t0, t1] = new_ranges.t_range;
            let [pmz0, pmz1] = prev_ranges.mz_range || [1e5, 0]; // Set to dummy values if null
            let [pt0, pt1] = prev_ranges.t_range || [1e5, 0]; // Set to dummy values if null
            // Make sure new ranges are within bounds
            mz0 = Math.max(mz0, self.figure_cache.mz_maxrange[0]);
            mz1 = Math.min(mz1, self.figure_cache.mz_maxrange[1]);
            t0 = Math.max(t0, self.figure_cache.t_maxrange[0]);
            t1 = Math.min(t1, self.figure_cache.t_maxrange[1]);
            // Set min significant zoom ranges
            let min_dmz = 10**(-self.mz_precision);
            // let max_mz_range = self.figure_cache.mz_maxrange[1] - self.figure_cache.mz_maxrange[0]
            // let min_dmz_factor = 0.2;   //don't zoom-in for more than 80% of orig.size
            let min_dt = 1;
            // Check if mz_range has changed
            let mz_range_updated = true;
            if ( (Math.abs(mz1-pmz1) < min_dmz && Math.abs(mz0-pmz0) < min_dmz) ) {
            // if ( Math.abs((Math.abs(mz1-mz0) - Math.abs(pmz1-pmz0))) * max_mz_range /
            //      (Math.abs(mz1-mz0))**2 < min_dmz_factor ) {
                // mz_range has not changed significantly, reset to original
                mz0 = pmz0;
                mz1 = pmz1;
                mz_range_updated = false;
            }
            // Check if t_range has changed
            let t_range_updated = true;
            if ( (Math.abs(t1-pt1) < min_dt &&
                  Math.abs(t0-pt0) < min_dt) ) {
                // t_range has not changed significantly, reset to original
                t0 = pt0;
                t1 = pt1;
                t_range_updated = false;
            }
            if (!mz_range_updated && !t_range_updated) {
                // No need to zoom, reset to original ranges
                self.beep();
                self.update_figure(prev_ranges);
                return
            }
            // Zoom in
            // Check if requested stack item exists in stack 
            let zoom_stack_item = self.zoom_stack_search([mz0, mz1]);
            if ( zoom_stack_item ) {
                // m/z range already in cache
                mz_range_updated = false;
                // Check if requested time range is already cached
                let figure_cache_item = self.figure_cache[zoom_stack_item.room];
                if ( (figure_cache_item.t_filled_range[0] - t0) < min_dt &&
                     (t1 - figure_cache_item.t_filled_range[1]) < min_dt ) {
                    // Requested time range is in cache
                    t_range_updated = false;
                }
                // Make a copy of the zoom stack item to add at the top of the stack
                zoom_stack_item = self.shallow_copy(zoom_stack_item);
            } else {
                // Create new zoom_stack_item
                zoom_stack_item = new self.ZoomStackItem([t0, t1], [mz0, mz1], volatile);
            }
            // Add the zoom stack item at the top of the stack
            self.zoom_stack.push(
                zoom_stack_item
                );
            // Increment figure_cache ref counter
            self.figure_cache_add_ref(zoom_stack_item.room);
            // Update figure
            let cur_ranges = self.shallow_copy(self.zoom_stack.slice(-1)[0]);
            // Set new ranges
            self.update_figure(cur_ranges);
            // Request new visualizations if needed
            if (mz_range_updated) {
                // mz_range changed, request full t_range in the new mz_range
                this.visualize_range = {...cur_ranges,
                                        'filename': this.filename,
                                        'viz_type': this.id,
                                        };
                return
            }
            // if (t_range_updated) {
            //     // TODO: During acquisition, this generates extra visualize_range notifications
            //     // Fill in t gap (range extended by dragging the axis from corner)
            //     let t_filled_range = cache_item.t_filled_range;
            //     let mz_range = cur_ranges.mz_range;
            //     if (Math.abs(t0 - t_filled_range[0]) > min_dt) {
            //         let t_range_to_fill = [t0, t_filled_range[0]];
            //         this.visualize_range = {'mz_range': mz_range,
            //                                 't_range': t_range_to_fill, 
            //                                 'filename': this.filename,
                                                // 'viz_type': this.id,
            //                                 };
            //         return
            //     }
            //     if (Math.abs(t1 - t_filled_range[1]) > min_dt) {
            //         let t_range_to_fill = [t_filled_range[1], t1];
            //         this.visualize_range = {'mz_range': mz_range,
            //                                 't_range': t_range_to_fill, 
            //                                 'filename': this.filename,
                                            // 'viz_type': this.id,
            //                                 };
            //         return
            //     }
            // }
        },

        visualize_range_on_zoom_out() {
            let self = this;
            if ( self.zoom_stack.length <= 1 ) {
                self.log("Zoom stack is empty.");
                self.beep();
                return
            }
            // reset traces
            self.figure_traces = [];
            // remove last zoom and take current zoom into view
            let zoom_stack_item_to_remove = self.zoom_stack.pop();
            let zoom_stack_item_to_restore = self.shallow_copy(self.zoom_stack.slice(-1)[0]);
            // collect client_rooms to cancel for stop_visualize_range call
            let cancel_requests = [];
            cancel_requests.push(self.shallow_copy(zoom_stack_item_to_remove.room));
            // Loop until persistent item found from zoom stack
            while (zoom_stack_item_to_restore.volatile) {
                cancel_requests.push(self.shallow_copy(zoom_stack_item_to_restore.room));
                // Release reference of popped item
                self.figure_cache_release_ref(zoom_stack_item_to_restore.room);
                // Get next item from stack
                self.zoom_stack.pop();
                zoom_stack_item_to_restore = self.shallow_copy(self.zoom_stack.slice(-1)[0]);
            }
            self.log("Zoom stack frames left:", self.zoom_stack.length - 1);
            if ( _.isUndefined(zoom_stack_item_to_remove) || _.isUndefined(zoom_stack_item_to_restore) )
                return;
            self.stop_visualize_range = {'client_rooms': cancel_requests};
            self.update_figure(zoom_stack_item_to_restore);
            // visualize missing frames and acquisition frames
            let prev_item_room = zoom_stack_item_to_remove.room;
            let cur_item_room = zoom_stack_item_to_restore.room;
            let cur_mz = zoom_stack_item_to_restore.mz_range;
            let prev_t_filled = self.figure_cache_get(prev_item_room).t_filled_range;
            let cur_t_filled = self.figure_cache_get(cur_item_room).t_filled_range;
            // retro-visualization
            let min_t_gap = 1;
            if ( prev_t_filled[1] - cur_t_filled[1] > min_t_gap) {
                self.visualize_range = {'t_range': [cur_t_filled[1], prev_t_filled[1]],
                                        'mz_range': cur_mz,
                                        'filename': self.filename,
                                        'viz_type': this.id,
                                        };
            }
            // remove cache item, if not used anymore
            self.figure_cache_release_ref(zoom_stack_item_to_remove.room);
        },

        ZoomStackItem: function(t_range, mz_range, volatile=false, room=null) {
            this.t_range = t_range;
            this.mz_range = mz_range;
            this.volatile = volatile;
            // Room for zoom stack item
            this.room = room || Math.random().toString(36).substring(2);
        },

    },

    watch: {
        figure_data: function(new_value) {
            this.on_figure_data(new_value);
        },
        figure_double_click: function() {
            this.visualize_range_on_zoom_out();
        },
        figure_ranges: function(new_value, old_value) {
            this.on_figure_ranges(new_value, old_value);
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
            this.figure_traces = [{
                            'x': new_ranges.t_range,
                            'y': [mz, mz],
                            'mode': 'lines',
                            'line': {'color': '#8c67ef'}
                            }];
            // Make volatile zoom-in
            this.visualize_range_on_zoom_in(prev_ranges, new_ranges, true);
        },
        stop_visualize_range: function(new_value, old_value) {
            let client_room = this.room;
            return this.be.export_one_way_binding_prop('stop_visualize_range',
                                                        {...new_value, 'uid': Math.random()},
                                                        old_value,
                                                        client_room
                                                        );
        },
        visualize_range: function(new_value, old_value) {
            let client_room = new_value.room || this.room;
            return this.be.export_one_way_binding_prop('visualize_range',
                                                        {...new_value, 'uid': Math.random()},
                                                        old_value,
                                                        client_room
                                                        );
        },
        'root_namespace.connected': function(new_value) {
            if ( new_value === true )
            {
                this.namespace = this.root_namespace;
                // handlers for for external notifications:
                // this.namespace.on("figure_ranges", (value) => this.be.import_one_way_binding_prop("figure_ranges", {...value.value, 'uid': Math.random()}));
                this.namespace.on("figure_data", (value) => this.be.import_one_way_binding_prop("figure_data", value));

                this.room_sid = this.root_namespace.id;
                this.room = Math.random().toString(36).substring(2);
                // this.be.subscribe(this.endpoints, this.room);
            }
        },
    },
};
</script>

<style src = "vue-multiselect/dist/vue-multiselect.min.css"> </style>
<style src = "../assets/css/MeasurementTab.css"> </style>