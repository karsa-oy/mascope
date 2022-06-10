<template>
  <section>
    <plotly
      :data="data"
      :layout="{ ...baseLayout, ...layout }"
      style="width: 100%; height: 100%"
      v-bind="{ ...baseConfig, ...config }"
      v-on="$listeners"
    ></plotly>
  </section>
</template>

<script>
import { Plotly } from "vue-plotly";

export default {
  name: "ThePageExplorerChartBatch",
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
      required: false,
      default: null,
    },
  },
  data: function() {
    return {
      baseConfig: {
        displayLogo: false,
        displayModeBar: false,
        responsive: true,
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
        plot_bgcolor: "transparent",
        paper_bgcolor: "transparent",
        autosize: false,
        useResizeHandler: true,
      };
    },
  },
};
</script>