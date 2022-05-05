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
                    v-model="sampleFileMinDateTime">
                  </b-datetimepicker>
                </div>
                <div class="column is-half">
                  <b-datetimepicker
                    placeholder="Until..."
                    v-model="sampleFileMaxDateTime">
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
                    <b>Items to add to {{workspaceActive.name}} batches: {{batchesSelected.map(b => b.name)}} :</b>
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
            @click="addItems"
            style="position: fixed; right: 5em; bottom: 2em"
            icon-left="content-save"
            type="is-primary"
            :disabled="sampleItemRows.length == 0 || batchesSelected.length == 0"
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
import { mapMutations } from "vuex";

export default {
  name: "ThePageSampleManagement",
  components: {
    TheLayoutSidebar,
    ThePaneBrowserSample,
    BaseTable,
  },
  data: function() {
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
      sampleFileSchema: "sample/fileSchema",
      sampleItemSchema: "sample/itemSchema",
      $sampleFileListResponse: "sample/$fileListResponse",
    }),
    batchesSelected: function() {
      return this.$store.getters["sample/batchesSelected"];
    },
    // layout
    srcTableHeight() {
      // return "calc(50vh - 140px)";
      return "calc(40vh)";
    },
    targetTableHeight() {
      return "calc(30vh)";
    },
    sampleFileCols() {
      let result = [];
      this.sampleFileSchema.schema.forEach(
        (el) => {
            if (el !== 'id')
              result.push({field: el, label: el})
          }
      );
      return result;
    },
    sampleItemCols() {
      let result = [];
      this.sampleItemSchema.schema.forEach(
        (field) => {
            if (field !== 'id' && field !== 'batchId')
              result.push({field: field, label: field})
          }
      );
      return result;
    },
  },
  methods: {
    ...mapMutations({
      $sampleFileListRequest: "sample/fileListRequest",
      sampleItemUpdate: "sample/itemUpdate",
    }),
    selectSampleFiles(rows) {
      let result = [];
      rows.forEach( (fileRow) => {
          let itemRow = {};
          this.sampleItemSchema.schema.forEach( field => {
            if (field !== 'id' && field != 'batchId' && fileRow[field]) {
              itemRow[field] = fileRow[field];
            }}
          );
          result.push(itemRow);
        }
      );
      this.sampleItemRows = result;
    },
    addItems() {
      let items = this.sampleItemRows.length == 1 ?
                `1  item` : `${this.sampleItemRows.length}  items`
      let batches = this.batchesSelected.length == 1 ? 'batch' : 'batches'
      this.$buefy.dialog.confirm({
        title: "Batch Items",
        message: `Add  ${items} to ${this.workspaceActive.name} ${batches} ${this.batchesSelected.map(b => b.name)}?`,
        confirmText: "Add",
        onConfirm: () => {
          let rows = [];
          this.batchesSelected.forEach( (batch) => {
            this.sampleItemRows.forEach( (row) => {
              rows.push({...row, batchId: batch.id});
            });
          });
          this.sampleItemUpdate(rows);
        },
      });
    },
    getSampleFiles() {
      if (!this.sampleFileMinDateTime || !this.sampleFileMaxDateTime)
        return;
      // reset sampleItems for new range selected
      this.sampleItemRows = [];
      // reset sampleFiles table to clean up internal static selection data
      this.sampleFileTableDataKey++;
      // recalculate from UTC to local timezone
      let d1 = this.sampleFileMinDateTime - (this.sampleFileMinDateTime.getTimezoneOffset() * 60000);
      let d2 = this.sampleFileMaxDateTime - (this.sampleFileMaxDateTime.getTimezoneOffset() * 60000);
      this.$sampleFileListRequest({
        column: 'datetime',
        min_value: new Date(d1).toISOString(),
        max_value: new Date(d2).toISOString()
      });
    },
  },
  watch: {
    $sampleFileListResponse: function (response) {
      this.sampleFileRows = response.records;
    },
    sampleFileMinDateTime: function() {
      this.getSampleFiles();
    },
    sampleFileMaxDateTime: function() {
      this.getSampleFiles();
    },
  },
};
</script>
