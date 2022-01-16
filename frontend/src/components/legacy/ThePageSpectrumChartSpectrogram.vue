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
  computed: {},
  data: function () {
    return {
      figureTracesDefault: [
        {
          name: "Found peaks",
          legendgroup: "Found peaks",
          x: [0],
          y: [0],
          mode: "lines",
          line: { color: "#ffffff", width: 1 },
          visible: "legendonly",
          showlegend: true,
        },
      ],
    };
  },

  created: function () {},

  mounted: function () {},

  methods: {},

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