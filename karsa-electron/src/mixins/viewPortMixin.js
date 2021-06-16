import { mapState } from 'vuex'
import { shallow_copy } from "../karsalib.js"

var fs = require('fs');
var Plotly = require('plotly.js-dist');
var _ = require('underscore');


export const viewPortMixin = {
    computed: {
        ...mapState([
                    'figure_data',
                    'sample_annotations',
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
        stop_visualize_range: {
            get() {
                return this.$store.state.stop_visualize_range;
            },
            set(value) {
                this.$store.commit('stop_visualize_range', value);
            },
        },
        visualize_range: {
            get() {
                return this.$store.state.visualize_range;
            },
            set(value) {
                this.$store.commit('visualize_range', value);
            },
        },
    },
    data: function() {
        return {
            name: "ViewPort_" + this.id,
            
            filename: '',

            figure: {},
            figure_annotations: [],
            figure_axes: {},
            figure_cache: {
                't_maxrange': [0, 0],
                'mz_maxrange': [0, 0]
                },
            figure_config: {},
            figure_traces: [],
            figure_img_config: {},
            figure_layout: {},
            figure_layout_default: {},
            figure_queue: Promise.resolve(),

            mz_precision: 4,
            
            zoom_stack: [],
        }
    },
    created: function(){
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
            console.log('[' + this.name + ']',  ...args);
        },

        figure_cache_add_ref(zoom_stack_item_id) {
            if ( Object.keys(this.figure_cache).includes(zoom_stack_item_id) ) {
                ++this.figure_cache[zoom_stack_item_id].ref_count;
                return this.figure_cache[zoom_stack_item_id];
            }
            this.figure_cache[zoom_stack_item_id] = {
                    'ref_count': 1,
                    't_filled_range': [Number.MAX_SAFE_INTEGER, 0],
                    'figure_layout': shallow_copy(this.figure_layout_default),
                    'figure_traces': [],
                    };
            return this.figure_cache[zoom_stack_item_id];
        },

        figure_cache_release_ref(zoom_stack_item_id) {
            let cache_item = this.figure_cache[zoom_stack_item_id];
            cache_item.ref_count--;
            if ( cache_item.ref_count <= 0 ) {
                delete this.figure_cache[zoom_stack_item_id];
            }
        },

        figure_cache_get(zoom_stack_item_id) {
            if ( _.isUndefined(zoom_stack_item_id) )
                return false;
            return this.figure_cache[zoom_stack_item_id];
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

            var self = this;
            // Read layouts from config file
            if (fs.existsSync('configs/figure_config.json')) {
                let figure_configs = JSON.parse(fs.readFileSync('configs/figure_config.json', 'utf8'));
                self.figure_config = shallow_copy(figure_configs.common_config);
                let figure_layout_config = shallow_copy(figure_configs[self.id].layout);
                self.figure_layout_default = figure_layout_config;
                self.figure_img_config = figure_configs[self.id].img;
                self.figure_axes = figure_configs[self.id].axes;
            }
            // ===== Initialize Plotly figure =====
            let figure_div = document.getElementById(self.id);
            Plotly.newPlot(figure_div,
                           [],
                           self.figure_layout_default,
                           {...self.figure_config,
                            "doubleClick": false
                            }
                           );
            
            
            // Relayout event
            figure_div.on("plotly_relayout", function(eventData) {
                if (!self.figure_ranges.filename) {
                    // No sample loaded
                    return
                }
                if ( _.isEmpty(eventData) ) {
                    // Likely a double-click event
                    return;
                }
                if ( _.isEqual(eventData, {'autosize': true}) ) {
                    // Figure resize event
                    return;
                }
                if ( Object.keys(eventData).length == 1 && eventData.annotations ) {
                    // Annotations edited
                    return;
                }
                if ( Object.keys(eventData).length ) {
                    // zoom_in
                    let prev_ranges = shallow_copy(self.zoom_stack.slice(-1)[0]);
                    // console.log("prev_ranges: ", prev_ranges);
                    let mz0 = eventData[self.figure_axes.mz + "axis.range[0]"];
                    let mz1 = eventData[self.figure_axes.mz + "axis.range[1]"];
                    let t0 = eventData[self.figure_axes.time + "axis.range[0]"];
                    let t1 = eventData[self.figure_axes.time + "axis.range[1]"];
                    if (_.isUndefined(prev_ranges) &&
                        _.isUndefined(mz0) && _.isUndefined(mz1) &&
                        _.isUndefined(t0) && _.isUndefined(t1)
                        ) {
                        self.beep();
                        self.log("Do we ever end up here?");
                    }
                    let ranges = {'filename': self.filename,
                                  'id': Math.random().toString(36).substring(2),
                                  };
                    
                    mz0 = (mz0 === undefined) ? prev_ranges.mz_range[0] : mz0;
                    mz1 = (mz1 === undefined) ? prev_ranges.mz_range[1] : mz1;
                    t0 = (t0 === undefined) ? prev_ranges.t_range[0] : t0;
                    t1 = (t1 === undefined) ? prev_ranges.t_range[1] : t1;
                    ranges.t_range = [t0, t1];
                    ranges.mz_range = [mz0, mz1];
                    
                    // self.log("ranges: ", ranges);
                    self.figure_ranges = ranges;
                }
            });
            // Click event
            figure_div.on('plotly_click', (eventData) => this.on_plotly_click(eventData));
            // Double click event
            figure_div.on('plotly_doubleclick', function(){
                // Signal double click to all ViewPorts
                self.figure_double_click = Math.random();
            });
            // Right click event
            figure_div.addEventListener('contextmenu', function(ev) {
                ev.preventDefault();
                self.log("Right click event....");
                return false;
            }, false);
            // ===== Plotly figure initialized =====
        },

        on_plotly_click(eventData) {
            // Plotly click event handler, override in ViewPort component
            switch (eventData.button){
                case 0:
                    this.log('left click')
                    break
                case 1:
                    this.log('wheel click')
                    break
                case 2:
                    this.log('right click')
                    break
            }
            return eventData
        },

        async _on_figure_ranges(new_value, old_value) {
            if (!new_value.filename) {
                // this.log("_on_figure_ranges: !new_value.filename");
                this.reset_view();
                this.filename = "";
                return
            }
            let new_sample = false;
            if (!_.isEqual(new_value.filename, old_value.filename)) {
                // New sample to load, reset
                // this.log("_on_figure_ranges: new_sample");
                this.reset_view();
                new_sample = true;
            }
            this.filename = new_value.filename;
            if (!new_value.mz_range) {
                this.log("Error: mz_range not defined!")
                return
            }
            let t0 = new_value.t_range[0];
            let t1 = new_value.t_range[1];
            let mz0 = new_value.mz_range[0];
            let mz1 = new_value.mz_range[1];

            this.figure_cache.t_maxrange[0] = Math.min(t0, this.figure_cache.t_maxrange[0]);
            this.figure_cache.t_maxrange[1] = Math.max(t1, this.figure_cache.t_maxrange[1]);
            this.figure_cache.mz_maxrange[0] = Math.min(mz0, this.figure_cache.mz_maxrange[0]);
            this.figure_cache.mz_maxrange[1] = Math.max(mz1, this.figure_cache.mz_maxrange[1]);

            if (new_sample) {
                this.visualize_range_on_sample_selected(new_value);
            } else {
                // Zoom in loaded sample
                this.visualize_range_on_zoom_in(old_value, new_value);
            }
            // Add target trace if target selected
            if (this.target_to_display) {
                let mz = this.target_to_display;
                let mz_axis = this.figure_axes.mz;
                let time_axis = this.figure_axes.time;
                if (mz_axis) {
                    // Add target trace
                    let target_traces = [{
                        [time_axis]: new_value.t_range,
                        [mz_axis]: [mz, mz],
                        'mode': 'lines',
                        'line': {'color': '#8c67ef'}
                        }];
                    let zoom_stack_item = this.zoom_stack.slice(-1)[0]
                    let figure_cache_item = this.figure_cache_get(zoom_stack_item.id);
                    figure_cache_item.figure_traces.push(...target_traces);
                }
            }
        },

        async _on_figure_data(json_data) {
            var self = this;
            if ( _.isEmpty(json_data) ) {
                // reset the figure
                self.figure_layout = shallow_copy(self.figure_layout_default);
                self.figure_traces = [];
                await Plotly.react(self.id, self.figure_traces, self.figure_layout);
                return;
            }
            let data = json_data.value;
            let zoom_stack_item_id = data.request_id;

            let cache_item = self.figure_cache_get(zoom_stack_item_id);
            if (!cache_item) {
                self.beep();
                self.log('Received figure_data for non-existing zoom stack item!', self.figure_cache);
                return;
            }

            let t0 = data.t_range[0]; // float
            let t1 = data.t_range[1]; // float
            let mz0 = data.mz_range[0]; // float
            let mz1 = data.mz_range[1]; // float

            let time_axis = self.figure_axes.time;
            let mz_axis = self.figure_axes.mz;
            
            let img = data.img; // base64 png
            if (img) {
                // Add image to figure layout
                let chunk = {
                    "source": img,
                    "xref": "x",
                    "yref": "y",
                    [mz_axis]: mz0,
                    [time_axis]: t0,
                    ["size" + mz_axis]: mz1 - mz0,
                    ["size" + time_axis]: t1 - t0,
                    "xanchor": "left",
                    "yanchor": "bottom",
                    "sizing": "stretch",
                    "layer": "below"
                };
                // Override from figure config
                chunk = Object.assign(chunk, self.figure_img_config);
                // Push to layout
                cache_item.figure_layout.images.push(chunk);
            }
            // Keep track of filled ranges
            cache_item.t_filled_range[0] = Math.min(t0, cache_item.t_filled_range[0]);
            cache_item.t_filled_range[1] = Math.max(t1, cache_item.t_filled_range[1]);

            // Add time axis ticks
            if (_.isEqual(self.figure_layout[time_axis+"axis"].tickmode, "array")) {
                cache_item.figure_layout[time_axis+"axis"].tickvals.push(t0);
                cache_item.figure_layout[time_axis+"axis"].ticktext.push(t0.toFixed(2).toString());
            }

            let traces = data.traces; // array
            if (traces) {
                // If traces in json_data, add to figure
                for (let i=0; i<traces.length; i++) {
                    cache_item.figure_traces.push(traces[i]);
                }
            }

            // if latest zoom stack item updated, draw the figure
            if ( _.isEqual(zoom_stack_item_id,
                           self.zoom_stack.slice(-1)[0].id) ) {
                self.figure_layout = cache_item.figure_layout;
                self.figure_traces = cache_item.figure_traces;
                await Plotly.update(self.id,
                                   self.figure_traces,
                                   {...self.figure_layout,
                                    annotations: shallow_copy(this.figure_annotations)
                                    }
                                   );
            }
        },

        reset_view() {
            this.reset_figure_cache();
            this.reset_figure();
            this.update_figure();
        },

        reset_figure() {
            this.figure_layout = shallow_copy(this.figure_layout_default);
            this.figure_traces = [];
        },

        reset_figure_cache() {
            // collect client_rooms to cancel for stop_visualize_range call
            let cancel_requests = [];
            // Collect client_rooms to release
            for (let i=0; i<this.zoom_stack.length; ++i) {
                cancel_requests.push(shallow_copy(this.zoom_stack[i].id));
            }
            this.stop_visualize_range = {
                                'request_ids': cancel_requests,
                                'filename': this.filename
                                };
            // Reset figure cache and zoom stack
            this.figure_cache = {'t_maxrange': [0, 0],
                                 'mz_maxrange': [0, 0], };
            this.zoom_stack = [];
        },

        async update_figure(zoom_stack_item=null) {
            // this.log(zoom_stack_item);
            // the function is destructive for zoom_stack_item - don't use refs
            var self = this;
            if ( !_.isNull(zoom_stack_item) ) {
                let cache_item = self.figure_cache_get(zoom_stack_item.id);
                let mz_range = zoom_stack_item.mz_range;
                let t_range = zoom_stack_item.t_range;
                let mz_axis = this.figure_axes.mz;
                let time_axis = this.figure_axes.time;
                if (mz_axis) {
                    cache_item.figure_layout[mz_axis+"axis"].range = mz_range;
                }
                if (time_axis) {
                    cache_item.figure_layout[time_axis+"axis"].range = t_range;
                }
                self.figure_layout = cache_item.figure_layout;
                self.figure_traces = cache_item.figure_traces;
            }
            // self.log(this.figure_annotations);
            await Plotly.react(self.id,
                                self.figure_traces,
                                self.figure_layout
                                );
        },

        visualize_range_on_sample_selected(new_ranges) {
            // this.log(new_ranges);
            // Unpack ranges
            let [mz0, mz1] = new_ranges.mz_range;
            let [t0, t1] = new_ranges.t_range;
            let request_id = new_ranges.id;
            // Create new zoom_stack_item
            let zoom_stack_item = new this.ZoomStackItem([t0, t1], [mz0, mz1], request_id);
            // Add the zoom stack item at the top of the stack
            this.zoom_stack.push(
                zoom_stack_item
                );
            // Increment figure_cache ref counter
            this.figure_cache_add_ref(zoom_stack_item.id);
            // Update figure
            let cur_ranges = shallow_copy(this.zoom_stack.slice(-1)[0]);
            // Set new ranges
            this.update_figure(cur_ranges);
            // Request full range visualization from DataViz (ranges null)
            this.visualize_range = {'filename': this.filename,
                                    'request_id': cur_ranges.id,
                                    };
        },

        visualize_range_on_zoom_in(prev_ranges, new_ranges) {
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
                let figure_cache_item = self.figure_cache[zoom_stack_item.id];
                if ( (figure_cache_item.t_filled_range[0] - t0) < min_dt &&
                     (t1 - figure_cache_item.t_filled_range[1]) < min_dt ) {
                    // Requested time range is in cache
                    t_range_updated = false;
                }
                // Make a copy of the zoom stack item to add at the top of the stack
                zoom_stack_item = shallow_copy(zoom_stack_item);
            } else {
                // Create new zoom_stack_item
                zoom_stack_item = new self.ZoomStackItem([t0, t1],
                                                         [mz0, mz1],
                                                         new_ranges.id,
                                                         new_ranges.volatile
                                                         );
            }
            // Add the zoom stack item at the top of the stack
            self.zoom_stack.push(
                zoom_stack_item
                );
            // Increment figure_cache ref counter
            self.figure_cache_add_ref(zoom_stack_item.id);
            // Update figure
            let cur_ranges = shallow_copy(self.zoom_stack.slice(-1)[0]);
            // Set new ranges
            self.update_figure(cur_ranges);
            // Request new visualizations if needed
            if (mz_range_updated) {
                // mz_range changed, request full t_range in the new mz_range
                this.visualize_range = {'filename': this.filename,
                                        'mz_range': cur_ranges.mz_range,
                                        't_range': cur_ranges.t_range,
                                        'request_id': cur_ranges.id,
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
            //                                 };
            //         return
            //     }
            //     if (Math.abs(t1 - t_filled_range[1]) > min_dt) {
            //         let t_range_to_fill = [t_filled_range[1], t1];
            //         this.visualize_range = {'mz_range': mz_range,
            //                                 't_range': t_range_to_fill, 
            //                                 'filename': this.filename,
            //                                 };
            //         return
            //     }
            // }
        },

        visualize_range_on_zoom_out() {
            let self = this;
            if ( self.zoom_stack.length <= 1 ) {
                // self.log("Zoom stack is empty.");
                self.beep();
                return
            }
            // reset traces
            self.figure_traces = [];
            // remove last zoom and take current zoom into view
            let zoom_stack_item_to_remove = self.zoom_stack.pop();
            let zoom_stack_item_to_restore = shallow_copy(self.zoom_stack.slice(-1)[0]);
            // collect client_rooms to cancel for stop_visualize_range call
            let cancel_requests = [];
            cancel_requests.push(shallow_copy(zoom_stack_item_to_remove.id));
            // Loop until persistent item found from zoom stack
            while (zoom_stack_item_to_restore.volatile) {
                cancel_requests.push(shallow_copy(zoom_stack_item_to_restore.id));
                // Release reference of popped item
                self.figure_cache_release_ref(zoom_stack_item_to_restore.id);
                // Get next item from stack
                self.zoom_stack.pop();
                zoom_stack_item_to_restore = shallow_copy(self.zoom_stack.slice(-1)[0]);
            }
            // self.log("Zoom stack frames left:", self.zoom_stack.length - 1);
            if ( _.isUndefined(zoom_stack_item_to_remove) || _.isUndefined(zoom_stack_item_to_restore) )
                return;
            self.stop_visualize_range = {
                                'request_ids': cancel_requests,
                                'filename': this.filename
                                };
            self.update_figure(zoom_stack_item_to_restore);
            // visualize missing frames and acquisition frames
// TODO:
            // let prev_item_room = zoom_stack_item_to_remove.id;
            // let cur_item_room = zoom_stack_item_to_restore.id;
            // let cur_mz = zoom_stack_item_to_restore.mz_range;
            // let prev_t_filled = self.figure_cache_get(prev_item_room).t_filled_range;
            // let cur_t_filled = self.figure_cache_get(cur_item_room).t_filled_range;
            // retro-visualization
            // let min_t_gap = 1;
            // if ( prev_t_filled[1] - cur_t_filled[1] > min_t_gap) {
            //     self.visualize_range = {'t_range': [cur_t_filled[1], prev_t_filled[1]],
            //                             'mz_range': cur_mz,
            //                             'filename': self.filename,
            //                             };
            // }
// TODO:
            // remove cache item, if not used anymore
            self.figure_cache_release_ref(zoom_stack_item_to_remove.id);
        },

        ZoomStackItem: function(t_range, mz_range, id=null, volatile=false) {
            this.t_range = t_range;
            this.mz_range = mz_range;
            this.volatile = volatile;
            this.id = id || Math.random().toString(36).substring(2);
        },

    },
    watch: {
        figure_data: function(new_value) {
            if ( !_.isEqual(new_value.value.viz_type, this.id) &&
                 !_.isEqual(new_value.value.data_type, this.id))
                return;
            var self = this;
            self.figure_queue = self.figure_queue.then(function() {
                return self._on_figure_data(new_value); }
            );
        },
        figure_double_click: function() {
            this.visualize_range_on_zoom_out();
        },
        figure_ranges: function(new_value, old_value) {
            if (_.isEqual(new_value, old_value)) {
                return
            }
            var self = this;
            self.figure_queue = self.figure_queue.then(function() {
                return self._on_figure_ranges(new_value, old_value); }
            );
        },
        // target_to_display: function(new_value, old_value) {
        //     if ( _.isEqual(new_value, old_value) || _.isEmpty(this.filename) ) {
        //         return false;
        //     }
        //     if (new_value == null) {
        //         this.visualize_range_on_zoom_out();
        //         return
        //     }
        //     let mz = new_value;
        //     let target_mz_range = [mz-.5, mz+.5];
        //     let prev_ranges = shallow_copy(this.zoom_stack.slice(-1)[0]);
        //     let new_ranges = {'mz_range': target_mz_range,
        //                       't_range': prev_ranges.t_range};
        //     // Make volatile zoom-in
        //     this.visualize_range_on_zoom_in(prev_ranges, new_ranges, true);
        //     let mz_axis = this.figure_axes.mz;
        //     let time_axis = this.figure_axes.time;
        //     if (mz_axis) {
        //         // Add target trace
        //         let target_traces = [{
        //             [time_axis]: new_ranges.t_range,
        //             [mz_axis]: [mz, mz],
        //             'mode': 'lines',
        //             'line': {'color': '#8c67ef'}
        //             }];
        //         let zoom_stack_item = this.zoom_stack.slice(-1)[0]
        //         let figure_cache_item = this.figure_cache_get(zoom_stack_item.id);
        //         figure_cache_item.figure_traces.push(...target_traces);
        //     }
        // },
    },
}