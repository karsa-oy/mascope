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
                :cols="[{ field: 'name', label: 'Batch' }]"
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
                      id: oldCollection.id,
                      name: newCollectionName,
                      description: newCollectionDesc,
                      sampleBatches: batchesToAddTo,
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
                Add to {{ sampleBatchSelected.name }}
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
                      name: newCollectionName,
                      description: newCollectionDesc,
                      targetCompounds: newTargetCompounds,
                      sampleBatches:
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
                      id: oldCollection.id,
                      name: newCollectionName,
                      description: newCollectionDesc,
                      targetCompounds: newTargetCompounds,
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
                deleteTargetCollection([oldCollection.id]);
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
      modalProps: "modal/targetCollectionOpProps",
    }),
    ...get({
      sampleBatches: "workspace/batches",
      modalActive: "modal/targetCollectionOpActive",
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
        { field: "name", label: "Name" },
        { field: "formula", label: "Formula" },
        { field: "casNumber", label: "CAS Number" },
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
    ...call({
      createTargetCollection: "target/collection/create",
      updateTargetCollection: "target/collection/update",
      deleteTargetCollection: "target/collection/delete",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    initData() {
      if (this.oldCollection) {
        this.newCollectionName = this.oldCollection.name;
        this.newCollectionDesc = this.oldCollection.description;
      }
    },
    loadTargetCompounds(rows) {
      this.newTargetCompounds = rows;
    },
    selectBatchesToAddTo(rows) {
      this.batchesToAddTo = rows.map((row) => row.id);
    },
  },
};
</script>