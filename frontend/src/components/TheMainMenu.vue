<template>
  <base-menu-bar :buttons="buttons" :footerButtons="footerButtons">
  </base-menu-bar>
</template>

<script>
import BaseMenuBar from "./BaseMenuBar.vue";

import { get, call } from "vuex-pathify";

export default {
  name: "TheMainMenu",
  components: {
    BaseMenuBar,
  },
  computed: {
    ...get({
      workspaceActive: "workspace/active",
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
          visible: this.workspaceActive,
        },
        {
          icon: "format-horizontal-align-center",
          label: "m/z calibration",
          path: "/mz-calibration",
          visible: this.workspaceActive,
        },
        {
          icon: "flask",
          label: "Batch overview",
          path: "/batch-overview",
          visible: this.workspaceActive,
        },
        {
          icon: "sine-wave",
          label: "Sample signal",
          path: "/sample-signal",
          visible: this.workspaceActive,
        },
        {
          icon: "table-multiple",
          label: "Data management",
          path: "/data-management",
          visible: this.workspaceActive,
        },
      ].filter((b) => b.visible);
    },
    footerButtons() {
      return [
        {
          icon: "tune",
          label: "Settings",
          path: "/settings",
          visible: false,
        },
        {
          icon: "logout-variant",
          label: "Change workspace",
          path: "/",
          onClick: this.workspaceUnload,
          visible: true,
        },
      ].filter((b) => b.visible);
    },
  },
  methods: {
    ...call({
      workspaceUnload: "workspace/unload",
    }),
  },
};
</script>