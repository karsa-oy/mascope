<template>
  <div class="chart">
    <!-- Main content  area-->
    <section>
      <div :id="id"></div>
    </section>
  </div>
</template>

<script type = "text/javascript" >
"use strict";
import Vue from "vue";
import { mapState } from "vuex";
import Buefy from "buefy";
import { shallow_copy } from "../karsalib.js"

import "buefy/dist/buefy.css";
import "@mdi/font/css/materialdesignicons.min.css";

Vue.use([Buefy]);

var fs = require('fs');
var Plotly = require('plotly.js-dist');

export default {
  name: "ExperimentView",
  components: {},
  props: [],
  computed: {
    ...mapState([
        "samples",
        "target_compound_intensities",
        "target_compound_selected",
        ]),
    sample_table_selected_row: {
      get() {
        return this.$store.state.sample_table_selected_row;
      },
      set(value) {
        this.$store.commit("sample_table_selected_row", value);
      },
    },
  },
  data: function () {
    return {
        figure_axes: {},
        figure_config: {},
        figure_img_config: {},
        figure_layout: {},
        figure_layout_default: {},
        figure_traces: [],
        figure_traces_default: [],
        id: "target_intensity_chart",
    };
  },
mounted: function() {
    this.init_figure();
},
  methods: {
    init_figure() {
        // This function reads figure layouts from config file, creates
        // the Plotly figures and configures event handlers

        var self = this;
        // Read layouts from config file
        if (fs.existsSync('configs/figure_config.json')) {
            const figure_configs = JSON.parse(fs.readFileSync('configs/figure_config.json', 'utf8'));
            self.figure_config = shallow_copy(figure_configs.common_config);
            self.figure_layout_default = shallow_copy(figure_configs[self.id].layout);
            self.figure_layout = shallow_copy(self.figure_layout_default);
            self.figure_img_config = figure_configs[self.id].img;
            self.figure_axes = figure_configs[self.id].axes;
        }
        // ===== Initialize Plotly figure =====
        let figure_div = document.getElementById(self.id);
        Plotly.newPlot(figure_div,
                        [],
                        self.figure_layout_default,
                        self.figure_config,
                        );
        
        
        // Relayout event
        figure_div.on("plotly_relayout", function(eventData) {
            console.log(eventData);
        });
        // Click event
        figure_div.on('plotly_click', (eventData) => this.on_plotly_click(eventData));
        // Right click event
        figure_div.addEventListener('contextmenu', function(ev) {
            ev.preventDefault();
            self.log("Right click event....");
            return false;
        }, false);
        // ===== Plotly figure initialized =====
    },
    log: function(...args) {
        console.log('[' + this.name + ']',  ...args);
    },
    on_plotly_click(eventData) {
        // Plotly click event handler, override in ViewPort component
        // this.log(eventData);
        switch (eventData.event.button){
            case 0: {
                // this.log('left click', eventData);
                // Get filename from eventData
                let p0 = eventData.points[0];
                let point_ind = p0.pointIndex;
                let clicked_sample_id = p0.data.sample_id[point_ind]; // get custom item 'sample_id'
                this.sample_table_selected_row = {filename: clicked_sample_id};
                break
            }
            case 1:
                this.log('wheel click')
                break
            case 2:
                this.log('right click')
                break
        }
        return eventData
    },
    updateFigure: function() {
        let selected_target_id = this.target_compound_selected.id;
        let x_tickvals = [];
        let x_ticktext = [];
        let x = [];
        let y = [];
        let i = 1;
        for (let filename in this.target_compound_intensities) {
            let sample = this.samples[filename];
            let sample_title = sample.attributes[0].value;
            let sample_target_intensity = this.target_compound_intensities[filename][selected_target_id];
            x.push(i);
            y.push(sample_target_intensity);
            x_tickvals.push(i);
            x_ticktext.push(sample_title);
            ++i;
        }
        this.figure_traces = [
            {'x': x,
             'y': y,
             'mode': 'markers',
             'type': 'scatter',
             'marker': { size: 20 },
             'name': this.target_compound_selected[0],
             'sample_id': Object.keys(this.target_compound_intensities) // set custom item 'sample_id'
             }
        ];
        this.figure_layout.xaxis.tickvals = x_tickvals;
        this.figure_layout.xaxis.ticktext = x_ticktext;
        Plotly.react(this.id,
                     this.figure_traces,
                     this.figure_layout
                     );
    },
  },
  watch: {
    target_compound_intensities: function() {
        this.updateFigure();
    },
    target_compound_selected: function() {
        this.updateFigure();
    }
  },
};
</script>