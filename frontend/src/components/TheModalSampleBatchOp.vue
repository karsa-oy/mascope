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
                <b-switch v-model="calibrationShowAllCollections"
                  >Show All Collections</b-switch
                >
                <b-table
                  :data="
                    calibrationShowAllCollections
                      ? allCollections
                      : calibrantsCollections
                  "
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
                <b-switch v-model="targetsShowAllCollections"
                  >Show All Collections</b-switch
                >
                <b-table
                  :data="
                    targetsShowAllCollections
                      ? allCollections
                      : targetsCollections
                  "
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
                  deleteSampleBatch(batchActive);
                  deactivateModal();
                }
              "
            >
              Delete
            </b-button>
          </footer>
        </div>
      </template>
      <template v-if="actionIs('copy')">
        <div class="modal-card">
          <!-- style="background-color: inherit; height: 500px" -->
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body">
            <b-field label="New batch name">
              <b-input v-model="newBatchName"></b-input>
            </b-field>
            <b-field label="Description (optional)">
              <b-input v-model="newBatchDescription"></b-input>
            </b-field>

            <!-- Workspace Selection -->
            <b-field label="Select a workspace to copy the batch to:">
              <b-select v-model="workspaceSelected">
                <option :value="sameWorkspace" v-if="sameWorkspace">
                  Same workspace: {{ sameWorkspace.workspace_name }}
                </option>
                <option
                  v-for="workspace in filteredWorkspaces"
                  :key="workspace.workspace_id"
                  :value="workspace"
                >
                  {{ workspace.workspace_name }}
                </option>
              </b-select>
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
              type="is-primary"
              icon-left="content-save"
              expanded
              :loading="isCopying"
              :disabled="!newBatchName || !workspaceSelected || isCopying"
              @click="copySampleBatch"
            >
              {{ isCopying ? "Please Wait..." : "Copy Batch" }}
            </b-button>
          </footer>
        </div>
      </template>
    </b-modal>
  </section>
</template>

<script>
import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";
import { generateCopyName } from "../store/modules/apiHelper";

export default {
  name: "TheModalSampleBatchOp",
  data: function () {
    return {
      batchName: null,
      batchDesc: null,
      // populating collections
      calibrationShowAllCollections: false,
      targetsShowAllCollections: false,
      // selected data
      calibrationCollectionSelected: null,
      ionMechanismsSelected: [],
      targetCollectionsSelected: [],
      // copy action
      workspaceSelected: null,
      newBatchName: this.batchActive
        ? `${this.batchActive.sample_batch_name} Copy`
        : null,
      newBatchDescription: this.batchActive
        ? this.batchActive.sample_batch_description
        : null,
      isCopying: false,
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
      batchIonMechanismIds: "batch/paramIonMechanisms",
      batchTargetCollections: "batch/targetCollections",
      ionMechanismsAll: "app/ionMechanisms",
      allCollections: "targets/getAllCollections",
      calibrantsCollections: "targets/getCalibrantsCollections",
      targetsCollections: "targets/getTargetsCollections",
      workspaceActive: "workspace/active",
      allWorkspaces: "app/workspaces",
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
        case "copy":
          title = `Copy sample batch: ${this.batchName}`;
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
    sameWorkspace() {
      return this.workspaceActive ? this.workspaceActive : null;
    },
    filteredWorkspaces() {
      if (this.workspaceActive) {
        return this.allWorkspaces.filter((workspace) => {
          return workspace.workspace_id !== this.workspaceActive.workspace_id;
        });
      }
      return [];
    },
  },
  methods: {
    ...call({
      batchUnload: "batch/unload",
      createBatch: "batch/createBatch",
      updateBatch: "batch/updateBatch",
      deleteBatch: "batch/deleteBatch",
      copyBatch: "batch/copyBatch",
    }),
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    async deleteSampleBatch(batch) {
      this.batchUnload();
      await this.deleteBatch(batch);
    },
    async copySampleBatch() {
      this.isCopying = true;
      const batchCopyData = {
        // for http client
        sample_batch_id: this.batchActive.sample_batch_id,
        workspace_id: this.workspaceSelected.workspace_id,
        sample_batch_name: this.newBatchName,
        sample_batch_description: this.newBatchDescription,
        // for notification
        workspace_name: this.workspaceSelected.workspace_name,
      };
      await this.copyBatch(batchCopyData);
      this.isCopying = false;
      this.deactivateModal();
    },

    initCalibrationCollectionSelected() {
      if (this.batchCalibrationCollectionId) {
        [this.calibrationCollectionSelected] = this.allCollections.filter(
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
        this.calibrationCollectionSelected =
          this.allCollections.find(
            (collection) =>
              collection.target_collection_name === "Br calibrants"
          ) ||
          this.allCollections.find(
            (collection) =>
              collection.target_collection_id === "xkSPp3eZrWXYSVDa"
          );
        this.ionMechanismsSelected = this.ionMechanismsAll.filter(
          (mech) => mech.ionization_mechanism === "+Br-"
        );
        let explosivesTargets = this.allCollections.filter(
          (collection) =>
            collection.target_collection_name === "Explosives targets"
        );
        this.targetCollectionsSelected =
          explosivesTargets.length > 0
            ? explosivesTargets
            : this.allCollections.filter(
                (collection) =>
                  collection.target_collection_id === "kNBOCx32dpehRWUw"
              );
      } else if (this.action == "copy") {
        this.batchName = this.batchActive.sample_batch_name;
        // this.newBatchName = `${this.batchActive.sample_batch_name} Copy`;
        this.newBatchName = this.batchActive
          ? generateCopyName(this.batchActive.sample_batch_name)
          : null;
        this.newBatchDescription = this.batchActive.sample_batch_description;
        this.workspaceSelected = null;
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
      this.targetCollectionsSelected = this.allCollections.filter((row) =>
        ids.includes(row.target_collection_id)
      );
    },
  },
};
</script>
