<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="initData"
      @close="deactivateModal"
      :type="actionIs('delete') ? 'is-danger' : 'is-primary'"
    >
      <template v-if="actionIs('addToBatch')">
        <div class="modal-card" style="height: 85vh">
          <header class="modal-card-head">
            <p class="modal-card-title">Add target collection to batch</p>
          </header>
          <section class="modal-card-body">
            <b-field label="Name">
              <b-input v-model="newCollectionName" :disabled="true"></b-input>
            </b-field>
            <b-field label="Description">
              <b-input v-model="newCollectionDesc" :disabled="true"> </b-input>
            </b-field>
            <b-field label="Add to sample batch">
              <base-table
                :rows="sampleBatches"
                :cols="[{ field: 'sample_batch_name', label: 'Batch' }]"
                :checkable="true"
                @selectRows="selectBatchesToAddTo"
              >
              </base-table>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button expanded @click="modalActive = false"> Cancel </b-button>
            <b-button
              type="is-primary"
              expanded
              @click="
                () => {
                  updateTargetCollection([
                    {
                      target_collection_id: oldCollection.target_collection_id,
                      target_collection_name: newCollectionName,
                      target_collection_description: newCollectionDesc,
                      sample_batches: batchesToAddTo,
                    },
                  ]);
                  deactivateModal();
                }
              "
            >
              Update
            </b-button>
          </footer>
        </div>
      </template>
      <template v-if="actionIs('create')">
        <div class="modal-card" style="height: 85vh">
          <header class="modal-card-head">
            <p class="modal-card-title">Create new target collection</p>
          </header>
          <section class="modal-card-body">
            <b-field label="Name">
              <b-input
                v-model="newCollectionName"
                placeholder="Enter a name for the target collection"
              ></b-input>
            </b-field>
            <b-field
              label="Description"
              placeholder="Enter a description for your target collection"
            >
              <b-input v-model="newCollectionDesc"></b-input>
            </b-field>
            <b-field
              v-if="sampleBatchSelected"
              label="Add to selected sample batch"
            >
              <b-checkbox v-model="addToSampleBatch">
                Add to {{ sampleBatchSelected.sample_batch_name }}
              </b-checkbox>
            </b-field>
            <base-spreadsheet-input
              label="Target compounds"
              :cols="targetCompoundCols"
              @rowsPasted="loadTargetCompounds"
            ></base-spreadsheet-input>
          </section>
          <footer class="modal-card-foot">
            <b-button expanded @click="modalActive = false"> Cancel </b-button>
            <b-button
              type="is-primary"
              expanded
              @click="
                () => {
                  createTargetCollection([
                    {
                      target_collection_name: newCollectionName,
                      target_collection_description: newCollectionDesc,
                      target_compounds: newTargetCompounds,
                      sample_batches:
                        addToSampleBatch && sampleBatchSelected
                          ? [sampleBatchSelected]
                          : [],
                    },
                  ]);
                  deactivateModal();
                }
              "
            >
              Create
            </b-button>
          </footer>
        </div>
      </template>
      <template v-if="actionIs('update')">
        <div class="modal-card" style="height: 85vh">
          <header class="modal-card-head">
            <p class="modal-card-title">Update target collection</p>
          </header>
          <section class="modal-card-body">
            <b-field label="Name">
              <b-input
                v-model="newCollectionName"
                placeholder="Enter a name for the target collection"
              ></b-input>
            </b-field>
            <b-field
              label="Description"
              placeholder="Enter a description for your target collection"
            >
              <b-input v-model="newCollectionDesc"></b-input>
            </b-field>
            <base-spreadsheet-input
              label="Target compounds"
              :cols="targetCompoundCols"
              @rowsPasted="loadTargetCompounds"
            ></base-spreadsheet-input>
          </section>
          <footer class="modal-card-foot">
            <b-button expanded @click="modalActive = false"> Cancel </b-button>
            <b-button
              type="is-primary"
              expanded
              @click="
                () => {
                  updateTargetCollection([
                    {
                      target_collection_id: oldCollection.target_collection_id,
                      target_collection_name: newCollectionName,
                      target_collection_description: newCollectionDesc,
                      target_compounds: newTargetCompounds,
                    },
                  ]);
                  deactivateModal();
                }
              "
            >
              Update
            </b-button>
          </footer>
        </div>
      </template>
      <template v-else-if="actionIs('delete')">
        <section class="modal-card-body" style="min-height: 250px">
          <b-field>
            <b-radio
              v-model="removeFrom"
              native-value="sample-batch"
              type="is-info"
            >
              Remove from sample batch
            </b-radio>
          </b-field>
          <b-field>
            <b-radio
              v-model="removeFrom"
              native-value="database"
              type="is-danger"
            >
              Delete from database
            </b-radio>
          </b-field>
        </section>
        <footer class="modal-card-foot">
          <b-button
            type="is-warning"
            icon-left="close"
            expanded
            @click="deactivateModal"
          >
            Cancel
          </b-button>
          <b-button
            type="is-danger"
            icon-left="delete"
            expanded
            @click="
              () => {
                deleteTargetCollection([oldCollection.target_collection_id]);
                deactivateModal();
              }
            "
          >
            Remove
          </b-button>
        </footer>
      </template>
    </b-modal>
  </section>
</template>

<script>
import { mapMutations } from "vuex";
import { sync, call, get } from "vuex-pathify";

import BaseSpreadsheetInput from "./BaseSpreadsheetInput.vue";
import BaseTable from "./BaseTable.vue";

export default {
  name: "TheModalTargetCollectionOp",
  components: { BaseSpreadsheetInput, BaseTable },
  data: function () {
    return {
      batchesToAddTo: [],
      newCollectionName: "",
      newCollectionDesc: "",
      newTargetCompounds: [],
      addToSampleBatch: true,
      removeFrom: "sample-batch",
    };
  },
  computed: {
    ...sync({
      modalActive: "modal/targetCollectionOpActive",
      modalProps: "modal/targetCollectionOpProps",
    }),
    ...get({
      sampleBatches: "workspace/batches",
    }),
    fields() {
      return this.cols.map((col) => col.field);
    },
    action() {
      return this.modalProps.action;
    },
    oldCollection() {
      return this.modalProps.collection ?? null;
    },
    targetCompoundCols() {
      return [
        { field: "target_compound_name", label: "Name" },
        { field: "target_compound_formula", label: "Formula" },
        { field: "cas_number", label: "CAS Number" },
      ];
    },
    sampleBatchSelected() {
      return this.$store.getters["batch/activeRow"];
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    createTargetCollection(target_collections) {
      this.$api.emit("target_collection_create", target_collections);
    },
    deleteTargetCollection(target_collection_ids) {
      this.$api.emit("target_collection_delete", target_collection_ids);
    },
    initData() {
      if (this.oldCollection) {
        this.newCollectionName = this.oldCollection.target_collection_name;
        this.newCollectionDesc =
          this.oldCollection.target_collection_description;
      }
    },
    loadTargetCompounds(rows) {
      this.newTargetCompounds = rows;
    },
    selectBatchesToAddTo(newRows, oldRows) {
      this.batchesToAddTo = newRows.map((row) => row.sample_batch_id);
    },
    updateTargetCollection(target_collections) {
      this.$api.emit("target_collection_update", target_collections);
    },
  },
};
</script>
