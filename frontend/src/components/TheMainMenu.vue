<template>
  <base-menu-bar :buttons="buttons" :footerButtons="footerButtons">
  </base-menu-bar>
</template>

<script>
import BaseMenuBar from "./BaseMenuBar";

import { bindState } from "$lib/store";

export default {
  name: "TheMainMenu",
  components: {
    BaseMenuBar,
  },
  computed: {
    ...bindState({
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