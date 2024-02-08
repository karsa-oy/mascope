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
      acquisitionActive: "instrument/acquisitionActiveFilename",
      batchActive: "batch/active",
      instrumentActive: "instrument/active",
      scenthoundModeActive: "instrument/scenthoundModeActive",
      workspaceActive: "workspace/active",
    }),
    allButtonsDisabled() {
      return this.scenthoundModeActive && this.acquisitionActive ? true : false;
    },
    buttons() {
      return [
        {
          disabled: this.allButtonsDisabled,
          icon: "home",
          label: "Workspace home",
          path: "/",
          visible: true,
        },
        {
          disabled:
            this.allButtonsDisabled ||
            !(this.batchActive && this.instrumentActive),
          icon: "dog-side",
          label: "Scenthound",
          path: "/scenthound",
          visible: true,
        },
        {
          disabled: this.allButtonsDisabled,
          icon: "chart-scatter-plot",
          label: "Batch overview",
          path: "/batch-overview",
          visible: this.batchActive,
        },
      ].filter((b) => b.visible);
    },
    footerButtons() {
      return [
        {
          disabled: this.allButtonsDisabled,
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
