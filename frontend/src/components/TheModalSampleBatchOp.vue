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
      <template v-if="actionIs('create', 'update', 'editBatchCollections')">
        <div
          class="modal-card"
          style="background-color: inherit; height: 800px"
        >
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <b-tabs
              v-model="activeTab"
              type="is-boxed"
              position="is-centered"
              expanded
            >
              <b-tab-item value="info" label="Info">
                <b-field label="Name">
                  <b-input
                    v-model="batchName"
                    :disabled="action == 'editBatchCollections'"
                    required
                  ></b-input>
                </b-field>
                <b-field label="Description">
                  <b-input
                    v-model="batchDesc"
                    :disabled="action == 'editBatchCollections'"
                  ></b-input>
                </b-field>
              </b-tab-item>
              <b-tab-item
                value="calibration"
                label="Calibration"
                :disabled="calibrationTabDisabled"
              >
                <b-field>
                  <b-select
                    v-model="selectedCalibrationCollectionType"
                    placeholder="Select a type"
                  >
                    <option value="targets">Targets collections</option>
                    <option value="calibrants">Calibrants collections</option>
                    <option value="diagnostics">Diagnostic collections</option>
                    <option value="all">All collections</option>
                  </b-select>
                </b-field>
                <b-table
                  :data="displayedCalibrationCollections"
                  :columns="collectionColumns"
                  :selected.sync="calibrationCollectionSelected"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item value="collections" label="Target collections">
                <b-field>
                  <b-select
                    v-model="selectedTargetCollectionType"
                    placeholder="Select a type"
                  >
                    <option value="targets">Targets collections</option>
                    <option value="calibrants">Calibrants collections</option>
                    <option value="diagnostics">Diagnostic collections</option>
                    <option value="all">All collections</option>
                  </b-select>
                </b-field>
                <b-table
                  :data="displayedTargetCollections"
                  :columns="collectionColumns"
                  checkable
                  :checked-rows.sync="targetCollectionsSelected"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item
                value="ionization"
                label="Ionization mechanisms"
                :disabled="action == 'editBatchCollections'"
              >
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
              :disabled="saveButtonActive"
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
import * as _ from "underscore";
import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";
import { generateCopyName } from "../store/modules/apiHelper";

