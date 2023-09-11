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
      <template v-if="actionIs('create', 'update')">
        <div
          class="modal-card"
          style="background-color: inherit; height: 800px"
        >
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <b-tabs type="is-boxed">
              <b-tab-item label="Info">
                <b-field label="Name">
                  <b-input v-model="batchName"></b-input>
                </b-field>
                <b-field label="Description">
                  <b-input v-model="batchDesc"></b-input>
                </b-field>
              </b-tab-item>
              <b-tab-item label="Calibration" :disabled="action != 'create'">
                <b-table
                  :data="targetCollectionsAll"
                  :columns="[
                    { field: 'target_collection_name', label: 'Name' },
                    {
                      field: 'target_collection_description',
                      label: 'Description',
                    },
                  ]"
                  :selected.sync="calibrationCollectionSelected"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item label="Target collections">
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
                  :checked-rows.sync="targetCollectionsSelected"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item label="Ionization mechanisms">
                <b-table
                  :data="ionMechanismsAll"
                  :columns="[
                    { field: 'ionization_mechanism', label: 'Mechanism' },
                    {
                      field: 'ionization_mechanism_polarity',
                      label: 'Polarity',
                    },
                  ]"
                  checkable
                  :checked-rows.sync="ionMechanismsSelected"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item label="Settings">
                <the-pane-settings-batch></the-pane-settings-batch>
              </b-tab-item>
            </b-tabs>
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
              type="is-primary"
              icon-left="content-save"
              expanded
              :disabled="
                !batchName ||
                !targetCollectionsSelected ||
                !calibrationCollectionSelected ||
                !ionMechanismsSelected
              "
              @click="
                () => {
                  actionIs('create')
                    ? createBatch(newBatch)
                    : updateBatch(newBatch);
                  deactivateModal();
                }
              "
            >
              Save
            </b-button>
          </footer>
        </div>
      </template>
      <template v-if="actionIs('delete')">
        <div class="modal-card" style="width: 500px">
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <p>Are you sure you want to delete this sample batch?</p>
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
                  deleteBatch([batchActive.sample_batch_id]);
                  deactivateModal();
                }
              "
            >
              Delete
            </b-button>
          </footer>
        </div>
      </template>
    </b-modal>
  </section>
</template>

<script>
import ThePaneSettingsBatch from "./ThePaneSettingsBatch.vue";
import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";

export default {
  name: "TheModalSampleBatchOp",
  components: {
    ThePaneSettingsBatch,
  },
  data: function () {
    return {
      batchName: null,
      batchDesc: null,
      calibrationCollectionSelected: null,
      ionMechanismsSelected: [],
      targetCollectionsSelected: [],
    };
  },
  created() {},
  computed: {
    ...sync({
      modalActive: "modal/sampleBatchOpActive",
      modalProps: "modal/sampleBatchOpProps",
    }),
    ...get({
      batchActive: "batch/active",
      batches: "workspace/batches",
      batchCalibrationCollectionId: "batch/paramCalibrationCollection",
      batchFilterParams: "batch/filterParams",
      batchIonMechanismIds: "batch/paramIonMechanisms",
      batchTargetCollections: "batch/targetCollections",
      ionMechanismsAll: "app/ionMechanisms",
      targetCollectionsAll: "targets/targetCollectionsAll",
      workspaceActive: "workspace/active",
    }),
    action() {
      return this.modalProps.action;
    },
    newBatch() {
      if (this.actionIs("create")) {
        return {
          sample_batch_name: this.batchName,
          sample_batch_description: this.batchDesc,
          workspace_id: this.workspaceActive.workspace_id,
          build_params: {
            calibration_collection:
              this.calibrationCollectionSelected.target_collection_id,
            ion_mechanisms: this.ionMechanismIds,
          },
          filter_params: this.batchFilterParams,
          target_collection_id: this.targetCollectionIds,
        };
      } else if (this.actionIs("update")) {
        return {
          sample_batch_id: this.batchActive.sample_batch_id,
          sample_batch_name: this.batchName,
          sample_batch_description: this.batchDesc,
          workspace_id: this.workspaceActive.workspace_id,
          build_params: {
            calibration_collection:
              this.calibrationCollectionSelected.target_collection_id,
            ion_mechanisms: this.ionMechanismIds,
          },
          filter_params: this.batchFilterParams,
          target_collection_id: this.targetCollectionIds,
          sample_batch_utc_created: this.batchActive.sample_batch_utc_created,
        };
      } else {
        return null;
      }
    },
    modalTitle() {
      let title;
      switch (this.action) {
        case "create":
          title = `Create a new sample batch`;
          break;
        case "update":
          title = `Update sample batch ${this.batchName}`;
          break;
        case "delete":
          title = `Delete sample batch ${this.batchName}`;
          break;
      }
      return title;
    },
    ionMechanismIds() {
      return this.ionMechanismsSelected.map(
        (row) => row.ionization_mechanism_id
      );
    },
    targetCollectionIds() {
      return this.targetCollectionsSelected.map(
        (row) => row.target_collection_id
      );
    },
  },
  methods: {
    ...call({
      batchUnload: "batch/unload",
    }),
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    async createBatch(newBatch) {
      await this.$api.httpClient.createBatch(newBatch);
    },
    async deleteBatch(batches) {
      this.batchUnload();
      await this.$api.httpClient.deleteBatch(batches);
    },

    initCalibrationCollectionSelected() {
      if (this.batchCalibrationCollectionId) {
        [this.calibrationCollectionSelected] = this.targetCollectionsAll.filter(
          (collection) =>
            collection.target_collection_id == this.batchCalibrationCollectionId
        );
      } else {
        this.calibrationCollectionSelected = null;
      }
    },
    initData() {
      if (this.action == "create") {
        this.batchName = null;
        this.batchDesc = null;
        // set defaults
        [this.calibrationCollectionSelected] = this.targetCollectionsAll.filter(
          (collection) => collection.target_collection_id === "xkSPp3eZrWXYSVDa"
        );
        this.ionMechanismsSelected = this.ionMechanismsAll.filter(
          (mech) => mech.ionization_mechanism === "+Br-"
        );
        this.targetCollectionsSelected = this.targetCollectionsAll.filter(
          (collection) => collection.target_collection_id === "kNBOCx32dpehRWUw"
        );
      } else {
        this.batchName = this.batchActive.sample_batch_name;
        this.batchDesc = this.batchActive.sample_batch_description;
        this.initCalibrationCollectionSelected();
        this.initIonMechanismsSelected();
        this.initTargetCollectionsSelected();
      }
    },
    initIonMechanismsSelected() {
      const ids = this.batchIonMechanismIds;
      this.ionMechanismsSelected = this.ionMechanismsAll.filter((row) =>
        ids.includes(row.ionization_mechanism_id)
      );
    },
    initTargetCollectionsSelected() {
      const ids = this.batchActive
        ? this.batchTargetCollections.map((row) => row.target_collection_id)
        : [];
      this.targetCollectionsSelected = this.targetCollectionsAll.filter((row) =>
        ids.includes(row.target_collection_id)
      );
    },
    async updateBatch(newBatch) {
      await this.$api.httpClient.updateBatch(newBatch);
    },
  },
};
</script>
