<template>
  <base-browser name="Samples" :levels="sampleLevels" :menu="menu">
  </base-browser>
</template>

<script>
import { mapActions, mapMutations } from "vuex";
import { bindState } from "$lib/store";

import BaseBrowser from "./BaseBrowser";

export default {
  name: "ThePaneBrowserSample",
  components: {
    BaseBrowser,
  },
  computed: {
    ...bindState({
      batchRows: "sample/batch/rows",
      itemRows: "sample/item/rows",
      batchSelected: "sample/batch/selection/row",
      itemsSelected: "sample/item/selection/rows",
      modalSampleBatchOpProps: "modal/sampleBatchOpProps",
      modalSampleItemAttributesSave: "modal/sampleItemAttributesSave",
      controlPressed: "key/control",
    }),
    sampleLevels() {
      return [
        {
          name: "Batch",
          slug: "batch",
          cols: [{ field: "name", label: "Batch", width: "90%" }],
          rows: this.batchRows,
          rowClick: this.toggleBatchSelection,
          rowStatus: this.$store.getters["sample/batch/status"],
          opened: this.opened,
        },
        {
          name: "Item",
          slug: "item",
          cols: [{ field: "title", label: "Title", width: "90%" }],
          rows: this.itemRows,
          detailsIcon: null,
          rowClick: this.itemClick,
          rowStatus: this.$store.getters["sample/item/status"],
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
      // menu
      return [...batchButtons, ...itemButtons];
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
      toggleBatchSelection: "sample/batch/selection/toggle",
      toggleItemSelection: "sample/item/selection/toggle",
      toggleItemFocus: "sample/item/focus/toggle",
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
      // get the item data into the modal fields
      await this.$nextTick();
      this.sampleItemRead({ id: this.itemsSelected[0].id });
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
