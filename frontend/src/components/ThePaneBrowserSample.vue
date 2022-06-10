<template>
  <base-browser name="Samples" :levels="sampleLevels" :menu="menu">
  </base-browser>
</template>

<script>
import { mapActions, mapMutations, mapGetters } from "vuex";
import { bindState } from "$lib/store";

import BaseBrowser from "./BaseBrowser";

export default {
  name: "ThePaneBrowserSample",
  components: {
    BaseBrowser,
  },
  computed: {
    ...mapGetters({
      batchSelected: "sample/batch/selectedRow",
      itemsSelected: "sample/item/selectedRows",
    }),
    ...bindState({
      batchRows: "sample/batch/rows",
      itemRows: "sample/item/rows",
      modalSampleBatchOpProps: "modal/sampleBatchOpProps",
      modalSampleItemAttributesSave: "modal/sampleItemAttributesSave",
    }),
    sampleLevels() {
      return [
        {
          name: "Batch",
          slug: "sampleBatch",
          cols: [{ field: "name", label: "Batch", width: "90%" }],
          rows: this.batchRows,
          rowClick: this.batchToggle,
          opened: this.opened,
        },
        {
          name: "Item",
          slug: "sampleItem",
          cols: [{ field: "title", label: "Item", width: "90%" }],
          rows: this.itemRows,
          detailsIcon: null,
          rowClick: this.itemToggle,
        },
      ];
    },
    batchSelectedCount() {
      return this.batchSelected ? 1 : 0;
    },
    itemSelectedCount() {
      return this.itemsSelected ? this.itemsSelected.length : 0;
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
        this.batchSelectedCount == 0
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
    opened() {
      return this.batchSelected && this.itemRows.length > 0
        ? [this.batchSelected]
        : [];
    },
  },
  methods: {
    ...mapMutations({
      activateModal: "modal/activate",
    }),
    ...mapActions({
      calibrateItems: "calibration/calibrateItems",
      batchToggle: "sample/batch/toggle",
      itemToggle: "sample/item/toggle",
      sampleItemRead: "sample/item/read",
      sampleItemDelete: "sample/item/delete",
    }),
    batchCreate() {
      this.modalSampleBatchOpProps = {
        action: "create",
      };
      this.activateModal({
        modal: "sampleBatchOp",
      });
    },
    batchUpdate() {
      this.modalSampleBatchOpProps = {
        action: "update",
        batch: this.batchSelected,
      };
      this.activateModal({
        modal: "sampleBatchOp",
      });
    },
    batchDelete() {
      this.modalSampleBatchOpProps = {
        action: "delete",
        batch: this.batchSelected,
      };
      this.activateModal({
        modal: "sampleBatchOp",
      });
    },
    itemCalibrate() {
      let itemsToCalibrate = this.itemsSelected.filter(
        (item) => item.id !== this.itemFocused.id
      );
      let fit = this.itemFocused.mz_calibration;
      this.$buefy.dialog.confirm({
        title: "Copy mass calibration",
        message: `Copy calibration from ${this.itemFocused.title} to ${itemsToCalibrate.length} selected samples?`,
        confirmText: "Copy",
        onConfirm: () => {
          this.calibrateItems({ items: itemsToCalibrate, fit });
        },
      });
    },
    itemClick(row) {
      if (!this.controlPressed) {
        this.toggleItemSelection(row);
      } else {
        this.toggleItemFocus(row);
      }
    },
    async itemUpdate() {
      this.modalSampleItemAttributesSave = { action: "create" };
      this.activateModal({ modal: "sampleItemAttributesSave" });
    },
    itemDelete() {
      this.$buefy.dialog.confirm({
        title: "Deleting items",
        message: `Delete ${this.itemsSelected.length} item(s) from ${this.batchSelected.name} ?`,
        confirmText: "Delete",
        onConfirm: () => {
          let itemIds = this.itemsSelected.map((item) => item.id);
          this.sampleItemDelete(itemIds);
        },
      });
    },
  },
};
</script>
