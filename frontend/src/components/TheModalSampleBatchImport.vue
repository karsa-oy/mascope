<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @close="deactivateModalResetData"
    >
      <div class="modal-card" style="height: 95vh; width: auto">
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
            <!-- Spreadsheet Input Tab -->
            <b-tab-item value="input" label="Data Input">
              <base-spreadsheet-input
                label="CSV"
                :cols="csvCols"
                :colsFromHeader="true"
                @colsPasted="processCsvCols"
                @rowsPasted="processCsvRows"
              >
              </base-spreadsheet-input>
              <!-- Filter ID input and dropdown -->
              <template v-if="showFilterIdInput">
                <b-field label="Please select the Filter ID">
                  <div
                    style="
                      display: flex;
                      justify-content: space-between;
                      align-items: center;
                    "
                  >
                    <div style="display: flex; align-items: center">
                      <b-button
                        type="is-primary"
                        icon-left="plus"
                        @click="generateFilterId"
                        style="margin-right: 10px"
                      >
                      </b-button>
                      <b-input
                        v-model="selectedFilterId"
                        disabled
                        expanded
                      ></b-input>
                      <b-dropdown
                        aria-role="list"
                        v-model="selectedFilterId"
                        expanded
                      >
                        <template #trigger>
                          <b-button
                            :label="selectedFilterId || 'Select Filter ID'"
                            icon-right="menu-down"
                          />
                        </template>
                        <template v-for="filterId in batchFilterIds">
                          <b-dropdown-item
                            aria-role="listitem"
                            :key="filterId"
                            :value="filterId"
                          >
                            {{ filterId }}
                          </b-dropdown-item>
                        </template>
                      </b-dropdown>
                    </div>
                    <b-button
                      type="is-primary"
                      @click="preprocessSamples"
                      :disabled="!selectedFilterId"
                    >
                      Continue
                    </b-button>
                  </div>
                </b-field>
              </template>
            </b-tab-item>

            <!-- Parsed Sample Items Tab -->
            <b-tab-item
              value="samples"
              label="Sample Items"
              :disabled="sampleItemsToCreate.length == 0"
            >
              <b-field
                :label="sampleItemsToCreateLabel"
                v-if="sampleItemsToCreate.length > 0"
              >
                <div class="table-with-pagination">
                  <div class="table-container">
                    <b-table
                      v-if="sampleItemsToCreate.length > 0"
                      :data="paginatedSampleItemsToCreate"
                      :columns="tableColumns"
                    ></b-table>
                  </div>
                  <div class="pagination-container">
                    <b-pagination
                      :total="sampleItemsToCreate.length"
                      :current.sync="samplesCurrentPage"
                      :per-page="samplesPerPage"
                      size="is-small"
                    ></b-pagination>
                  </div>
                </div>
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
            expanded
            type="is-primary"
            :disabled="!sampleItemsValidation"
            @click="processButtonClick"
          >
            Process ({{ sampleItemsToCreate.length }})
          </b-button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>

<script>
import { mapMutations } from "vuex";
import { sync, call, get } from "vuex-pathify";
import { parseAutosamplerCsv, parseGenericCsv, genId } from "../lib/util";

import BaseSpreadsheetInput from "./BaseSpreadsheetInput.vue";
import BaseTable from "./BaseTable.vue";

