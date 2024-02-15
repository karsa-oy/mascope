<template>
  <section>
    <the-layout-sidebar>
      <div style="margin: 0 auto; width: 50vw">
        <!-- Progress bars -->
        <section>
          <b-field label="Acquisition">
            <b-progress
              :value="acquisitionProgress"
              :type="acquisitionProgress == 100 ? 'is-success' : 'is-primary'"
            >
            </b-progress>
          </b-field>
          <b-field label="Conversion">
            <b-progress
              :value="conversionProgress"
              :type="conversionProgress == 100 ? 'is-success' : 'is-primary'"
            >
            </b-progress>
          </b-field>
          <b-field label="Calibration">
            <b-progress
              :value="calibrationProgress"
              :type="
                calibrationProgress == 100
                  ? calibrationStatus.failed
                    ? 'is-danger'
                    : 'is-success'
                  : 'is-primary'
              "
            >
            </b-progress>
          </b-field>
          <b-field label="Target search">
            <b-progress :value="matchingProgress" :type="sampleMatchClass">
            </b-progress>
          </b-field>
        </section>
        <br />
        <!-- Steps -->
        <b-steps v-model="activeStep" :has-navigation="false">
          <!-- Sample information step -->
          <b-step-item
            label="Sample information"
            :clickable="true"
            :type="{ 'is-success': this.sampleActive ? true : false }"
          >
            <div style="text-align: right" v-if="true">
              <b-button
                icon-right="cog"
                type="is-primary"
                size="is-small"
                @click="showEditFunctions = !showEditFunctions"
              >
              </b-button>
            </div>
            <div style="padding-bottom: 1.5em">
              <h1 class="title has-text-centered">Sample information</h1>
            </div>
            <div v-for="item in formFields" :key="item.label">
              <template>
                <b-field :label="convertLabelToTitle(item.label)">
                  <b-input
                    v-model="item.value"
                    :placeholder="
                      showEditFunctions
                        ? item.placeholder || 'default value'
                        : ''
                    "
                    :required="fillable && item.required"
                    :disabled="!fillable || item.disabled"
                    lazy
                    expanded
                  >
                  </b-input>
                  <div v-if="showEditFunctions">
                    <b-button
                      :id="item.label"
                      :disabled="item.required"
                      @click="removeField"
                      type="is-danger"
                      icon-right="delete"
                      hover
                      title="Delete Field"
                    >
                    </b-button>
                  </div>
                </b-field>
              </template>
            </div>
            <b-field label="Filter ID">
              <b-input v-model="sampleItemFilterId" disabled expanded>
              </b-input>
              <b-dropdown
                aria-role="list"
                v-model="sampleItemFilterId"
                :disabled="!acquisitionFilename"
                expanded
              >
                <template #trigger>
                  <b-button
                    :label="sampleItemFilterId"
                    icon-right="menu-down"
                    style="align: left"
                  />
                </template>
                <template v-for="filterId of batchFilterIds">
                  <b-dropdown-item
                    aria-role="listitem"
                    :key="filterId"
                    :value="filterId"
                  >
                    {{ filterId }}
                  </b-dropdown-item>
                </template>
              </b-dropdown>
              <b-button
                type="is-primary"
                icon-left="plus"
                :disabled="!acquisitionFilename"
                @click="generateFilterId()"
              >
              </b-button>
            </b-field>
            <b-field label="Sample type">
              <b-dropdown
                aria-role="list"
                v-model="sampleItemType"
                :disabled="!acquisitionFilename"
                expanded
              >
                <template #trigger>
                  <b-button
                    :label="sampleItemType"
                    icon-right="menu-down"
                    expanded
                    style="align: left"
                  />
                </template>
                <b-dropdown-item
                  aria-role="listitem"
                  value="INSTRUMENT_BACKGROUND"
                  v-if="!sampleItemFilterId"
                >
                  Instrument background
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="FILTER_REGENERATION"
                  v-if="sampleItemFilterId && filterIsNew"
                >
                  Filter regeneration
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="FILTER_BACKGROUND"
                  v-if="sampleItemFilterId"
                >
                  Filter background
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="SAMPLE"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Sample
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="BLANK"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Blank
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="UNKNOWN"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Unknown
                </b-dropdown-item>
              </b-dropdown>
            </b-field>
            <b-field label="Filename">
              <b-input
                v-model="acquisitionFilename"
                required
                :disabled="true"
                expanded
              >
              </b-input>
            </b-field>
            <b-field label="Sample batch">
              <b-tooltip
                :delay="200"
                position="is-top"
                type="is-dark"
                size="is-small"
                multilined
              >
                <b-dropdown
                  aria-role="list"
                  expanded
                  @change="selectBatch"
                  disabled
                >
                  <template #trigger>
                    <b-button
                      :label="batchActive ? batchActive.sample_batch_name : ''"
                      icon-right="menu-down"
                      expanded
                      style="align: left"
                    />
                  </template>
                  <template v-for="batch of batches">
                    <b-dropdown-item
                      aria-role="listitem"
                      :key="batch.sample_batch_id"
                      :value="batch"
                    >
                      {{ batch.sample_batch_name }}
                    </b-dropdown-item>
                  </template>
                </b-dropdown>
                <!-- tooltip slot -->
                <template v-slot:content>
                  <table style="text-align: center; width: 100%">
                    <tr>
                      <th>#</th>
                      <th>Sample name</th>
                    </tr>
                    <template v-for="item in sampleItems">
                      <tr v-bind:key="item.sample_item_id">
                        <td>{{ item.index }}</td>
                        <td>{{ item.sample_item_name }}</td>
                      </tr>
                    </template>
                  </table>
                </template>
              </b-tooltip>
            </b-field>
            <div v-if="showEditFunctions" style="padding-top: 2em">
              <b-field>
                <b-button @click="addField" expanded>
                  <b>Add new field</b>
                </b-button>
              </b-field>
            </div>
            <div><br /></div>
            <b-field label="Reuse template">
              <div class="container">
                <div class="row">
                  <div class="columns">
                    <div class="column is-half" style="text-align: center">
                      <b-select
                        v-model="loadedTemplate"
                        placeholder="Load template"
                        expanded
                      >
                        <option
                          v-for="t in availableTemplates"
                          :value="t"
                          :key="t.name"
                        >
                          {{ t.name }}
                        </option>
                      </b-select>
                    </div>
                    <div
                      class="column is-narrow"
                      style="text-align: left"
                      v-if="showEditFunctions"
                    >
                      <b-button
                        :disabled="
                          !loadedTemplate ||
                          !loadedTemplate.name ||
                          loadedTemplate.name == 'default'
                        "
                        @click="deleteTemplate"
                        type="is-danger"
                        icon-right="delete"
                        hover
                        title="Delete Template"
                      >
                      </b-button>
                    </div>
                    <div
                      class="column is-narrow"
                      style="text-align: left"
                      v-if="showEditFunctions"
                    >
                      <b-button
                        @click="saveTemplate"
                        :disabled="!formFields.length"
                        type="is-success"
                        icon-left="content-save"
                        hover
                        title="Save Template"
                      >
                      </b-button>
                    </div>
                  </div>
                </div>
              </div>
            </b-field>
            <div
              class="container"
              style="text-align: center; padding: 2em 0em 0em 0em"
            >
              <div class="rows">
                <div class="row">
                  <b-button
                    :disabled="
                      sampleIsSaved ||
                      !sampleItemName ||
                      !sampleItemType ||
                      !acquisitionFilename
                    "
                    :type="sampleIsSaved ? 'is-success' : 'is-danger'"
                    :loading="sampleItemPending === null ? false : true"
                    icon-left="content-save"
                    expanded
                    @click="saveSampleInfoButtonPressed"
                  >
                    Save sample info
                  </b-button>
                </div>
                <div class="row" style="padding: 1em">
                  <b-button
                    type="is-primary"
                    icon-left="close"
                    @click="closeButtonPressed()"
                    :disabled="
                      sampleActive
                        ? calibrationProgress != 100 || matchingProgress == null
                        : false
                    "
                    v-if="acquisitionFilename && conversionProgress == 100"
                  >
                    Close
                  </b-button>
                </div>
              </div>
            </div>
          </b-step-item>
          <!-- Calibration step -->
          <b-step-item
            label="Calibration"
            :clickable="this.sampleActive ? true : false"
            :type="{ 'is-success': this.sampleMzCalibrated }"
          >
            <h1 class="title has-text-centered">Calibration</h1>
            <b-collapse :open="false" animation="slide">
              <template #trigger>
                <section style="padding: 0.5em">
                  <b-button
                    icon-left="wrench"
                    size="is-small"
                    @click="
                      (props) => {
                        props.open = !props.open;
                      }
                    "
                  >
                  </b-button>
                </section>
              </template>
              <the-pane-settings-calibration></the-pane-settings-calibration>
            </b-collapse>
            <b-message v-if="mzFitError" type="is-danger" has-icon>
              {{ mzFitError }}
            </b-message>
            <base-table
              :key="mzCalibrationTableKey"
              :rows="mzCalibrationTableRows"
              :cols="mzCalibrationTableCols"
              :checkable="false"
              :defaultSort="['mz', 'asc']"
              :searchable="false"
              :minPrecision="4"
              :maxPrecision="4"
            >
            </base-table>
            <div style="text-align: right">
              <b-button
                :disabled="this.sampleActive ? false : true"
                type="is-primary"
                icon-left=""
                @click="mzCalibrationFit"
              >
                Fit
              </b-button>
              <b-button
                :disabled="this.mzFit ? false : true"
                type="is-success"
                icon-left="content-save"
                @click="mzCalibrationApply"
              >
                Apply calibration
              </b-button>
            </div>
            <div style="text-align: center">
              <b-button
                type="is-primary"
                icon-left="close"
                @click="closeButtonPressed()"
                v-if="mzFitError"
              >
                Close
              </b-button>
            </div>
          </b-step-item>
          <!-- Target search step -->
          <b-step-item
            label="Target search"
            :clickable="
              this.sampleActive
                ? this.sampleMzCalibrated
                  ? true
                  : false
                : false
            "
            :type="{ 'is-success': this.sampleMatched }"
          >
            <h1 class="title has-text-centered">Target search</h1>
            <div v-if="this.sampleMatched">
              <the-pane-browser-target></the-pane-browser-target>
            </div>
            <div style="text-align: center">
              <b-button
                :disabled="this.sampleActive ? false : true"
                type="is-success"
                icon-left=""
                @click="sampleMatch"
                v-if="!sampleMatched"
              >
                Process
              </b-button>
              <b-button
                type="is-primary"
                icon-left="close"
                @click="closeButtonPressed()"
                v-if="sampleMatched"
              >
                Close
              </b-button>
            </div>
          </b-step-item>
        </b-steps>
      </div>
    </the-layout-sidebar>
  </section>
