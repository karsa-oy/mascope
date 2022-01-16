<template>
  <div class="chart">
    <section>
      <div :id="id"></div>
    </section>
  </div>
</template>


<script>
import { chartMixin } from "$mixins/chartMixin";

var Plotly = require("plotly.js-dist");

export default {
  components: {},
  mixins: [chartMixin],
  props: {
    id: String,
  },
  computed: {
    sampleAnnotationTimestamp: {
      get() {
        return this.$store.state.sampleAnnotationTimestamp;
      },
      set(value) {
        this.$store.commit("sampleAnnotationTimestamp", value);
      },
    },
  },
  data: function () {
    return {};
  },

  created: function () {},

  mounted: function () {},

  methods: {
    onPlotlyClick(eventData) {
      // Plotly click event handler
      switch (eventData.event.button) {
        case 0:
          // Left click
          break;
        case 1:
          // Wheel click
          break;
        case 2:
          // Right click
          var timestamp = eventData.points[0].x;
          this.sampleAnnotationTimestamp = timestamp;
          return;
      }
    },
  },

  watch: {
    sampleAnnotations: function (newValue) {
      let annotations = [];
      for (let i in newValue) {
        let annotation = {
          text: newValue[i].text,
          xref: "x",
          x: newValue[i].timestamp,
          yref: "paper",
          y: 0,
          ayref: "paper",
          ay: 0.9,
          ax: 0,
        };
        annotations.push(annotation);
      }
      // Update figure
      Plotly.relayout(this.id, { annotations: annotations });
    },
  },
};
</script>