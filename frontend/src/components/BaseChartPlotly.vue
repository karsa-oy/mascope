<template>
  <section>
    <plotly
      :data="data"
      :layout="{ ...baseLayout, ...layout }"
      :display-logo="false"
      :display-mode-bar="false"
      style="width: 100%; height: 100%"
      :responsive="true"
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