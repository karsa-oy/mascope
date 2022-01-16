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
      for (let i in newValue) {
        let annotation = {
          text: newValue[i].text,
          yref: "y",
          y: newValue[i].timestamp,
          xref: "paper",
          x: 1,
          axref: "paper",
          ax: 0,
          ay: 0,
        };
        this.figureAnnotations.push(annotation);
      }
      // Update figure
      Plotly.relayout(this.id, { annotations: this.figureAnnotations });
    },
  },
};
</script>