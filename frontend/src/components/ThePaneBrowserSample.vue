<template>
  <base-browser name="Samples" :levels="sampleLevels" :menu="menu">
  </base-browser>
</template>

<script>
import { mapMutations } from "vuex";
import { sync, get, call } from "vuex-pathify";
import table from "../lib/table";

import BaseBrowser from "./BaseBrowser.vue";

export default {
  name: "ThePaneBrowserSample",
  components: {
    BaseBrowser,
  },
  computed: {
    ...get({
      batches: "workspace/batches",
      batchActive: "batch/active",
      batchMatchCompounds: "batch/matchCompounds",
      batchMatchIons: "batch/matchIons",
      sampleItems: "batch/sampleItems",
      sampleItemFocused: "batch/sampleItemFocused",
      targetCollections: "batch/targetCollections",
    }),
    ...sync({
      modalSampleBatchOpProps: "modal/sampleBatchOpProps",
      modalSampleItemAttributesSaveProps: "modal/sampleItemAttributesSaveProps",
      modalSampleItemOverviewProps: "modal/sampleItemOverviewProps",
    }),
    sampleLevels() {
      let hidden = this.batchActive ? false : true;
      return [
        {
          name: "Batch",
          slug: "sample_batch",
          cols: [
            { field: "sample_batch_name", label: "Batch", width: "90%" },
          ],
          detailsIcon: 'none',
          rows: this.batches,
          rowClick: this.batchToggle,
          opened: this.openedBatch,
        },
        {
          name: "Item",
          slug: "sample_item",
          cols: [
            { field: "sample_item_name", label: "Item", width: "90%" },
            { field: "datetime", label: "Datetime", width: "0%", hidden:true },
            {
              field: "match_score",
              label: "Score",
              width: "10%",
              displayMatchScore: false,
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.sample_peak_height_sum),
                };
              },
            },
          ],
          rows: this.sampleItems,
          defaultSort: ["datetime", "asc"],
          // detailsIcon: 'magnify',
          // detailsOpen: this.itemShow,
          detailsIcon: 'none',
          rowClick: this.itemSelect,
          opened: [],
        },
      ];
    },
    batchActiveCount() {
      return this.batchActive ? 1 : 0;
    },
    menu() {
      // sample batch
      let createBatchButton = {
        label: "Create sample batch",
        onClick: this.batchCreate,
      };
      let deleteBatchButton = {
        label: "Delete sample batch",
        onClick: this.batchDelete,
      };
      let exportBatchButton = {
        label: "Export sample batch",
        onClick: this.batchExport,
      };
      let updateBatchButton = {
        label: "Update sample batch",
        onClick: this.batchUpdate,
      };
      let batchButtons =
        this.batchActiveCount == 0
          ? [createBatchButton]
          : [
            createBatchButton,
            updateBatchButton,
            deleteBatchButton,
            exportBatchButton
          ];
      // sample items
      let updateItemButton = {
        label: `Update sample item`,
        onClick: this.itemUpdate,
      };
      let deleteItemButton = {
        label: `Delete sample item`,
        onClick: this.itemDelete,
      };
      let itemButtons =
        this.sampleItemFocused
          ? [updateItemButton, deleteItemButton]
          : [];
      // menu
      return [...batchButtons, ...itemButtons];
    },
    openedBatch() {
      return this.batchActive
        ? this.batches.filter((batch) => 
            batch.sample_batch_id == this.batchActive.sample_batch_id
            )
        : [];
    },
  },
  created: function () {
    this.formatter = new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  },
  methods: {
    ...mapMutations({
      activateModal: "modal/activate",
    }),
    ...call({
      batchLoad: "batch/load",
      itemFocus: "batch/sampleItemFocus",
      itemToggle: "batch/sampleItemToggle",
      batchToggle: "batch/batchToggle",
    }),
    batchCreate() {
      this.modalSampleBatchOpProps = {
        action: "create",
      };
      this.activateModal({
        modal: "sampleBatchOp",
      });
    },
    batchDelete() {
      this.modalSampleBatchOpProps = {
        action: "delete",
        batch: this.batchActive,
      };
      this.activateModal({
        modal: "sampleBatchOp",
      });
    },
    batchExport() {
      const sampleItemCols = [
        {
          field: "sample_item_name",
          label: "Sample name",
        },
        {
          field: "filename",
          label: "Filename",
        },
        {
          field: "datetime",
          label: "Datetime",
        },
      ];
      const matchCompoundCols = [
        { field: "sample_item_name", label: "Sample name" },
        { field: "filename", label: "Filename" },
        { field: "target_compound_name", label: "Compound name" },
        { field: "target_compound_formula", label: "Compound formula" },
        { field: "sample_peak_height_sum", label: "Sample peak intensity" },
        { field: "match_score", label: "Match score" },
      ];
      const matchIonCols = [
        { field: "sample_item_name", label: "Sample name" },
        { field: "filename", label: "Filename" },
        { field: "target_compound_name", label: "Compound name" },
        { field: "target_compound_formula", label: "Compound formula" },
        { field: "target_ion_mechanism", label: "Ionization mechanism" },
        { field: "target_ion_formula", label: "Ion formula" },
        { field: "sample_peak_height_sum", label: "Sample peak intensity" },
        { field: "match_score", label: "Match score" },
      ];
      table.toSpreadsheet("test.xlsx", [
        {
          name: "Samples",
          rows: this.sampleItems,
          cols: sampleItemCols
        },
        {
          name: "Match compounds",
          rows: this.batchMatchCompounds,
          cols: matchCompoundCols
        },
        {
          name: "Match ions",
          rows: this.batchMatchIons,
          cols: matchIonCols
        },
      ]);
    },
    batchUpdate() {
      this.modalSampleBatchOpProps = {
        action: "update",
        batch: this.batchActive,
      };
      this.activateModal({
        modal: "sampleBatchOp",
      });
    },
    async itemUpdate() {
      this.modalSampleItemAttributesSaveProps = {
        action: "update",
        sampleItemRecordToLoad: this.sampleItemFocused,
      };
      this.activateModal({ modal: "sampleItemAttributesSave" });
    },
    itemDelete() {
      this.$buefy.dialog.confirm({
        title: "Deleting item",
        message: `Delete sample "${this.sampleItemFocused.sample_item_name}"
          from batch "${this.batchActive.sample_batch_name}"?`,
        confirmText: "Delete",
        onConfirm: () => {
          const itemId = this.sampleItemFocused.sample_item_id;
          // defocus
          this.itemFocus(this.sampleItemFocused);
          this.$api.emit('sample_item_delete', [itemId]);
        },
      });
    },
    itemSelect(row) {
      this.itemToggle(row);
      this.itemFocus(row);
    },
    itemShow(row) {
      if (!this.sampleItemFocused
        || !(this.sampleItemFocused.sample_item_id == row.sample_item_id)) {
        this.itemSelect(row);
      }
      if (this.sampleItemFocused) {
        this.modalSampleItemOverviewProps = {
          sampleItemRecordToLoad: row,
        };
        this.activateModal({
          modal: "sampleItemOverview",
        });
      }
    },
  },
};
</script>
