<template>
  <section ref="plotlyChart">
    <plotly
      :id="id"
      :data="data"
      :layout="{ ...baseLayout, ...layout }"
      style="width: 100%; height: 100%"
      v-bind="{ ...baseConfig, ...config }"
      v-on="$listeners"
    ></plotly>
  </section>
</template>

<script>
import Plotly from "./external/Plotly.vue";

export default {
  name: "BaseChartPlotly",
  components: {
    Plotly,
  },
  props: {
    title: {
      type: String,
    },
    config: {
      type: Object,
      required: false,
    },
    data: {
      type: Array,
    },
    layout: {
      type: Object,
    },
    id: {
      type: String,
      required: true,
    },
  },
  data: function () {
    return {
      baseConfig: {
        displaylogo: false,
        displayModeBar: true,
        responsive: true,
        modeBarButtonsToRemove: [
          "autoScale",
          "resetScale2d",
          "pan2d",
          "zoomIn2d",
          "zoomOut2d",
        ],
        toImageButtonOptions: {
          format: "png", // one of png, svg, jpeg, webp
          filename: this.title.toLowerCase().replaceAll(/[\s-]/g, "_"),
          height: 500,
          width: 700,
          scale: 1, // Multiply title/legend/axis/canvas sizes by this factor
        },
      },
    };
  },
  computed: {
    baseLayout: function () {
      return {
        title: {
          text: this.title,
        },
        font: {
          color: "#fff",
        },
        hoverinfo: "name+y",
        plot_bgcolor: "#313239f0",
        paper_bgcolor: "transparent",
        autosize: true,
        useResizeHandler: true,
        modebar: {
          bgcolor: "transparent",
        },
      };
    },
  },
  mounted() {
    // Disable context menu on right click
    this.$refs.plotlyChart.addEventListener("contextmenu", (event) => {
      event.preventDefault();
    });
  },
};
</script>
