<template>
  <the-layout-sidebar>
    <section>
      <div class="columns">
        <div class="column is-2 base-browser-sidebar">
          <the-pane-browser-sample></the-pane-browser-sample>
        </div>
        <div class="column is-10" style="padding-right: 1em">
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
            :height="sampleFileTableHeight"
            @selectRows="selectSampleFiles"
          >
          </base-table>
          <div style="padding-top: 1.5em; padding-bottom: 1.5em">
            <h1 style="font-size: 16px; text-align: left">
              <p>
                <b>
                  {{
                    batchActive
                      ? "Items to add to batch: " + batchActive.name
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
            :height="sampleItemTableHeight"
          >
          </base-table>
        </div>
      </div>

      <b-button
        @click="itemsAdd"
        style="position: fixed; right: 5em; bottom: 2em"
        icon-left="content-save"
        type="is-primary"
        :disabled="!sampleItemRows.length || !batchActive"
        rounded
      >
        Add Items
      </b-button>
    </section>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import ThePaneBrowserSample from "./ThePaneBrowserSample.vue";
import BaseTable from "./BaseTable.vue";

import { sync, get } from "vuex-pathify";

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
      sampleFileMinDateTime: null,
      sampleFileMaxDateTime: null,
      sampleFileTableDataKey: 0,
      sampleItemRows: [],
    };
  },
  computed: {
    ...sync({
    }),
    ...get({
      batchActive: "batch/active",
      workspaces: "app/workspaces",
      workspaceActive: "workspace/active",
      sampleFileCols: "app/schema@sample_file",
      sampleItemCols: "app/schema@sample_item",
    }),
    sampleFileTableHeight() {
      return "calc(40vh)";
    },
    sampleItemTableHeight() {
      return "calc(30vh)";
    },
  },
  methods: {
    sampleItemCreate(items) {
      this.$api.emit('sample_item_create', items);
    },
    selectSampleFiles(selectedFiles) {
      let fields = this.sampleItemCols
        .map((col) => col.field
      );
      this.sampleItemRows = selectedFiles.map((file) =>
        fields
          .map((field) => ({ [field]: file[field] }))
          .reduce((i, j) => ({ ...i, ...j }), {})
      );
    },
    itemsAdd() {
      let n = this.sampleItemRows.length;
      let s = n > 1 ? "s" : "";
      let w = this.workspaceActive.name;
      let b = this.batchActive.name;
      this.$buefy.dialog.confirm({
        title: "Batch Items",
        message: `
          Add ${n} sample item${s} to batch ${b} in workspace ${w}?
        `,
        confirmText: "Add",
        onConfirm: () => {
          let rows = this.sampleItemRows.map((row) => ({
            ...row,
            sample_batch_id: this.batchActive.sample_batch_id,
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
      let dt1 = new Date(this.sampleFileMinDateTime).toISOString();
      let dt2 = new Date(this.sampleFileMaxDateTime).toISOString();
      this.$api
        .query(`--sql
          SELECT *
          FROM sample_file
          WHERE datetime_utc BETWEEN '${dt1}' AND '${dt2}'
        `)
        .then((res) => {
          this.sampleFileRows = res.toArray().map((row) => ({...row}));
        });
    },
  },
  watch: {
    sampleFileMinDateTime: function () {
      this.getSampleFiles();
    },
    sampleFileMaxDateTime: function () {
      this.getSampleFiles();
    },
  },
};
</script>
