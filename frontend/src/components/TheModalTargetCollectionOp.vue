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
      <template v-if="actionIs('editBatchCollections')">
        <div class="modal-card" style="height: 85vh">
          <header class="modal-card-head">
            <p class="modal-card-title">Add target collection to batch</p>
          </header>
          <section class="modal-card-body">
            <b-field
              :label="`Select target collections for sample batch    ${selectedBatchInfo.sample_batch_name}`"
            >
              <b-table
                :data="targetCollectionsAll"
                :columns="[
                  { field: 'target_collection_name', label: 'Name' },
                  {
                    field: 'target_collection_description',
                    label: 'Description',
                  },
                ]"
                checkable
                :checked-rows.sync="targetCollectionsChecked"
              >
              </b-table>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button
              type="is-dark"
              icon-left="close"
              expanded
              @click="deactivateModal"
            >
              Cancel
            </b-button>
            <b-button
              type="is-primary"
              icon-left="content-save"
              expanded
              @click="
                () => {
                  editBatchCollections(targetCollectionsChecked, selectedBatch);
                  deactivateModal();
                }
              "
            >
              Set collections
            </b-button>
          </footer>
        </div>
      </template>
      <template v-if="actionIs('manageSelectedCollectionBatches')">
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
            <b-field
              :label="`Select batches for target collection ${targetCollectionActiveInfo.target_collection_name}`"
            >
              <b-table
                :data="sampleBatches"
                :columns="[{ field: 'sample_batch_name', label: 'Batch' }]"
                checkable
                :checked-rows.sync="sampleBatchesChecked"
              >
              </b-table>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button
              type="is-dark"
              icon-left="close"
              expanded
              @click="modalActive = false"
            >
              Cancel
            </b-button>
            <b-button
              type="is-primary"
              icon-left="content-save"
              expanded
              @click="
                () => {
                  manageSelectedCollectionBatches(
                    sampleBatchesChecked,
                    selectedCollection
                  );
                  deactivateModal();
                }
              "
            >
              Save
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
            <base-spreadsheet-input
              label="Target compounds"
              :cols="targetCompoundCols"
              @rowsPasted="loadTargetCompounds"
            ></base-spreadsheet-input>
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
            <b-button
              type="is-dark"
              icon-left="close"
              expanded
              @click="modalActive = false"
            >
              Cancel
            </b-button>
            <b-button
              type="is-primary"
              icon-left="content-save"
              expanded
              @click="
                () => {
                  createTargetCollection({
                    target_collection_name: newCollectionName,
                    target_collection_description: newCollectionDesc,
                    target_compounds: newTargetCompounds,
                    sample_batches: this.batchesToAddTo
                      ? this.batchesToAddTo
                      : [],
                  });
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
            <b-button type="is-warning" expanded @click="modalActive = false">
              Cancel
            </b-button>
            <b-button
              type="is-primary"
              expanded
              @click="
                () => {
                  updateTargetCollection([
                    {
                      target_collection_id:
                        selectedCollection.target_collection_id,
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
        <div class="modal-card" style="height: 40vh">
          <header class="modal-card-head">
            <p class="modal-card-title">Delete terget colletion</p>
          </header>
          <section
            class="modal-card-body"
            style="
              min-height: 150px;
              display: flex;
              flex-direction: column;
              justify-content: center;
            "
          >
            <b-field
              :label="`Are you sure you want to delete the collection ${targetCollectionActiveInfo.target_collection_name} ?`"
            >
              <b-radio
                v-model="deleteUnusedCompounds"
                :native-value="false"
                type="is-info"
              >
                Delete collection
              </b-radio>
            </b-field>
            <b-field>
              <b-radio
                v-model="deleteUnusedCompounds"
                :native-value="true"
                type="is-primary"
              >
                Delete collection and unused compounds
              </b-radio>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button
              type="is-dark"
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
                  deleteTargetCollection(
                    selectedCollection.target_collection_id
                  );
                  deactivateModal();
                }
              "
            >
              Remove
            </b-button>
          </footer>
        </div>
      </template>
    </b-modal>
  </section>
</template>

<script>
import { mapActions, mapMutations } from "vuex";
import { sync, call, get } from "vuex-pathify";

import BaseSpreadsheetInput from "./BaseSpreadsheetInput.vue";
import BaseTable from "./BaseTable.vue";

export default {
  name: "TheModalTargetCollectionOp",
  components: { BaseSpreadsheetInput, BaseTable },
  data: function () {
    return {
      // Edit Batch Collections
      initialTargetCollectionsChecked: [],
      targetCollectionsChecked: [],
      selectedBatchInfo: {},
      // Copy Selected Collection To Batches
      batchesToAddTo: [],
      newCollectionName: "",
      newCollectionDesc: "",
      newTargetCompounds: [],
      addToSampleBatch: true,
      // Delete Selected Collection
      targetCollectionActiveInfo: {},
      deleteUnusedCompounds: true,
      //
      initialSampleBatchesChecked: [],
      sampleBatchesChecked: [],
    };
  },
  computed: {
    ...sync({
      modalActive: "modal/targetCollectionOpActive",
      modalProps: "modal/targetCollectionOpProps",
    }),
    ...get({
      sampleBatches: "workspace/batches",
      sampleBatchesSelected: "workspace/sampleBatchesSelected",
      targetCollectionsSelected: "batch/targetCollectionsSelected",
      batchActive: "batch/active",
      targetCollectionActive: "targets/activeCollection",
      batchTargetCollections: "batch/targetCollections",
      targetCollectionsAll: "targets/targetCollectionsAll",
    }),
    fields() {
      return this.cols.map((col) => col.field);
    },
    action() {
      return this.modalProps.action;
    },
    selectedBatch() {
      return this.sampleBatchesSelected[0] ?? null;
    },
    selectedCollection() {
      return this.targetCollectionsSelected[0] ?? null;
    },
    targetCompoundCols() {
      return [
        { field: "target_compound_name", label: "Name" },
        { field: "target_compound_formula", label: "Formula" },
        { field: "cas_number", label: "CAS Number" },
      ];
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    async createTargetCollection(target_collection) {
      await this.$api.httpClient.createTargetCollection(target_collection);
    },
    async deleteTargetCollection(target_collection_id) {
      await this.$api.httpClient.deleteTargetCollection(
        target_collection_id,
        this.deleteUnusedCompounds
      );
    },
    async editBatchCollections(target_collections, sample_batch) {
      const removedCollections = this.initialTargetCollectionsChecked.filter(
        (initialCollection) =>
          !target_collections.some(
            (collection) =>
              collection.target_collection_id ===
              initialCollection.target_collection_id
          )
      );

      const addedCollections = target_collections
        .filter(
          (collection) =>
            !this.initialTargetCollectionsChecked.some(
              (initialCollection) =>
                initialCollection.target_collection_id ===
                collection.target_collection_id
            )
        )
        .map((collection) => ({
          target_collection_id: collection.target_collection_id,
          sample_batch_id: sample_batch.sample_batch_id,
        }));

      if (removedCollections.length === 0 && addedCollections.length === 0)
        return;

      if (removedCollections.length > 0) {
        const collectionsToRemove = removedCollections.map((collection) => ({
          target_collection_id: collection.target_collection_id,
          sample_batch_id: sample_batch.sample_batch_id,
        }));

        const skipRematch = addedCollections.length > 0;
        await this.$api.httpClient.removeTargetCollectionsFromSampleBatch(
          collectionsToRemove,
          skipRematch
        );
      }

      if (addedCollections.length > 0) {
        await this.$api.httpClient.addTargetCollectionToSampleBatch(
          addedCollections
        );
      }
    },
    async manageSelectedCollectionBatches(batches, target_collection) {
      const removedBatches = this.initialSampleBatchesChecked.filter(
        (initialBatch) =>
          !batches.some(
            (batch) => batch.sample_batch_id === initialBatch.sample_batch_id
          )
      );

      const addedBatches = batches
        .filter(
          (batch) =>
            !this.initialSampleBatchesChecked.some(
              (initialBatch) =>
                initialBatch.sample_batch_id === batch.sample_batch_id
            )
        )
        .map((batch) => ({
          sample_batch_id: batch.sample_batch_id,
          target_collection_id: target_collection.target_collection_id,
        }));

      if (removedBatches.length === 0 && addedBatches.length === 0) return;

      if (removedBatches.length > 0) {
        const batchesToRemove = removedBatches.map((batch) => ({
          sample_batch_id: batch.sample_batch_id,
          target_collection_id: target_collection.target_collection_id,
        }));

        const skipRematch = addedBatches.length > 0;
        await this.$api.httpClient.removeTargetCollectionsFromSampleBatch(
          batchesToRemove,
          skipRematch
        );
      }

      if (addedBatches.length > 0) {
        await this.$api.httpClient.addTargetCollectionToSampleBatch(
          addedBatches
        );
      }
    },

    initData() {
      if (this.selectedCollection) {
        this.newCollectionName = this.selectedCollection.target_collection_name;
        this.newCollectionDesc =
          this.selectedCollection.target_collection_description;
        this.targetCollectionActiveInfo = this.targetCollectionActive;
      }
      if (this.selectedBatch) {
        this.selectedBatchInfo = this.batchActive;
      }
      this.initTargetCollectionsChecked();
      this.initSampleBatchesChecked();
    },
    initTargetCollectionsChecked() {
      const ids = this.batchActive
        ? this.batchTargetCollections.map((row) => row.target_collection_id)
        : [];
      this.targetCollectionsChecked = this.targetCollectionsAll.filter((row) =>
        ids.includes(row.target_collection_id)
      );
      this.initialTargetCollectionsChecked = [...this.targetCollectionsChecked];
    },
    initSampleBatchesChecked() {
      const batchIdsForCurrentCollection = this.targetCollectionActive
        ? this.targetCollectionActive.sample_batches.map(
            (batch) => batch.sample_batch_id
          )
        : [];
      this.sampleBatchesChecked = this.sampleBatches.filter((batch) =>
        batchIdsForCurrentCollection.includes(batch.sample_batch_id)
      );
      this.initialSampleBatchesChecked = [...this.sampleBatchesChecked];
    },

    loadTargetCompounds(rows) {
      this.newTargetCompounds = rows;
    },
    selectBatchesToAddTo(newRows) {
      this.batchesToAddTo = newRows.map((row) => ({
        workspace_id: row.workspace_id,
        sample_batch_id: row.sample_batch_id,
      }));
    },
    updateTargetCollection(target_collection) {
      this.$api.emit("target_collection_update", target_collection);
    },
  },
};
</script>
