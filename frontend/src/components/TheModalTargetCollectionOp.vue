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
      @close="deactivateModalResetData"
      :type="actionIs('delete') ? 'is-danger' : 'is-primary'"
    >
      <template v-if="actionIs('create', 'update', 'manageCollectionBatches')">
        <div class="modal-card" style="background-color: inherit; height: 90vh">
          <header class="modal-card-head">
            <p class="subtitle">{{ modalTitle }}</p>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <b-tabs
              v-model="activeTab"
              type="is-boxed"
              position="is-centered"
              expanded
            >
              <!-- Basic fields -->
              <b-tab-item value="info" label="Info">
                <b-field label="Name">
                  <b-input
                    v-model="collectionName"
                    placeholder="Enter a name for the target collection"
                    :disabled="action == 'manageCollectionBatches'"
                    required
                  ></b-input>
                </b-field>
                <b-field label="Description">
                  <b-input
                    v-model="collectionDesc"
                    placeholder="Enter a description for the target collection"
                    :disabled="action == 'manageCollectionBatches'"
                  ></b-input>
                </b-field>
                <b-field label="Collection type">
                  <b-dropdown
                    aria-role="list"
                    v-model="collectionType"
                    :disabled="action == 'manageCollectionBatches'"
                    expanded
                  >
                    <template #trigger>
                      <b-button
                        :label="collectionType || 'Select Type'"
                        icon-right="menu-down"
                        expanded
                        style="align: left"
                      />
                    </template>
                    <b-dropdown-item
                      aria-role="listitem"
                      v-for="collectionType in collectionTypes"
                      :key="collectionType"
                      :value="collectionType"
                    >
                      {{ collectionType }}
                    </b-dropdown-item>
                  </b-dropdown>
                </b-field>
              </b-tab-item>

              <!-- Target compounds associations -->
              <b-tab-item
                value="compounds"
                label="Target compounds"
                :disabled="action == 'manageCollectionBatches'"
              >
                <b-tabs type="is-toggle" v-model="compoundsTab" expanded>
                  <!-- Selected compounds tab -->
                  <b-tab-item
                    value="selectedCompounds"
                    label="Selected compounds"
                  >
                    <b-field :label="selectedCompoundsLabel"></b-field>
                    <b-field
                      v-if="initialCompounds.length > 0"
                      :label="`Current compounds of '${collectionName}'`"
                    >
                      <b-table
                        :data="paginatedInitialCompounds"
                        :columns="targetCompoundColumns"
                        checkable
                        :checked-rows.sync="targetCompounds"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="initialCompounds.length"
                            :current.sync="initialCompoundsCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                    <b-field
                      :label="addedCompoundsLabel"
                      v-if="addedCompounds.length > 0"
                    >
                      <b-table
                        :data="paginatedAddedCompounds"
                        :columns="targetCompoundColumns"
                        checkable
                        :checked-rows.sync="targetCompounds"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="addedCompounds.length"
                            :current.sync="addedCompoundsCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                    <b-field
                      :label="newCompoundsLabel"
                      v-if="targetCompoundsCreate.length > 0"
                    >
                      <b-table
                        :data="paginatedTargetCompoundsCreate"
                        :columns="targetCompoundColumns"
                        checkable
                        :checked-rows.sync="targetCompoundsCreate"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="targetCompoundsCreate.length"
                            :current.sync="targetCompoundsCreateCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                  </b-tab-item>
                  <!-- Add compounds tab -->
                  <b-tab-item value="addCompounds" label="Add compounds">
                    <!-- Source Selection -->
                    <b-field label="Add target compounds from">
                      <b-select
                        v-model="addCompoundsSource"
                        @input="loadAddCompoundsList"
                        placeholder="Select a source for adding compounds"
                        expanded
                      >
                        <optgroup label="Target Collections">
                          <option
                            v-for="collection in filteredCollections"
                            :key="collection.target_collection_id"
                            :value="collection"
                          >
                            {{ collection.target_collection_name }}
                          </option>
                        </optgroup>
                        <option value="all">All compounds</option>
                        <option value="spreadsheet">Spreadsheet</option>
                      </b-select>
                    </b-field>

                    <!-- Spreadsheet compounds input -->
                    <b-field v-if="addCompoundsSource === 'spreadsheet'">
                      <base-spreadsheet-input
                        :label="spreadsheetLabel"
                        :cols="targetCompoundColumns"
                        @rowsPasted="loadSpreadsheetCompounds"
                      ></base-spreadsheet-input>
                    </b-field>

                    <!-- Add Compounds Selection -->
                    <b-field
                      :label="addCompoundsListLabel"
                      v-if="addCompoundsList.length > 0"
                    >
                      <b-table
                        :data="paginatedAddCompoundsList"
                        :columns="targetCompoundColumns"
                        checkable
                        :checked-rows.sync="targetCompounds"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="addCompoundsList.length"
                            :current.sync="addCompoundsCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                    <b-field
                      :label="newCompoundsLabel"
                      v-if="targetCompoundsCreate.length > 0"
                    >
                      <b-table
                        :data="paginatedTargetCompoundsCreate"
                        :columns="targetCompoundColumns"
                        checkable
                        :checked-rows.sync="targetCompoundsCreate"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="targetCompoundsCreate.length"
                            :current.sync="targetCompoundsCreateCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                  </b-tab-item>
                </b-tabs>
              </b-tab-item>

              <!-- Sample batches associations -->
              <b-tab-item
                value="batches"
                label="Sample batches"
                :disabled="action == 'update'"
              >
                <!-- Source Selection -->
                <b-field label="Choose a workspace">
                  <b-select
                    v-model="workspaceSelected"
                    @input="loadWorkspaceBatches"
                    placeholder="Choose a workspace"
                    expanded
                  >
                    <option :value="currentWorkspace" v-if="currentWorkspace">
                      Current workspace: {{ currentWorkspace.workspace_name }}
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
                <!-- Workspace Batches Selection -->
                <b-field :label="workspaceBatchesSelectionLabel">
                  <b-table
                    :data="paginatedSelectedWorkspaceBatches"
                    :columns="[{ field: 'sample_batch_name', label: 'Batch' }]"
                    checkable
                    :checked-rows.sync="sampleBatches"
                    paginated
                  >
                    <!-- Optional: Pagination controls -->
                    <template v-slot:pagination>
                      <b-pagination
                        :total="selectedWorkspaceBatches.length"
                        :current.sync="selectBatchesCurrentPage"
                        :per-page="batchesPerPage"
                        size="is-small"
                      ></b-pagination>
                    </template>
                  </b-table>
                </b-field>
              </b-tab-item>
            </b-tabs>
          </section>
          <footer class="modal-card-foot">
            <b-button
              type="is-dark"
              icon-left="close"
              expanded
              @click="deactivateModalResetData"
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
                    ? createCollection(newCollection)
                    : updateCollection(newCollection);
                  deactivateModalResetData();
                }
              "
            >
              Save
            </b-button>
          </footer>
        </div>
      </template>
      <template v-else-if="actionIs('delete')">
        <div class="modal-card" style="height: 28vh">
          <header class="modal-card-head">
            <p class="subtitle">{{ modalTitle }}</p>
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
              :label="`Would you like to keep or remove compounds from '${collectionName}' that are not part of any other collection?`"
            >
            </b-field>
            <b-field>
              <b-radio
                v-model="deleteOrphanCompounds"
                :native-value="false"
                type="is-info"
              >
                Delete the collection and keep the unique compounds
              </b-radio>
            </b-field>
            <b-field>
              <b-radio
                v-model="deleteOrphanCompounds"
                :native-value="true"
                type="is-primary"
              >
                Delete the collection and its unique compounds
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
              @click="deleteButtonClick"
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
import * as _ from "underscore";
import { mapMutations } from "vuex";
import { sync, call, get } from "vuex-pathify";