</template>

<script>
import BaseParamField from "./BaseParamField.vue";
import BaseTable from "./BaseTable.vue";
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import ThePaneBrowserTarget from "./ThePaneBrowserTarget.vue";
import ThePaneSettingsCalibration from "./ThePaneSettingsCalibration.vue";

import * as _ from "underscore";
import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";
import { beautifySnakeCase, camelToSnakeCase, genId } from "../lib/util";

export default {
  name: "TheModalScenthoundWorkflow",
  components: {
    BaseParamField,
    BaseTable,
    TheLayoutSidebar,
    ThePaneBrowserTarget,
    ThePaneSettingsCalibration,
  },
  props: {},
  data: function () {
    return {
      activeStep: 0,
      defaultTemplate: {
        name: "default",
        template: [
          {
            label: "sample_item_name",
            required: true,
            placeholder: "Sample title",
          },
        ],
      },
      formFields: [],
      loadedTemplate: null,
      mzCalibrationTableCols: [
        { field: "mz", label: "Isotope m/z" },
        { field: "sample_peak_mz", label: "Pre peak m/z" },
        {
          field: "match_mz_error",
          label: "Pre m/z error [ppm]",
          subheading: null,
        },
        { field: "calibration_mz", label: "Post peak m/z" },
        {
          field: "calibration_mz_error",
          label: "Post m/z error [ppm]",
          subheading: null,
        },
        { field: "mz_error_diff", label: "m/z error diff", subheading: null },
        {
          field: "calibrant_to_tic",
          label: "fraction of TIC",
          subheading: null,
        },
      ],
      mzCalibrationTableKey: 0,
      sampleItemFilterId: null,
      sampleItemType: null,
      showEditFunctions: false,
      templateType: "sample_item",
    };
  },
  computed: {
    ...get({
      acquisitionFilename: "instrument/acquisitionActiveFilename",
      acquisitionProgress: "instrument/acquisitionProgress",
      allTemplates: "app/attributeTemplates",
      batchActive: "batch/active",
      batches: "workspace/batches",
      calibrationStatus: "calibration/calibrationStatus",
      conversionProgress: "instrument/conversionProgress",
      instrumentActive: "instrument/active",
      matchingProgress: "instrument/matchingProgress",
      mzCalibrationParams: "calibration/params",
      mzFit: "calibration/mzFit",
      mzFitError: "calibration/mzFitError",
      mzFitStats: "calibration/mzFitStats",
      sampleActive: "sample/active",
      sampleAlarmCategory: "sample/alarmCategory",
      sampleItems: "batch/sampleItems",
      sampleMatched: "sample/matched",
      sampleMatchCompounds: "sample/matchCompounds",
      sampleMzCalibrated: "sample/active@mz_calibration.verified",
    }),
    ...sync({
      sampleItemPending: "instrument/sampleItemPending",
      scenthoundModeActive: "instrument/scenthoundModeActive",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.savedTemplates];
    },
    editable() {
      return true;
    },
    fillable() {
      return this.acquisitionFilename;
    },
    batchFilterIds() {
      return this.batchActive
        ? [null, ...new Set(this.sampleItems.map((item) => item.filter_id))]
        : [];
    },
    calibrationProgress() {
      return this.calibrationStatus ? this.calibrationStatus.progress : 0;
    },
    filterIsNew() {
      return !this.batchFilterIds.includes(this.sampleItemFilterId);
    },
    mzCalibrationTableRows() {
      return this.mzFitStats ?? [];
    },
    sampleFilename() {
      return this.sampleActive
        ? this.sampleActive.filename
        : this.acquisitionFilename;
    },
    sampleIsSaved() {
      return this.sampleActive
        ? this.sampleItemName === this.sampleActive.sample_item_name &&
            this.sampleItemType === this.sampleActive.sample_item_type &&
            this.sampleItemFilterId === this.sampleActive.filter_id
        : false;
    },
    sampleItemAttributes() {
      return this.formFields
        .filter((field) => field.label != "sample_item_name")
        .reduce((acc, cur) => ({ ...acc, [cur.label]: cur.value }), {});
    },
    sampleItemName() {
      return this.formFields.filter(
        (field) => field.label == "sample_item_name"
      )[0].value;
    },
    sampleMatchClass() {
      if (this.sampleAlarmCategory === null) return "is-primary";
      if (this.sampleAlarmCategory === 2) {
        return "is-danger";
      } else if (this.sampleAlarmCategory === 1) {
        return "is-primary";
      } else {
        return "is-success";
      }
    },
    savedTemplates() {
      return this.allTemplates.filter(
        (template) => template.type == this.templateType
      );
    },
  },
  created() {
    this.sampleUnload();
    this.scenthoundModeActive = true;
    this.formFields = [...this.defaultTemplate.template];
  },
  beforeRouteLeave(to, from, next) {
    this.scenthoundModeActive = false;
    next();
  },
  methods: {
    ...call({
      batchSelect: "batch/load",
      mzCalibrationReset: "calibration/unload",
      calibrationMzFit: "calibration/calibrationMzFit",
      calibrationMzApply: "calibration/calibrationMzApply",
      resetAcquisitionStatus: "instrument/resetAcquisitionStatus",
      sampleItemCreate: "sample/create",
      sampleItemUpdate: "sample/update",
      sampleUnload: "sample/unload",
      matchSampleCompute: "sample/matchSampleCompute",
    }),
    ...mapMutations({}),
    clone(obj) {
      return JSON.parse(JSON.stringify(obj));
    },
    closeButtonPressed() {
      if (this.sampleActive && this.sampleIsSaved) {
        this.reset();
      } else {
        this.$buefy.dialog.confirm({
          title: "Close sample without saving?",
          message: `There is unsaved information in the form.
            Are you sure you want to close the sample without saving?`,
          confirmText: "Close",
          onConfirm: () => {
            this.reset();
          },
        });
      }
    },
    convertLabelToTitle(label) {
      return beautifySnakeCase(label);
    },
    addField() {
      this.$buefy.dialog.prompt({
        message: "Add field to template",
        confirmText: "Add",
        inputAttrs: {
          placeholder: "field label",
          maxlength: 100,
        },
        trapFocus: true,
        onConfirm: (fieldToAdd) => {
          this.loadedTemplate = {
            name: null,
            template: [...this.formFields, { label: fieldToAdd, value: "" }],
          };
        },
      });
    },
    deleteTemplate() {
      this.$buefy.dialog.confirm({
        title: "Deleting template",
        message:
          "Are you sure you want to delete template <b>" +
          this.loadedTemplate.name +
          "</b>?",
        confirmText: "Delete",
        onConfirm: () => {
          this.$api.emit(
            "attribute_template_delete",
            this.availableTemplates
              .filter(
                (template) =>
                  template.attribute_template_id ==
                  this.loadedTemplate.attribute_template_id
              )
              .map((template) => template.attribute_template_id)
          );
        },
      });
    },
    removeField(event) {
      // Field to remove label is in button element id, find it from the event data
      let fieldToRemove = event.target.id;
      if (!fieldToRemove.length) {
        // Failed to find the button id
        console.log("fieldToRemove not found at event.target.id: ", event);
        return;
      }
      for (let i = 0; i < this.loadedTemplate.template.length; ++i) {
        if (_.isEqual(fieldToRemove, this.loadedTemplate.template[i].label)) {
          this.loadedTemplate = {
            name: null,
            template: [
              ...this.loadedTemplate.template.slice(0, i),
              ...this.loadedTemplate.template.slice(i + 1),
            ],
          };
          break;
        }
      }
    },
    saveTemplate() {
      this.$buefy.dialog.prompt({
        title: "Template name",
        confirmText: "Save",
        inputAttrs: {
          placeholder: "template name",
          maxlength: 100,
        },
        trapFocus: true,
        onConfirm: (templateName) => {
          if (templateName.toLowerCase() === "default") {
            this.$buefy.toast.open({
              message: `Name "${templateName}" is not allowed`,
              duration: 5000,
              type: "is-danger",
            });
            return;
          }
          let templateFormFields = this.clone(this.formFields);
          // Empty values
          templateFormFields.forEach((field) => (field.value = ""));
          let newTemplate = {
            name: templateName,
            type: this.templateType,
            template: templateFormFields,
          };
          let i = 0;
          // set loaded template
          for (i = 0; i < this.availableTemplates.length; ++i) {
            if (_.isEqual(templateName, this.availableTemplates[i].name)) break;
          }
          if (i < this.availableTemplates.length) {
            // existing template
            this.availableTemplates[i] = this.clone(newTemplate);
          } else {
            // new template
            this.availableTemplates.push(this.clone(newTemplate));
          }
          this.loadedTemplate = this.clone(newTemplate);
          // push new template
          this.$api.emit("attribute_template_create", [this.loadedTemplate]);
        },
      });
    },
    generateFilterId() {
      this.sampleItemFilterId = genId(6, false);
    },
    async mzCalibrationFit() {
      this.mzCalibrationReset();
      const requestData = {
        sampleId: this.sampleActive.sample_item_id,
        sampleName: this.sampleActive.sample_item_name,
        body: this.mzCalibrationParams,
      };
      await this.calibrationMzFit(requestData);
    },
    async mzCalibrationApply() {
      const requestData = {
        fit: this.mzFit,
        sample_filename: this.sampleFilename,
      };
      await this.calibrationMzApply(requestData);
    },
    reset() {
      this.resetAcquisitionStatus();
      this.resetSampleItem();
      this.activeStep = 0;
    },
    resetSampleItem() {
      this.sampleUnload();
      this.sampleItemFilterId = null;
      this.sampleItemType = null;
      // Reset sample item name
      this.formFields.filter(
        (field) => field.label == "sample_item_name"
      )[0].value = null;
    },
    async sampleMatch() {
      await this.matchSampleCompute(this.sampleActive);
    },
    saveSampleInfoButtonPressed() {
      let sample = {
        filename: this.sampleFilename,
        sample_item_name: this.sampleItemName,
        sample_item_type: this.sampleItemType,
        sample_batch_id: this.batchActive.sample_batch_id,
        sample_item_attributes: this.sampleItemAttributes,
        filter_id: this.sampleItemFilterId,
      };
      if (this.conversionProgress < 100) {
        this.sampleItemPending = sample;
        return;
      } else {
        this.saveSampleInformation(sample);
      }
    },
    async saveSampleInformation(sample) {
      if (!this.sampleActive) {
        // Create
        await this.sampleItemCreate(sample);
      } else {
        // Update
        sample = {
          ...sample,
          sample_item_id: this.sampleActive.sample_item_id,
          sample_item_attributes: this.sampleActive.sample_item_attributes,
          sample_item_utc_created: this.sampleActive.sample_item_utc_created,
        };
        await this.sampleItemUpdate(sample);
      }
    },
    selectBatch(val) {
      this.batchSelect(val.sample_batch_id);
    },
  },
  watch: {
    activeStep() {
      switch (this.activeStep) {
        case 0:
          break;
        case 1:
          break;
        case 2:
          break;
      }
    },
    acquisitionProgress(newValue, oldValue) {
      if (newValue == 0) {
        this.resetSampleItem();
        this.activeStep = 0;
      }
    },
    calibrationProgress(newValue, oldValue) {
      if (oldValue != 100 && newValue == 100) {
        if (this.calibrationStatus.failed) {
          this.activeStep = 1;
        }
      }
    },
    loadedTemplate: {
      handler(newValue) {
        if (newValue) {
          // Make a copy to avoid mutating the loaded template directly
          let newFormFields = this.clone(newValue.template);
          // Fill in new form with values from the old
          newFormFields.forEach(
            (field) =>
              (field.value = this.formFields.find(
                (old_field) => old_field.label === field.label
              )?.value)
          );
          this.formFields = newFormFields;
        }
      },
      deep: true,
    },
    sampleMaxMatchCategory(newValue, oldValue) {
      if (this.sampleMaxMatchCategory > 0) {
        this.activeStep = 2;
      }
    },
  },
};
</script>
