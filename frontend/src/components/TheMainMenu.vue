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
          icon: "file-plus",
          label: "Sample management",
          path: "/sample-management",
          visible: false, //this.workspaceActive,
        },
        {
          disabled: this.allButtonsDisabled,
          icon: "format-horizontal-align-center",
          label: "m/z calibration",
          path: "/mz-calibration",
          visible: false, //this.workspaceActive,
        },
        {
          disabled: this.allButtonsDisabled,
          icon: "flask",
          label: "Batch overview",
          path: "/batch-overview",
          visible: this.batchActive,
        },
        {
          disabled: this.allButtonsDisabled,
          icon: "sine-wave",
          label: "Sample signal",
          path: "/sample-signal",
          visible: false, //this.workspaceActive,
        },
        {
          disabled: this.allButtonsDisabled,
          icon: "table-multiple",
          label: "Data management",
          path: "/data-management",
          visible: false, //this.workspaceActive,
        },
      ].filter((b) => b.visible);
    },
    footerButtons() {
      return [
        {
          disabled: this.allButtonsDisabled,
          icon: "tune",
          label: "Settings",
          path: "/settings",
          visible: false,
        },
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
