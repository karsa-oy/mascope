<template>
  <base-browser
    name="Samples"
    :levels="sampleLevels"
    :menu="[
      {
        label: 'Create batch',
        onClick: () => {
          modalProps = {
            action: 'create',
          };
          activateModal({
            modal: 'batchSave',
          });
        },
      },
    ]"
  >
  </base-browser>
</template>

<script>
import { bindState } from "$lib/store";

import { mapActions, mapMutations } from "vuex";

import BaseBrowser from "./BaseBrowser";

export default {
  name: "ThePaneBrowserSample",
  components: {
    BaseBrowser,
  },
  computed: {
    ...bindState({
      batchRows: "sample/batchRows",
      itemRows: "sample/itemRows",
      modalProps: "modal/batchSaveProps",
    }),
    sampleLevels: function () {
      return [
        {
          name: "Batch",
          slug: "batch",
          cols: [{ field: "name", label: "Batch", width: "90%" }],
          rows: this.batchRows,
          detailsOpen: this.batchOpen,
          detailsClose: this.batchClose,
          rowClick: this.toggleSampleBatchSelection,
        },
        {
          name: "Item",
          slug: "item",
          cols: [{ field: "title", label: "Title", width: "90%" }],
          rows: this.itemRows,
          detailsIcon: null,
          rowClick: this.toggleSampleItemSelection,
        },
      ];
    },
  },
  methods: {
    ...mapMutations({
      activateModal: "modal/activate",
    }),
    ...mapActions({
      batchOpen: "sample/batchOpen",
      batchClose: "sample/batchClose",
      toggleSampleBatchSelection: "sample/batchSelectionToggle",
      toggleSampleItemSelection: "sample/itemSelectionToggle",
    }),
  },
};
</script>