<template>
  <base-browser name="Samples" :levels="sampleLevels" :menu="menu">
  </base-browser>
</template>

<script>
import { mapMutations } from "vuex";
import { sync, get, call } from "vuex-pathify";

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
      items: "batch/sampleItems",
      itemsSelected: "batch/sampleItemsSelected",
      itemsToCalibrate: "batch/sampleItemsSelected",
      itemFocused: "batch/sampleItemFocused",
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
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.sample_peak_height_sum),
                };
              },
            },
          ],
          rows: this.items,
          defaultSort: ["datetime", "asc"],
          detailsIcon: 'magnify',
          detailsOpen: this.itemShow,
          rowClick: this.itemSelect,
          opened: [],
        },
      ];
    },
    batchActiveCount() {
      return this.batchActive ? 1 : 0;
    },
    itemSelectedCount() {
      return this.itemsSelected.length;
    },
    menu() {
      // sample batch
      let createBatchButton = {
        label: "Create sample batch",
        onClick: this.batchCreate,
      };
      let updateBatchButton = {
        label: "Update sample batch",
        onClick: this.batchUpdate,
      };
      let deleteBatchButton = {
        label: "Delete sample batch",
        onClick: this.batchDelete,
      };
      let batchButtons =
        this.batchActiveCount == 0
          ? [createBatchButton]
          : [createBatchButton, updateBatchButton, deleteBatchButton];
      // sample items
      let s = this.itemSelectedCount > 1 ? "s" : "";
      let updateItemButton = {
        label: `Update sample item${s}`,
        onClick: this.itemUpdate,
      };
      let deleteItemButton = {
        label: `Delete sample item${s}`,
        onClick: this.itemDelete,
      };
      let itemButtons =
        this.itemSelectedCount == 0
          ? []
          : this.itemSelectedCount == 1
          ? [updateItemButton, deleteItemButton]
          : [deleteItemButton];
      //
      let calibrateItemButton = {
        label: `Calibrate sample item${s}`,
        onClick: this.itemCalibrate,
      };
      let calibrateButtons = this.itemFocused ? [calibrateItemButton] : [];
      // menu
      return [...batchButtons, ...itemButtons, ...calibrateButtons];
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
      calibrateItems: "calibration/calibrateItems",
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
    batchUpdate() {
      this.modalSampleBatchOpProps = {
        action: "update",
        batch: this.batchActive,
      };
      this.activateModal({
        modal: "sampleBatchOp",
      });
    },
    itemCalibrate() {
      let fit = this.itemFocused.mzCalibration;
      this.$buefy.dialog.confirm({
        title: "Copy mass calibration",
        message: `Copy calibration from ${this.itemFocused.title} to ${this.itemsToCalibrate.length} selected samples?`,
        confirmText: "Copy",
        onConfirm: () => {
          this.calibrateItems({ items: itemsToCalibrate, fit });
        },
      });
    },
    async itemUpdate() {
      this.modalSampleItemAttributesSaveProps = {
        action: "update",
        sampleItemRecordToLoad: this.itemFocused,
      };
      this.activateModal({ modal: "sampleItemAttributesSave" });
    },
    itemDelete() {
      this.$buefy.dialog.confirm({
        title: "Deleting items",
        message: `Delete ${this.itemsSelected.length} item(s) from ${this.batchActive.sample_batch_name}?`,
        confirmText: "Delete",
        onConfirm: () => {
          let itemIds = this.itemsSelected.map((item) => item.sample_item_id);
          this.$api.emit('sample_item_delete', itemIds);
        },
      });
    },
    itemSelect(row) {
      this.itemToggle(row);
      this.itemFocus(row);
    },
    itemShow(row) {
      if (!this.itemFocused
        || !(this.itemFocused.sample_item_id == row.sample_item_id)) {
        this.itemSelect(row);
      }
      if (this.itemFocused) {
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
