<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @close="deactivateModal"
    >
      <div class="modal-card" style="width: 100vw">
        <header class="modal-card-head">
          <h2 class="subtitle">Import a batch of samples</h2>
        </header>
        <section class="modal-card-body" style="min-height: 250px;">
          <base-spreadsheet-input
            label="CSV"
            :cols="csvCols"
            :colsFromHeader="true"
            @colsPasted="(cols) => {
              csvCols = cols;
            }"
            @rowsPasted="(rows) => {
              csvRows = rows;
            }"
          >
          </base-spreadsheet-input>
        </section>
        <footer class="modal-card-foot">
          <b-button expanded @click="modalActive = false"> Cancel </b-button>
          <b-button
            type="is-primary"
            expanded
            :disabled="!readyToProcess"
            @click="
              () => {
                processBatch();
                deactivateModal();
              }
            "
          >
            Process
          </b-button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>

<script>
import { mapMutations } from "vuex";
import { get, sync } from "vuex-pathify";
import { parseAutosamplerCsv } from "../lib/util";

import BaseSpreadsheetInput from "./BaseSpreadsheetInput.vue";
import BaseTable from "./BaseTable.vue";

export default {
  name: "TheModalSampleBatchImport",
  components: {
    BaseSpreadsheetInput,
    BaseTable
  },
  props: {},
  data: function () {
    return {
      action: null,
      csvCols: [],
      csvRows: [],
      parsedRows: null,
    };
  },
  computed: {
    ...get({
      acquisitions: "instrument/acquisitions",
      batchActive: "batch/active",
      sampleItemSchema: "app/schema@sample_item",
    }),
    ...sync({
      modalActive: "modal/sampleBatchImportActive",
    }),
    readyToProcess() {
      return (
        this.parsedRows
        && this.acquisitions
        && this.parsedRows.length == this.acquisitions.length
      );
    },
    // readyToProcess() {
    //   return this.sampleItemsToCreate.length > 0
    //     && this.sampleItemSchema.map((dbCol) => dbCol.field)
    //       .every((field) => (
    //         field == 'sample_item_id'
    //         || Object.keys(this.sampleItemsToCreate[0]).includes(field)
    //         )
    //       )
    //   },
    // sampleItemsToCreate() {
    //   let items = [];
    //   for (let row of this.csvRows) {
    //     // convert [{label, value...}, ...] to object
    //     let props = {};
    //     let sample_item_attributes = {};
    //     this.csvCols.forEach(
    //       (col) => {
    //         if (
    //           this.sampleItemSchema.map((dbCol) => dbCol.field)
    //           .includes(col.field)
    //           ) {
    //           props[col.field] = row[col.field];
    //         } else {
    //           sample_item_attributes[col.field] = row[col.field];
    //         }
    //     });
    //     let newSampleItem = {
    //       ...props,
    //       sample_item_attributes,
    //       sample_batch_id: this.batchActive.sample_batch_id,
    //       };
    //     items.push(newSampleItem);
    //   }
    //   return items;
    // },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    processBatch() {
      let items = [];
      for (let [i, row] of Object.entries(this.parsedRows)) {
        let newSampleItem = {
          filename: this.acquisitions[i].filename,
          sample_batch_id: this.batchActive.sample_batch_id
        };
        let attributes = {};
        for (const key in row) {
          const attr = key.toLowerCase().replaceAll(/[\s-]/g, '_');
          if (attr.startsWith('sample_')) {
            // sampl_name or sample_type
            const prop = attr.replace('sample', 'sample_item');
            newSampleItem[prop] = row[key];
          } else {
            attributes[attr] = row[key];
          }
        }
        newSampleItem.sample_item_attributes = attributes;
        items.push(newSampleItem);
      }
      console.log(items);
      this.$api.emit('scenthound_process_samples', items);
    },
  },
  watch: {
    csvRows() {
      this.parsedRows = parseAutosamplerCsv(this.csvRows);
    },
  },
};
</script>

