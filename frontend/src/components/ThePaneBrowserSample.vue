<template>
  <base-browser name="Samples" :levels="sampleLevels"> </base-browser>
</template>

<script>
import { bindState } from "$lib/store";

import { mapActions } from "vuex";

import BaseBrowser from "./BaseBrowser";

export default {
  name: "ThePaneBrowserSample",
  components: {
    BaseBrowser,
  },
  computed: {
    ...bindState({
      batchRows: "workspace/sample/batchRows",
      itemRows: "workspace/sample/itemRows",
    }),
    sampleLevels: function () {
      return [
        {
          name: "Batch",
          slug: "batch",
          cols: [{ field: "name", label: "Batch", width: "90%" }],
          rows: this.batchRows,
          detailsOpen: this.openBatch,
          detailsClose: this.closeBatch,
          rowClick: this.toggleSampleBatchSelection,
        },
        {
          name: "Item",
          slug: "item",
          cols: [{ field: "filename", label: "Filename", width: "90%" }],
          rows: this.itemRows,
          detailsIcon: null,
          rowClick: this.toggleSampleItemSelection,
        },
      ];
    },
  },
  methods: {
    ...mapActions({
      openBatch: "workspace/sample/openBatch",
      closeBatch: "workspace/sample/closeBatch",
      toggleSampleBatchSelection: "workspace/sample/batchToggleSelection",
      toggleSampleItemSelection: "workspace/sample/itemToggleSelection",
    }),
  },
};
</script>