import BaseSpreadsheetInput from "./BaseSpreadsheetInput.vue";
import BaseTable from "./BaseTable.vue";

export default {
  name: "TheModalTargetCollectionOp",
  components: { BaseSpreadsheetInput, BaseTable },
  data() {
    return {
      //// Main collection data
      // Basic fields
      collectionId: "",
      collectionName: "",
      collectionDesc: "",
      collectionType: null,
      // Associations data
      targetCompounds: [],
      sampleBatches: [],
      // Create data
      targetCompoundsCreate: [],

      //// Utility data
      activeTab: null, // This will hold the value of the active tab
      compoundsTab: null, // This will hold the value of the Target Compounds active subtab
      // Select compounds tab
      initialCompounds: [], // To store initial compounds from the active collection
      // Pagination properties
      initialCompoundsCurrentPage: 1,
      addedCompoundsCurrentPage: 1,
      targetCompoundsCreateCurrentPage: 1,
      // Add compounds tab
      addCompoundsSource: null,
      spreadsheetCompounds: [], // To store pasted to spreadsheet data
      addCompoundsList: [], // To store filtered list of available compounds (already existing in db)
      // Pagination properties for addCompoundsList
      addCompoundsCurrentPage: 1,
      compoundsPerPage: 15,

      // Sample Batches tab
      initialBatches: [], // To store initial batches of the active collection
      workspaceSelected: null,
      selectedWorkspaceBatches: [], // Loaded batches of the selected workspace
      // Pagination properties for selectedWorkspaceBatches
      selectBatchesCurrentPage: 1,
      batchesPerPage: 15,

      // Delete Modal
      deleteOrphanCompounds: true,
    };
  },
  computed: {
    ...sync({
      modalActive: "modal/targetCollectionOpActive",
      modalProps: "modal/targetCollectionOpProps",
    }),
    ...get({
      targetCollectionActive: "targets/activeCollection",
      collectionTypes: "targets/collectionTypes",
      allCollections: "targets/getAllCollections",
      allCompounds: "targets/getAllCompounds",
      allWorkspaces: "app/workspaces",
      activeWorkspace: "workspace/active",
      activeWorkspaceBatches: "workspace/batches",
    }),
    //// General data ////
    action() {
      return this.modalProps.action;
    },
    targetCompoundColumns() {
      // TODO_target_compound_management make fields editable
      return [
        { field: "target_compound_name", label: "Name" },
        { field: "target_compound_formula", label: "Formula" },
        { field: "cas_number", label: "CAS Number" },
      ];
    },
    saveButtonActive() {
      switch (this.action) {
        case "create":
          return (
            !this.collectionName ||
            !this.collectionType ||
            (this.targetCompounds.length === 0 &&
              this.targetCompoundsCreate.length === 0)
          );

        case "update":
          // Check if basic properties have changed
          const basicPropertiesChanged =
            this.collectionName !==
              this.targetCollectionActive.target_collection_name ||
            this.collectionDesc !==
              this.targetCollectionActive.target_collection_description ||
            this.collectionType !==
              this.targetCollectionActive.target_collection_type;

          // Compare initial and current compounds
          const compoundsChanged =
            !_.isEqual(
              this.initialCompounds
                .map((compound) => compound.target_compound_id)
                .sort(),
              this.targetCompounds
                .map((compound) => compound.target_compound_id)
                .sort()
            ) || this.targetCompoundsCreate.length > 0; // Check if there are new compounds to create;

          let disabled = !basicPropertiesChanged && !compoundsChanged;

          // Check if there are any compounds to assign or to create
          const hasCompounds =
            this.targetCompounds.length > 0 ||
            this.targetCompoundsCreate.length > 0;
          if (!hasCompounds) disabled = true;
          return disabled;
        case "manageCollectionBatches":
          return _.isEqual(
            this.initialBatches.map((batch) => batch.sample_batch_id).sort(),
            this.sampleBatches.map((batch) => batch.sample_batch_id).sort()
          );

        default:
          return false;
      }
    },

    //// Labels and titles ////
    //// modal
    modalTitle() {
      // Define the modal title based on the action
      let title = "";
      switch (this.action) {
        case "create":
          title = `Create a new target collection ${
            this?.collectionName || ""
          }`;
          break;
        case "update":
          title = `Update target collection "${this.collectionName}"`;
          break;
        case "manageCollectionBatches":
          title = `Manage batches of "${this.collectionName}" target collection`;
          break;
        case "delete":
          title = `Delete target collection "${this.collectionName}"`;
          break;
      }
      return title;
    },
    //// Target Compounds
    // Selected compounds tab
    selectedCompoundsLabel() {
      const name =
        this.collectionName === "" ? "new" : `"${this.collectionName}"`;
      if (
        !this.initialCompounds.length &&
        !this.addedCompounds.length &&
        !this.targetCompoundsCreate.length
      ) {
        return `Please add compounds to the ${name} collection.`;
      }
      return `Following checked compounds (uncheck to remove) will be present in the ${name} collection:`;
    },
    addedCompoundsLabel() {
      return `Added compounds:`;
    },

    // Add compounds tab
    addCompoundsListLabel() {
      if (this.addCompoundsSource.target_collection_id)
        return "Select compounds to add from the chosen collection:";
      if (this.addCompoundsSource === "all")
        return "Select compounds to add from all compounds:";
      if (this.addCompoundsSource === "spreadsheet")
        return "Select compounds to add from already existing compounds:";
      else return "Select compounds to add:";
    },
    spreadsheetLabel() {
      if (
        this.addCompoundsSource === "spreadsheet" &&
        this.spreadsheetCompounds.length
      )
        return "Pasted target compounds:";
      else return "Paste a list of target compounds:";
    },
    // both tabs
    newCompoundsLabel() {
      const name =
        this.collectionName === "" ? "new" : `"${this.collectionName}"`;
      return `Compounds to be created and added to the ${name} collection, please check the name and formula carefully:`;
    },
    //// Sample Batches Tab
    workspaceBatchesSelectionLabel() {
      const name =
        this.collectionName === "" ? "new" : `"${this.collectionName}"`;
      let title = "";
      switch (this.action) {
        case "create":
        case "manageCollectionBatches":
          title = `Select batches ${
            this.workspaceSelected
              ? `of the "${this?.workspaceSelected?.workspace_name}" workspace`
              : ""
          } where to add the ${name} collection`;
          break;
      }
      return title;
    },
    ////// tabs data //////
    //// Target Compounds Tab ////
    // data for Select compounds tab
    paginatedInitialCompounds() {
      const start =
        (this.initialCompoundsCurrentPage - 1) * this.compoundsPerPage;
      const end = start + this.compoundsPerPage;
      return this.initialCompounds.slice(start, end);
    },
    paginatedAddedCompounds() {
      const start =
        (this.addedCompoundsCurrentPage - 1) * this.compoundsPerPage;
      const end = start + this.compoundsPerPage;
      return this.addedCompounds.slice(start, end);
    },
    paginatedTargetCompoundsCreate() {
      const start =
        (this.targetCompoundsCreateCurrentPage - 1) * this.compoundsPerPage;
      const end = start + this.compoundsPerPage;
      return this.targetCompoundsCreate.slice(start, end);
    },
    // Computes the added compounds by filtering out those that are not in the initial compounds
    addedCompounds() {
      return this.targetCompounds.filter(
        (compound) =>
          !this.initialCompounds.some(
            (initialCompound) =>
              initialCompound.target_compound_id === compound.target_compound_id
          )
      );
    },

    // data for Add compounds tab
    filteredCollections() {
      if (this.action !== "create") {
        return this.allCollections.filter((collection) => {
          return (
            collection.target_collection_id !==
            this.targetCollectionActive.target_collection_id
          );
        });
      }
      return this.allCollections;
    },

    paginatedAddCompoundsList() {
      const start = (this.addCompoundsCurrentPage - 1) * this.compoundsPerPage;
      const end = start + this.compoundsPerPage;
      return this.addCompoundsList.slice(start, end);
    },

    /// Sample Batches Tab ////
    // Select workspaces
    currentWorkspace() {
      return this.activeWorkspace ? this.activeWorkspace : null;
    },
    filteredWorkspaces() {
      if (this.activeWorkspace) {
        return this.allWorkspaces.filter((workspace) => {
          return workspace.workspace_id !== this.activeWorkspace.workspace_id;
        });
      }
      return [];
    },
    paginatedSelectedWorkspaceBatches() {
      const start = (this.selectBatchesCurrentPage - 1) * this.batchesPerPage;
      const end = start + this.batchesPerPage;
      return this.selectedWorkspaceBatches.slice(start, end);
    },

    //// data to form http request ////
    targetCompoundsIds() {
      return this.targetCompounds.map(
        (compound) => compound.target_compound_id
      );
    },
    sampleBatchesIds() {
      return this.sampleBatches.map((batch) => batch.sample_batch_id);
    },
    newCollection() {
      if (this.actionIs("create")) {
        return {
          target_collection_name: this.collectionName,
          target_collection_description: this.collectionDesc,
          target_collection_type: this.collectionType,
          target_compound_ids: this.targetCompoundsIds,
          target_compounds_create: this.targetCompoundsCreate,
          sample_batch_ids: this.sampleBatchesIds,
        };
      }
      if (this.actionIs("update")) {
        return {
          target_collection_id:
            this.targetCollectionActive.target_collection_id,
          target_collection_name: this.collectionName,
          target_collection_description: this.collectionDesc,
          target_collection_type: this.collectionType,
          target_compound_ids: this.targetCompoundsIds,
          target_compounds_create: this.targetCompoundsCreate,
        };
      }
      if (this.actionIs("manageCollectionBatches")) {
        return {
          target_collection_id:
            this.targetCollectionActive.target_collection_id,
          target_collection_name: this.collectionName,
          target_collection_description: this.collectionDesc,
          target_collection_type: this.collectionType,
          sample_batch_ids: this.sampleBatchesIds,
        };
      }
    },
  },
  methods: {
    ...call({
      gethWorkspaceBatches: "workspace/gethWorkspaceBatches",
      getTargetCollection: "targets/getTargetCollection",
      getAllTargetCompounds: "targets/getAllTargetCompounds",
      createCollection: "targets/createCollection",
      updateCollection: "targets/updateCollection",
      deleteCollection: "targets/deleteCollection",
      processSpreadsheetInput: "targets/processSpreadsheetInput",
      showWarningNotification: "notification/showWarningNotification",
    }),
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    //// General methods ////
    actionIs(...actions) {
      return actions.includes(this.modalProps.action);
    },
    deactivateModalResetData() {
      this.deactivateModal();
      this.resetData();
    },
    deleteButtonClick() {
      this.$buefy.dialog.confirm({
        message: `Are you sure you want to delete '${this.collectionName}' target collection?`,
        confirmText: "Delete",
        type: "is-danger",
        hasIcon: true,
        icon: "delete-alert",
        onConfirm: async () => {
          const collectionId = this.collectionId;
          const collectionName = this.collectionName;
          const deleteOrphanCompounds = this.deleteOrphanCompounds;
          this.deleteCollection({
            collectionId,
            collectionName,
            deleteOrphanCompounds,
          });
          this.deactivateModalResetData();
        },
      });
    },
    //// Data loading ////
    // General data loading methods
    // Initialization logic when the modal is activated
    initData() {
      // Initializes data specific to the 'create' action
      if (this.action == "create") {
        this.activeTab = "info";
        this.compoundsTab = "addCompounds";
        this.collectionId = "";
        this.collectionName = "";
        this.collectionDesc = "";
        this.collectionType = null;
        this.targetCompounds = [];
        this.initialCompounds = this.targetCompounds;
        this.targetCompoundsCreate = [];
        this.spreadsheetCompounds = [];
        this.sampleBatches = [];
        this.initialBatches = this.sampleBatches;
        this.workspaceSelected = this?.currentWorkspace || null;
        if (this.activeWorkspaceBatches)
          this.reconcileBatches(this.activeWorkspaceBatches);
      }
      // Initializes data specific to the 'update' action
      if (this.actionIs("update")) {
        this.activeTab = "info";
        this.compoundsTab = "selectedCompounds";
        // Reset the selected compounds tab to the first page when the list is reloaded
        this.initialCompoundsCurrentPage = 1;
        this.collectionId =
          this?.targetCollectionActive?.target_collection_id || "";
        this.collectionName =
          this?.targetCollectionActive?.target_collection_name || "";
        this.collectionDesc =
          this?.targetCollectionActive?.target_collection_description || "";
        this.collectionType =
          this?.targetCollectionActive?.target_collection_type || null;
        this.targetCompounds =
          this?.targetCollectionActive?.target_compounds || [];
        this.initialCompounds = this.targetCompounds;
        this.targetCompoundsCreate = [];
        this.spreadsheetCompounds = [];
      }
      // Initializes data specific to the 'manageCollectionBatches' action
      if (this.action == "manageCollectionBatches") {
        this.activeTab = "batches";
        this.collectionId =
          this?.targetCollectionActive?.target_collection_id || "";
        this.collectionName =
          this?.targetCollectionActive?.target_collection_name || "";
        this.collectionDesc =
          this?.targetCollectionActive?.target_collection_description || "";
        this.collectionType =
          this?.targetCollectionActive?.target_collection_type || null;
        this.sampleBatches = this?.targetCollectionActive?.sample_batches || [];
        this.initialBatches = this.sampleBatches;
        this.workspaceSelected = this?.currentWorkspace || null;
        if (this.activeWorkspaceBatches)
          this.reconcileBatches(this.activeWorkspaceBatches);
      }
      // Initializes data specific to the 'delete' action
      if (this.action == "delete") {
        this.collectionId =
          this?.targetCollectionActive?.target_collection_id || "";
        this.collectionName =
          this?.targetCollectionActive?.target_collection_name || "";
        this.deleteOrphanCompounds = true;
      }
    },
    resetData() {
      this.modalProps = {};
      this.activeTab = "info";
      this.compoundsTab = "selectedCompounds";
      this.collectionId = "";
      this.collectionName = "";
      this.collectionDesc = "";
      this.collectionType = null;
      this.targetCompounds = [];
      this.targetCompoundsCreate = [];
      this.sampleBatches = [];
      this.addCompoundsSource = null;
      this.addCompoundsList = [];
      this.spreadsheetCompounds = [];
      this.workspaceSelected = null;
      this.selectedWorkspaceBatches = [];
      this.deleteOrphanCompounds = true;
      this.addedCompoundsCurrentPage = 1;
      this.targetCompoundsCreateCurrentPage = 1;
    },
    // Data loading methods for Add compounds tab
    async loadAddCompoundsList() {
      if (!this.addCompoundsSource) return;
      if (this.addCompoundsSource === "spreadsheet") {
        this.addCompoundsList = [];
        return;
      }
      // Reset add compounds list to the first page when the list is reloaded
      this.addCompoundsCurrentPage = 1;

      let compoundsToProcess = [];
      if (this.addCompoundsSource === "all") {
        compoundsToProcess = this.allCompounds;
      }
      if (this.addCompoundsSource.target_collection_id) {
        const collectionId = this.addCompoundsSource.target_collection_id;
        const collection = await this.getTargetCollection(collectionId);
        compoundsToProcess = collection?.target_compounds || [];
      }
      // check if the loaded collection has any compounds
      if (!compoundsToProcess.length) return;
      this.reconcileCompounds(compoundsToProcess);
    },

    // Reconcile compounds to maintain reference equality with compounds in targetCompounds and initialCompounds list.
    reconcileCompounds(compounds) {
      // Combine initialCompounds and targetCompounds to cover all compounds that are already part of the collection or selected
      const combinedCompounds = [
        ...this.initialCompounds,
        ...this.targetCompounds,
      ];

      // Use a Map to eliminate duplicate compounds based on a unique identifier (target_compound_id or formula)
      const compoundMap = new Map(
        combinedCompounds.map((compound) => [
          compound.target_compound_id || compound.target_compound_formula,
          compound,
        ])
      );

      this.addCompoundsList = compounds.map((compound) => {
        // First, try finding by target_compound_id, if not found by ID and there's no ID on the new compound, try finding by formula
        let selectedCompound = compoundMap.get(
          compound.target_compound_id || compound.target_compound_formula
        );

        // If found, use the existing compound from combinedCompounds if available; otherwise, use the current compound
        return selectedCompound || compound;
      });
    },

    // spreadsheet loading
    async loadSpreadsheetCompounds(rows) {
      if (this.addCompoundsSource !== "spreadsheet") return;
      // Reset add compounds list to the first page when the list is reloaded
      this.addCompoundsCurrentPage = 1;
      this.targetCompoundsCreateCurrentPage = 1;
      this.targetCompoundsCreate = [];
      this.spreadsheetCompounds = rows;
      const { existingCompounds, notExistingCompounds } =
        await this.processSpreadsheetInput(rows);

      // Reconcile existing compounds
      this.reconcileCompounds(existingCompounds);

      // Add notExistingCompounds to a list for creation
      this.targetCompoundsCreate.push(...notExistingCompounds);
    },

    // Data loading methods for Sample Batches tab
    reconcileBatches(batches) {
      this.selectedWorkspaceBatches = batches.map((batch) => {
        // Try to find an existing batch in sampleBatches
        const existingBatch = this.sampleBatches.find(
          (sb) => sb.sample_batch_id === batch.sample_batch_id
        );
        // If found, use the existing batch object to maintain reference equality; otherwise, use the current batch
        return existingBatch || batch;
      });
    },

    async loadWorkspaceBatches() {
      if (!this.workspaceSelected) return;

      // Reset to the first page when the list is reloaded
      this.selectBatchesCurrentPage = 1;

      const workspaceBatches = await this.gethWorkspaceBatches(
        this.workspaceSelected.workspace_id
      );
      if (!workspaceBatches.length) return;
      // Reconcile the loaded batches with those already present in sampleBatches
      this.reconcileBatches(workspaceBatches);
    },
  },
};
</script>

<style scoped>
optgroup {
  color: #464752 !important;
}
</style>