export default {
  name: "TheModalSampleBatchImport",
  components: {
    BaseSpreadsheetInput,
    BaseTable,
  },
  props: {},
  data: function () {
    return {
      csvCols: [],
      csvRows: [],
      parsedRows: [],
      sampleItemsToCreate: [], // Array of objects containing sample_item data
      // Pagination properties for sampleItemsToCreate
      samplesCurrentPage: 1,
      samplesPerPage: 12,
      activeTab: "input", // This will hold the value of the active tab
      importType: null, // property for import type
      columnsValidation: false, // the check theat pasted columns are valid
      sampleItemsValidation: false, // the check theat pasted sample items fields are valid
      // To store the details of validation failures
      failedValidations: {
        messages: [],
        sampleFailures: [],
        columnsFailures: [],
        info: [],
      },
      showFilterIdInput: false, // Controls visibility of filter ID input
      selectedFilterId: "", // Stores the selected filter ID
    };
  },
  computed: {
    ...get({
      batchActive: "batch/active",
      sampleItems: "batch/sampleItems",
      sampleBatchImportProps: "modal/sampleBatchImportProps",
      sampleTypes: "sample/sampleTypes",
    }),
    ...sync({
      modalActive: "modal/sampleBatchImportActive",
    }),
    //// Labels and titles ////
    modalTitle() {
      const batchName = this.batchActive?.sample_batch_name || "selected";
      // Define the modal title based on the importType
      switch (this.importType) {
        case "autosampler":
          return `Import samples from the autosampler report to "${batchName}" batch`;
        case "general":
          return `Import samples from the spreedsheet input to "${batchName}" batch`;
        default:
          return `Paste samples data to import to "${batchName}" batch`;
      }
    },
    sampleItemsToCreateLabel() {
      const batchName = this.batchActive?.sample_batch_name || "selected";
      switch (this.importType) {
        case "autosampler":
          return `Please check carefully the details of the samples parsed from the autosampler report:`;
        case "general":
          return `Please check carefully the details of the samples parsed from the spreedsheet input:`;
      }
    },
    // Data Input Tab
    batchFilterIds() {
      return this.batchActive
        ? [null, ...new Set(this.sampleItems.map((item) => item.filter_id))]
        : [];
    },
    // Sample Items Tab
    tableColumns() {
      if (this.sampleItemsToCreate.length === 0) {
        return [];
      }

      const mainColumns = [
        { field: "sample_item_name", label: "Sample Name" },
        { field: "filename", label: "Filename" },
        { field: "sample_item_type", label: "Sample Type" },
        { field: "filter_id", label: "Filter ID" },
      ];

      // Find all unique attribute keys from sample_item_attributes
      const attributeKeys = new Set();
      this.sampleItemsToCreate.forEach((item) => {
        Object.keys(item.sample_item_attributes).forEach((key) => {
          attributeKeys.add(key);
        });
      });

      // Create columns for each attribute key
      const attributeColumns = Array.from(attributeKeys).map((key) => ({
        field: `sample_item_attributes.${key}`,
        label: key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      }));

      return [...mainColumns, ...attributeColumns];
    },
    paginatedSampleItemsToCreate() {
      const start = (this.samplesCurrentPage - 1) * this.samplesPerPage;
      const end = start + this.samplesPerPage;
      return this.sampleItemsToCreate.slice(start, end);
    },
  },
  methods: {
    ...call({
      importSamplesToBatch: "batch/importSamplesToBatch",
      processSpreadsheetInput: "targets/processSpreadsheetInput",
      showWarningNotification: "notification/showWarningNotification",
      closeGeneralNotification: "notification/closeGeneralNotification",
    }),
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    deactivateModalResetData() {
      this.deactivateModal();
      this.resetData();
    },
    generateFilterId() {
      this.selectedFilterId = genId(6, false);
    },
    processButtonClick() {
      this.$buefy.dialog.confirm({
        message: `Are you sure you want to import ${
          this.sampleItemsToCreate.length
        } samples into the batch '${
          this.batchActive?.sample_batch_name || ""
        }'?`,
        confirmText: "Import",
        type: "is-primary",
        hasIcon: true,
        icon: "file-import",
        onConfirm: async () => {
          this.processSamples();
          this.deactivateModalResetData();
        },
      });
    },
    resetData() {
      this.csvCols = [];
      this.csvRows = [];
      this.parsedRows = [];
      this.sampleItemsToCreate = [];
      this.selectedFilterId = "";
      this.importType = null;
      this.showFilterIdInput = false;
      this.activeTab = "input";
      this.sampleItemsValidation = false;
      this.columnsValidation = false;
      this.closeGeneralNotification();
    },
    //// Data processing ////
    // csv loading columns
    async processCsvCols(cols) {
      this.resetData();
      if (!cols.length) return;
      this.csvCols = [];
      this.determineImportType(cols);
      this.validateColumns(cols);
      if (!this.columnsValidation) return;
      this.csvCols = cols;
    },
    // csv loading rows
    async processCsvRows(rows) {
      if (!rows.length) return;
      this.csvRows = [];
      if (!this.columnsValidation) return;
      this.csvRows = rows;
      this.parseCsv();
      if (!this.parsedRows) return;
      if (this.importType === "autosampler") {
        this.showFilterIdInput = true;
      } else {
        this.preprocessSamples();
      }
    },

    preprocessSamples() {
      this.prepareSampleItemsToCreate();
      this.activeTab = "samples";
      this.samplesCurrentPage = 1;
      this.validateImportedSampleItems();
    },

    processSamples() {
      if (!this.sampleItemsValidation) return;
      const data = {
        batch: this.batchActive,
        sample_items: this.sampleItemsToCreate,
      };
      this.importSamplesToBatch(data);
    },

    determineImportType(cols) {
      // List of keys that can identify the autosampler report
      const autosamplerKeys = [
        "ht3000a_autorun_report",
        "software",
        "sample_list",
        "autosampler",
      ];

      // Check if the field of any of the first few columns matches the autosampler keys
      const isAutosamplerReport = cols.some((col) =>
        autosamplerKeys.includes(col.field.toLowerCase())
      );

      this.importType = isAutosamplerReport ? "autosampler" : "general";
    },

    parseCsv() {
      if (this.importType === "autosampler") {
        this.parsedRows = parseAutosamplerCsv(this.csvRows);
      } else if (this.importType === "general") {
        this.parsedRows = parseGenericCsv(this.csvCols, this.csvRows);
      }
    },

    prepareSampleItemsToCreate() {
      if (this.importType === "autosampler") {
        let items = [];
        for (let [i, row] of Object.entries(this.parsedRows)) {
          let newSampleItem = {
            filename:
              this.sampleBatchImportProps.sampleFilesSelected[i]?.filename ||
              null,
            sample_batch_id: this.batchActive.sample_batch_id,
            filter_id: this.selectedFilterId,
          };
          let attributes = {};
          for (const key in row) {
            const attr = key.toLowerCase().replaceAll(/[\s-]/g, "_");
            if (attr.startsWith("sample_")) {
              // sample_name or sample_type
              const prop = attr.replace("sample", "sample_item");
              newSampleItem[prop] = row[key];
            } else {
              attributes[attr] = row[key];
            }
          }

          newSampleItem.sample_item_attributes = attributes;
          items.push(newSampleItem);
        }
        this.sampleItemsToCreate = items;
        this.showFilterIdInput = false;
        this.selectedFilterId = "";
      }
      // Process items for the general import
      if (this.importType === "general") {
        // Transform the parsed rows into sample items with necessary properties
        this.sampleItemsToCreate = this.parsedRows.map((row, index) => {
          const newSampleItem = {
            sample_batch_id: this.batchActive.sample_batch_id,
            filename:
              this.sampleBatchImportProps.sampleFilesSelected[index]
                ?.filename || null,
            ...row, // spread the already parsed row properties
          };
          return newSampleItem;
        });
      }
    },

    //// Data validation ////
    validateColumns(cols) {
      // Clear previous validation failures
      this.failedValidations.messages = [];
      this.failedValidations.sampleFailures = [];
      this.failedValidations.columnsFailures = [];
      this.failedValidations.info = [];

      // skip column validation for autosampler report import
      if (this.importType === "autosampler")
        return (this.columnsValidation = true);

      // Ensure all columns are labeled
      const unlabeledCols = cols.filter((col) => !col.label.trim());
      if (unlabeledCols.length > 0) {
        this.failedValidations.messages.push("All columns should be labeled.");
      }

      // Check for duplicated column names
      const columnNameCounts = {};
      cols.forEach((col) => {
        const label = col.label.trim();
        columnNameCounts[label] = (columnNameCounts[label] || 0) + 1;
      });

      for (const label in columnNameCounts) {
        if (columnNameCounts[label] > 1) {
          this.failedValidations.columnsFailures.push(
            `Column label "${label}" is duplicated, each column should have the unique label`
          );
        }
      }

      // Check for empty column labels and specific naming conventions
      if (!cols[0] || cols[0].label.trim() === "") {
        this.failedValidations.columnsFailures.push(
          "The first column should be labeled to indicate it contains sample names (e.g., 'Sample Name', 'Name')."
        );
      }
      if (cols.length > 1 && (!cols[1] || cols[1].label.trim() === "")) {
        this.failedValidations.columnsFailures.push(
          "The second column should be labeled to indicate it contains sample types (e.g., 'Sample Type', 'Type')."
        );
      }
      if (cols.length > 2 && (!cols[2] || cols[2].label.trim() === "")) {
        this.failedValidations.columnsFailures.push(
          "The third column should be labeled to indicate it contains filter IDs (e.g., 'Filter ID', 'Filter')."
        );
      }
      // Identify unlabeled sample item attribute columns and list their indices
      const unlabeledAttributeColsIndices = cols
        .slice(3)
        .map((col, index) => (!col.label.trim() ? index + 4 : null))
        .filter((index) => index !== null);

      if (unlabeledAttributeColsIndices.length === 1) {
        const columnIndex = unlabeledAttributeColsIndices[0];
        this.failedValidations.columnsFailures.push(
          `Column ${columnIndex} is unlabeled. Each column after the third must be labeled to indicate the name of the sample item attribute it contains.`
        );
      } else if (unlabeledAttributeColsIndices.length > 1) {
        const formattedIndices = unlabeledAttributeColsIndices.join(", ");
        this.failedValidations.columnsFailures.push(
          `Columns ${formattedIndices} should be labeled to indicate the name of the sample item attribute it contains.`
        );
      }

      // Show warning notification if there are any failed validations
      if (
        this.failedValidations.messages.length > 0 ||
        this.failedValidations.columnsFailures.length > 0
      ) {
        this.showWarningNotification({
          notification: "validationErrors",
          data: this.failedValidations,
        });
        this.columnsValidation = false; // Column validation failed
      } else {
        this.columnsValidation = true; // Column validation passed
      }
    },

    validateImportedSampleItems() {
      // TODO_configuration possible collection types
      const FILTER_ID_REGEX = /^[0-9A-Z]{6}$/; // The regex pattern for filter ID validation

      if (!this.sampleItemsToCreate.length > 0) return;
      // Clear previous validation failures
      this.failedValidations.messages = [];
      this.failedValidations.sampleFailures = [];
      this.failedValidations.columnsFailures = [];
      this.failedValidations.info = [];

      // Check for mismatch in the number of samples and files
      if (
        this.sampleItemsToCreate.length !==
        this.sampleBatchImportProps.sampleFilesSelected.length
      ) {
        this.failedValidations.messages.push(
          `The number of pasted samples (${this.sampleItemsToCreate.length}) doesn't line up with the total number of selected files (${this.sampleBatchImportProps.sampleFilesSelected.length}).
          Please ensure each pasted sample corresponds to a selected file.`
        );
      }

      // Iterate over each sample item to validate data
      for (const item of this.sampleItemsToCreate) {
        let itemFailures = []; // Store validation failures for the current item

        // Validate sample type
        if (!this.sampleTypes.includes(item.sample_item_type)) {
          itemFailures.push(
            `Sample type '${item.sample_item_type}' isn't recognized, please use one of the accepted types.`
          );

          // Add recommendation info if not already present
          const allowedTypesInfo = `Sample Types: please use one of the following: ${this.sampleTypes.join(
            ", "
          )}. You can leave this field empty, sample type will be set to UNKNOWN. `;
          if (!this.failedValidations.info.includes(allowedTypesInfo)) {
            this.failedValidations.info.push(allowedTypesInfo);
          }
        }

        // Validate filter ID presence based on sample type
        if (
          ["INSTRUMENT_BACKGROUND", "ONLINE"].includes(item.sample_item_type) &&
          item.filter_id
        ) {
          itemFailures.push(
            `Filter ID should not be provided for sample type '${item.sample_item_type}'.`
          );
        } else if (
          !["INSTRUMENT_BACKGROUND", "ONLINE"].includes(
            item.sample_item_type
          ) &&
          !item.filter_id
        ) {
          itemFailures.push(
            `Filter ID must be provided for sample type '${item.sample_item_type}'.`
          );
        }

        // Validate filter ID format if present
        if (item.filter_id && !FILTER_ID_REGEX.test(item.filter_id)) {
          itemFailures.push(
            `The filter ID '${item.filter_id}' is incorrectly formatted.`
          );

          // Add recommendation info if not already present
          const allowedFilterIdInfo = `Filter ID: ensure it is exactly 6 characters long and only contains uppercase letters and numbers.
          You can leave this field empty, filter ID will be generated automatically.`;
          if (!this.failedValidations.info.includes(allowedFilterIdInfo)) {
            this.failedValidations.info.push(allowedFilterIdInfo);
          }
        }

        // If there are failures, add them to the failedValidations array with the sample name
        if (itemFailures.length > 0) {
          this.failedValidations.sampleFailures.push({
            sampleName: item.sample_item_name,
            failures: itemFailures,
          });
        }
      }

      // Show warning notification if there are any failed validations
      if (
        this.failedValidations.messages.length > 0 ||
        this.failedValidations.sampleFailures.length > 0
      ) {
        this.showWarningNotification({
          notification: "validationErrors",
          data: this.failedValidations,
        });
        return (this.sampleItemsValidation = false);
      }

      return (this.sampleItemsValidation = true);
    },
  },
};
</script>
