<template>
  <the-layout-sidebar>
    <b-tabs type="is-boxed">
      <b-tab-item label="Batch Items" icon="test-tube">
        <section>
          <div class="columns">
            <div class="column is-2 base-browser-sidebar">
              <the-pane-browser-sample></the-pane-browser-sample>
            </div>
            <div class="column" style="padding-right: 1em">
              <div style="padding-top: 0.5em; padding-bottom: 1em">
                <h1 style="font-size: 16px; text-align: left">
                  <p>
                    <b>Select Sample Files:</b>
                  </p>
                </h1>
              </div>
              <div class="columns">
                <div class="column is-half">
                  <b-datetimepicker
                    placeholder="Starting from..."
                    v-model="sampleFileMinDateTime"
                  >
                  </b-datetimepicker>
                </div>
                <div class="column is-half">
                  <b-datetimepicker
                    placeholder="Until..."
                    v-model="sampleFileMaxDateTime"
                  >
                  </b-datetimepicker>
                </div>
              </div>
              <base-table
                :key="sampleFileTableDataKey"
                :rows="sampleFileRows"
                :cols="sampleFileCols"
                :checkable="true"
                :searchable="true"
                :height="srcTableHeight"
                @selectRows="selectSampleFiles"
              >
              </base-table>
              <div style="padding-top: 1.5em; padding-bottom: 1.5em">
                <h1 style="font-size: 16px; text-align: left">
                  <p>
                    <b>
                      {{
                        batchSelected
                        ? "Items to add to batch: " + batchSelected.name
                        : "Please select a batch"
                      }}
                    </b>
                  </p>
                </h1>
              </div>
              <base-table
                :rows="sampleItemRows"
                :cols="sampleItemCols"
                :checkable="false"
                :searchable="false"
                :height="targetTableHeight"
              >
              </base-table>
            </div>
          </div>

          <b-button
            @click="itemsAdd"
            style="position: fixed; right: 5em; bottom: 2em"
            icon-left="content-save"
            type="is-primary"
            :disabled="!sampleItemRows.length || !batchSelected"
            rounded
          >
            Add Items
          </b-button>
        </section>
      </b-tab-item>
    </b-tabs>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar";
import ThePaneBrowserSample from "./ThePaneBrowserSample";
import BaseTable from "./BaseTable";

import { bindState } from "$lib/store";
import { mapActions } from "vuex";

export default {
  name: "ThePageSampleManagement",
  components: {
    TheLayoutSidebar,
    ThePaneBrowserSample,
    BaseTable,
  },
  data: function () {
    return {
      sampleFileRows: [],
      sampleItemRows: [],
      sampleFileMinDateTime: null,
      sampleFileMaxDateTime: null,
      sampleFileTableDataKey: 0,
    };
  },
  computed: {
    ...bindState({
      workspaceActive: "workspace/active",
      sampleFileSchema: "sample/file/schema/row",
      sampleItemSchema: "sample/item/schema/row",
      $sampleFileListRequest: "sample/file/$listRequest",
      $sampleFileListResponse: "sample/file/$listResponse",
      batchSelected: "sample/batch/selection/row",
    }),
    // layout
    srcTableHeight() {
      return "calc(40vh)";
    },
    targetTableHeight() {
      return "calc(30vh)";
    },
    // columns
    sampleFileCols() {
      let result = [];
      this.sampleFileSchema.forEach((el) => {
        if (el !== "id") result.push({ field: el, label: el });
      });
      return result;
    },
    sampleItemCols() {
      let result = [];
      this.sampleItemSchema.forEach((field) => {
        if (field !== "id" && field !== "batchId")
          result.push({ field: field, label: field });
      });
      return result;
    },
  },
  methods: {
    ...mapActions({
      sampleItemCreate: "sample/item/create",
    }),
    selectSampleFiles(files) {
      let fields = this.sampleItemSchema.filter(
        (field) => !["id", "batchId"].includes(field)
      );
      this.sampleItemRows = files.map((file) =>
        fields
          .map((field) => ({ [field]: file[field] }))
          .reduce((i, j) => ({ ...i, ...j }), {})
      );
    },
    itemsAdd() {
      let n = this.sampleItemRows.length;
      let s = n > 1 ? "s" : "";
      let w = this.workspaceActive.name;
      let b = this.batchSelected.name;
      this.$buefy.dialog.confirm({
        title: "Batch Items",
        message: `
          Add ${n} sample item${s} to batch ${b} in workspace ${w}?
        `,
        confirmText: "Add",
        onConfirm: () => {
          let rows = this.sampleItemRows.map((row) => ({
            ...row,
            batchId: this.batchSelected.id,
          }));
          this.sampleItemCreate(rows);
        },
      });
    },
    getSampleFiles() {
      if (!this.sampleFileMinDateTime || !this.sampleFileMaxDateTime) return;
      // reset sampleItems for new range selected
      this.sampleItemRows = [];
      // reset sampleFiles table to clean up internal static selection data
      this.sampleFileTableDataKey++;
      // recalculate from UTC to local timezone
      let d1 =
        this.sampleFileMinDateTime -
        this.sampleFileMinDateTime.getTimezoneOffset() * 60000;
      let d2 =
        this.sampleFileMaxDateTime -
        this.sampleFileMaxDateTime.getTimezoneOffset() * 60000;
      this.$sampleFileListRequest = {
        column: "datetime",
        min_value: new Date(d1).toISOString(),
        max_value: new Date(d2).toISOString(),
      };
    },
  },
  watch: {
    $sampleFileListResponse: function (response) {
      this.sampleFileRows = response.records;
    },
    sampleFileMinDateTime: function () {
      this.getSampleFiles();
    },
    sampleFileMaxDateTime: function () {
      this.getSampleFiles();
    },
  },
};
</script>