export default {
  name: "TheModalSampleBatchOp",
  data: function () {
    return {
      //// Main batch data
      // Basic fields
      batchName: "",
      batchDesc: "",
      // Selected Associations data
      calibrationCollectionSelected: null,
      targetCollectionsSelected: [],
      ionMechanismsSelected: [],

      //// Utility data
      activeTab: null, // This will hold the value of the active tab
      isCopying: false,
      // Basic fields to track changes
      initialBatchName: "",
      initialBatchDesc: "",
      // Calibration tab
      selectedCalibrationCollectionType: "calibrants", // default calibrant selection
      initialCalibrationCollection: null, // This will be used to check if the user has changed the calibration collection
      // Target Collections tab
      selectedTargetCollectionType: "all", // default target selection
      initialTargetCollections: [], // To store initial target collections
      // Ionization tab
      initialIonizationMechanisms: [], // To store initial ion_mechanisms

      // copy action
      workspaceSelected: null,
      newBatchName: this.batchActive
        ? `${this.batchActive.sample_batch_name} Copy`
        : null,
      newBatchDescription: this.batchActive
        ? this.batchActive.sample_batch_description
        : null,
    };
  },
  computed: {
    ...sync({
      modalActive: "modal/sampleBatchOpActive",
      modalProps: "modal/sampleBatchOpProps",
    }),
    ...get({
      batchActive: "batch/batchActive",
      batchCalibrationCollectionId: "batch/paramCalibrationCollection",
      batchIonMechanismIds: "batch/paramIonMechanisms",
      batchTargetCollections: "batch/targetCollections",
      ionMechanismsAll: "app/ionMechanisms",
      allCollections: "targets/getAllCollections",
      targetsCollections: "targets/getTargetsCollections",
      calibrantsCollections: "targets/getCalibrantsCollections",
      diagnosticsCollections: "targets/getDiagnosticsCollections",
      workspaceActive: "workspace/active",
      allWorkspaces: "app/workspaces",
    }),
    //// General data ////
    action() {
      return this.modalProps.action;
    },
    collectionColumns() {
      return [
        { field: "target_collection_name", label: "Name" },
        { field: "target_collection_description", label: "Description" },
      ];
    },
    calibrationTabDisabled() {
      switch (this.action) {
        case "create":
          return false;
        case "update":
          // Compare initial and current calibration collection
          const initialCalibrationCollectionId = this
            .initialCalibrationCollection
            ? this.initialCalibrationCollection.target_collection_id
            : null;
          const currentCalibrationCollectionId = this
            .calibrationCollectionSelected
            ? this.calibrationCollectionSelected.target_collection_id
            : null;
          const calibrationCollectionChanged =
            initialCalibrationCollectionId !== currentCalibrationCollectionId;
          return !calibrationCollectionChanged;
        default:
          return true;
      }
    },

    saveButtonActive() {
      switch (this.action) {
        case "create":
          return (
            !this.batchName ||
            !this.calibrationCollectionSelected ||
            this.ionMechanismsSelected.length === 0
          );

        case "update":
          // Check if basic properties have changed
          const basicPropertiesChanged =
            (this.batchName !== this.initialBatchName ||
              this.batchDesc !== this.initialBatchDesc) &&
            this.batchName; // the name is required

          // Compare initial and current calibration collection
          const initialCalibrationCollectionId =
            this?.initialCalibrationCollection?.target_collection_id || null;
          const currentCalibrationCollectionId =
            this?.calibrationCollectionSelected?.target_collection_id || null;
          const calibrationCollectionChanged =
            initialCalibrationCollectionId !== currentCalibrationCollectionId;

          // Compare initial and current target collections
          const collectionsChanged = !_.isEqual(
            this.initialTargetCollections
              .map((collection) => collection.target_collection_id)
              .sort(),
            this.targetCollectionsSelected
              .map((collection) => collection.target_collection_id)
              .sort()
          );

          // Compare initial and current ion mechanisms
          const iomMechanismsChanged =
            !_.isEqual(
              this.initialIonizationMechanisms
                .map((mechanism) => mechanism)
                .sort(),
              this.ionMechanismsSelected.map((mechanism) => mechanism).sort()
            ) && this.ionMechanismsSelected.length > 0; // Check if there are any ion_mechanisms selected

          return (
            !basicPropertiesChanged &&
            !calibrationCollectionChanged &&
            !collectionsChanged &&
            !iomMechanismsChanged
          );

        case "editBatchCollections":
          // Compare initial and current target collections
          return !_.isEqual(
            this.initialTargetCollections
              .map((collection) => collection.target_collection_id)
              .sort(),
            this.targetCollectionsSelected
              .map((collection) => collection.target_collection_id)
              .sort()
          );

        default:
          return false;
      }
    },
    //// Labels and titles ////
    modalTitle() {
      let title;
      switch (this.action) {
        case "create":
          title = `Create a new sample batch`;
          break;
        case "update":
          title = `Update sample batch "${this.batchName}"`;
          break;
        case "editBatchCollections":
          title = `Edit collections of sample batch "${this.batchName}"`;
          break;
        case "delete":
          title = `Delete sample batch "${this.batchName}"`;
          break;
        case "copy":
          title = `Copy sample batch "${this.batchName}"`;
          break;
      }
      return title;
    },
    /// Calibration Tab ////
    displayedCalibrationCollections() {
      switch (this.selectedCalibrationCollectionType) {
        case "targets":
          return this.targetsCollections;
        case "calibrants":
          return this.calibrantsCollections;
        case "diagnostics":
          return this.diagnosticsCollections;
        case "all":
        default:
          return this.allCollections;
      }
    },
    /// Target Collections Tab ////
    displayedTargetCollections() {
      switch (this.selectedTargetCollectionType) {
        case "targets":
          return this.targetsCollections;
        case "calibrants":
          return this.calibrantsCollections;
        case "diagnostics":
          return this.diagnosticsCollections;
        case "all":
        default:
          return this.allCollections;
      }
    },

    /// Copy batch action ////
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
    //// data to form http request ////
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
          target_collection_ids: this.targetCollectionIds,
        };
      }
      if (this.actionIs("update") || this.actionIs("editBatchCollections")) {
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
          target_collection_ids: this.targetCollectionIds,
          sample_batch_utc_created: this.batchActive.sample_batch_utc_created,
        };
      }
    },
  },
  methods: {
    ...call({
      batchUnload: "batch/unload",
      createBatch: "batch/createBatch",
      updateBatch: "batch/updateBatch",
      deleteBatch: "batch/deleteBatch",
      copyBatch: "batch/copyBatch",
      showWarningNotification: "notification/showWarningNotification",
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

    //// Data loading ////
    // General data loading methods
    initData() {
      // Initialization logic when the modal is activated
      if (this.action == "create") {
        this.activeTab = "info";
        this.selectedTargetCollectionType = "targets";
        this.selectedCalibrationCollectionType = "calibrants";
        this.batchName = "";
        this.batchDesc = "";
        // TODO_configuration
        // set defaults
        let calibrantTargets = this.displayedCalibrationCollections.find(
          (collection) => collection.target_collection_name === "Br calibrants"
        );
        this.calibrationCollectionSelected = calibrantTargets
          ? calibrantTargets
          : this.allCollections.find(
              (collection) =>
                collection.target_collection_id === "xkSPp3eZrWXYSVDa"
            );
        let explosivesTargets = this.displayedTargetCollections.filter(
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
        this.ionMechanismsSelected = this.ionMechanismsAll.filter(
          (mech) => mech.ionization_mechanism === "+Br-"
        );
      }
      if (this.action == "update") {
        this.activeTab = "info";
        this.selectedTargetCollectionType = "targets";
        this.selectedCalibrationCollectionType = "calibrants";
        this.batchName = this.batchActive.sample_batch_name;
        this.batchDesc = this.batchActive.sample_batch_description;
        this.initialBatchName = this.batchName;
        this.initialBatchDesc = this.batchDesc;
        this.initCalibrationCollectionSelected();
        this.initTargetCollectionsSelected();
        this.initIonMechanismsSelected();
      }
      if (this.action == "delete") {
        this.batchName = this.batchActive.sample_batch_name;
      }
      if (this.action == "copy") {
        this.batchName = this.batchActive.sample_batch_name;
        this.newBatchName = this.batchActive
          ? generateCopyName(this.batchActive.sample_batch_name)
          : null;
        this.newBatchDescription = this.batchActive.sample_batch_description;
        this.workspaceSelected = null;
      }
      if (this.action == "editBatchCollections") {
        this.activeTab = "collections";
        this.selectedTargetCollectionType = "all";
        this.selectedCalibrationCollectionType = "calibrants";
        this.batchName = this.batchActive.sample_batch_name;
        this.batchDesc = this.batchActive.sample_batch_description;
        this.initCalibrationCollectionSelected();
        this.initTargetCollectionsSelected();
        this.initIonMechanismsSelected();
      }
    },
    initCalibrationCollectionSelected() {
      // set active batch calibration collection from build_params
      if (this.batchCalibrationCollectionId) {
        this.calibrationCollectionSelected = this.allCollections.find(
          (collection) =>
            collection.target_collection_id == this.batchCalibrationCollectionId
        );
      }
      this.initialCalibrationCollection = this.calibrationCollectionSelected;
      if (!this.calibrationCollectionSelected) {
        // set defaults if batch calibration collection is not set (debug)
        // TODO_configuration
        let calibrantTargets = this.displayedCalibrationCollections.find(
          (collection) => collection.target_collection_name === "Br calibrants"
        );
        this.calibrationCollectionSelected = calibrantTargets
          ? calibrantTargets
          : this.allCollections.find(
              (collection) =>
                collection.target_collection_id === "xkSPp3eZrWXYSVDa"
            );
        const data = {
          batchName: this.batchName,
          collectionName:
            this.calibrationCollectionSelected.target_collection_name,
        };
        // inform client about debug
        this.showWarningNotification({
          notification: "noCalibrationCollection",
          data: data,
        });
        this.activeTab = "calibration";
      }
    },
    initTargetCollectionsSelected() {
      const ids = this.batchActive
        ? this.batchTargetCollections.map((row) => row.target_collection_id)
        : [];
      this.targetCollectionsSelected = this.allCollections.filter((row) =>
        ids.includes(row.target_collection_id)
      );
      this.initialTargetCollections = this.targetCollectionsSelected;
    },
    initIonMechanismsSelected() {
      const ids = this.batchIonMechanismIds;
      this.ionMechanismsSelected = this.ionMechanismsAll.filter((row) =>
        ids.includes(row.ionization_mechanism_id)
      );
      this.initialIonizationMechanisms = this.ionMechanismsSelected;
    },
  },
};
</script>
