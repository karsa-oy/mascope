<template>
  <base-menu-bar :buttons="buttons" :footerButtons="footerButtons">
  </base-menu-bar>
</template>

<script>
import BaseMenuBar from "./BaseMenuBar";

import { mapGetters } from "vuex";

export default {
  name: "TheMainMenu",
  components: {
    BaseMenuBar,
  },
  computed: {
    ...mapGetters({
      workspaceSelected: "workspace/selectedRow",
    }),
    buttons() {
      return [
        {
          icon: "home",
          label: "Workspace home",
          path: "/",
          visible: true,
        },
        {
          icon: "file-plus",
          label: "Sample management",
          path: "/sample-management",
          visible: this.workspaceSelected,
        },
        {
          icon: "format-horizontal-align-center",
          label: "m/z calibration",
          path: "/mz-calibration",
          visible: this.workspaceSelected,
        },
        {
          icon: "flask",
          label: "Batch overview",
          path: "/batch-overview",
          visible: this.workspaceSelected,
        },
        {
          icon: "sine-wave",
          label: "Sample signal",
          path: "/sample-signal",
          visible: this.workspaceSelected,
        },
        {
          icon: "table-multiple",
          label: "Data management",
          path: "/data-management",
          visible: this.workspaceSelected,
        },
      ].filter((b) => b.visible);
    },
    footerButtons() {
      return [
        {
          icon: "tune",
          label: "Settings",
          path: "/settings",
          visible: true,
        },
        {
          icon: "logout-variant",
          label: "Change workspace",
          path: "/",
          newQuery: {},
          visible: true,
        },
      ].filter((b) => b.visible);
    },
  },
};
</script>