<template>
  <base-browser name="Samples" :levels="sampleLevels">
    <template v-slot:header>
      <b-button
        icon-left="plus"
        size="is-small"
        @click="
          () => {
            modalProps = {
              action: 'create',
            };
            activateModal({
              modal: 'batchSave',
            });
          }
        "
      >
        <b>create batch</b>
      </b-button>
    </template>
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
      batchRows: "workspace/sample/batchRows",
      itemRows: "workspace/sample/itemRows",
      modalProps: "ui/modal/batchSaveProps",
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
          cols: [{ field: "filename", label: "Filename", width: "90%" }],
          rows: this.itemRows,
          detailsIcon: null,
          rowClick: this.toggleSampleItemSelection,
        },
      ];
    },
  },
  methods: {
    ...mapMutations({
      activateModal: "ui/modal/activate",
    }),
    ...mapActions({
      batchOpen: "workspace/sample/batchOpen",
      batchClose: "workspace/sample/batchClose",
      toggleSampleBatchSelection: "workspace/sample/batchSelectionToggle",
      toggleSampleItemSelection: "workspace/sample/itemSelectionToggle",
    }),
  },
};
</script>