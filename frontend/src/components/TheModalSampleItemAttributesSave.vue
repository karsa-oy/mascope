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
      <div class="box" style="background-color: inherit">
        <b-steps v-model="activeStep" :has-navigation="false">
          <b-step-item
            label="Sample information"
            :clickable="true"
            :type="{ 'is-success': this.sampleActive ? true : false }"
          >
            <div style="text-align: right" v-if="editable">
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
            <div>
              <b-field label="Filter ID">
                <b-input v-model="sampleItemFilterId" disabled expanded>
                </b-input>
                <b-dropdown
                  aria-role="list"
                  v-model="sampleItemFilterId"
                  expanded
                >
                  <template #trigger>
                    <b-button
                      :label="sampleItemFilterId"
                      icon-right="menu-down"
                      style="align: left"
                    />
                  </template>
                  <template
                    v-for="filterId of batchFilterIds"
                    :key="filterId"
                  >
                    <b-dropdown-item
                      aria-role="listitem"
                      :value="filterId"
                    >
                      {{ filterId }}
                    </b-dropdown-item>
                  </template>
                </b-dropdown>
                <b-button
                  type="is-primary"
                  icon-left="plus"
                  @click="generateFilterId()"
                >
                </b-button>
              </b-field>
              <b-field label="Sample type">
                <b-dropdown aria-role="list" v-model="sampleItemType" expanded>
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
                    >Instrument background</b-dropdown-item
                  >
                  <b-dropdown-item
                    aria-role="listitem"
                    value="FILTER_REGENERATION"
                    v-if="sampleItemFilterId"
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
                    v-if="sampleItemFilterId"
                    >Sample</b-dropdown-item
                  >
                  <b-dropdown-item
                    aria-role="listitem"
                    value="BLANK"
                    v-if="sampleItemFilterId"
                    >Blank</b-dropdown-item
                  >
                  <b-dropdown-item
                    aria-role="listitem"
                    value="UNKNOWN"
                    v-if="sampleItemFilterId"
                    >Unknown</b-dropdown-item
                  >
                </b-dropdown>
              </b-field>
              <b-field label="Filename">
                <b-input
                  v-model="sampleFilename"
                  required
                  :disabled="true"
                  expanded
                >
                </b-input>
              </b-field>
            </div>
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
                    <div class="column is-one-half" style="text-align: right">
                      <b-button
                        :disabled="
                          !sampleItemType ||
                          formFields.filter((f) => f.required).length !=
                            formFields
                              .filter((f) => f.required)
                              .filter((f) => f.value).length ||
                          (action == 'create' && sampleActive)
                        "
                        type="is-success"
                        icon-left="content-save"
                        @click="saveSampleItem"
                      >
                        Save sample info
                      </b-button>
                    </div>
                  </div>
                </div>
              </div>
            </b-field>
          </b-step-item>

          <b-step-item
            label="Calibration"
            :visible="instrumentIsTof"
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
          </b-step-item>

          <b-step-item
            label="Target search"
            :clickable="
              this.sampleActive
                ? !this.instrumentIsTof || this.sampleMzCalibrated
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
                @click="deactivateModal"
                v-if="sampleMatched"
              >
                Close
              </b-button>
            </div>
          </b-step-item>
        </b-steps>
      </div>
    </b-modal>
  </section>
</template>

<script>
import BaseParamField from "./BaseParamField.vue";
import BaseTable from "./BaseTable.vue";
import ThePaneBrowserTarget from "./ThePaneBrowserTarget.vue";
import ThePaneSettingsCalibration from "./ThePaneSettingsCalibration.vue";

import * as _ from "underscore";
import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";
import { beautifySnakeCase, strToSnakeCase, genId } from "../lib/util";

export default {
  name: "TheModalSampleItemAttributesSave",
  components: {
    BaseParamField,
    BaseTable,
    ThePaneBrowserTarget,
    ThePaneSettingsCalibration,
  },
  props: {},
  data: function () {
    return {
      action: null,
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
      sampleFilename: null,
      sampleItemFilterId: null,
      sampleInstrument: null,
      sampleItemType: null,
      showEditFunctions: false,
      templateType: "sample_item",
    };
  },
  computed: {
    ...get({
      allTemplates: "app/attributeTemplates",
      batchActive: "batch/active",
      modalProps: "modal/sampleItemAttributesSaveProps",
      mzCalibrationParams: "calibration/params",
      mzFit: "calibration/mzFit",
      mzFitError: "calibration/mzFitError",
      mzFitStats: "calibration/mzFitStats",
      sampleActive: "sample/active",
      sampleItems: "batch/sampleItems",
      sampleMatched: "sample/matched",
      sampleMzCalibrated: "sample/active@mz_calibration.verified",
    }),
    ...sync({
      modalActive: "modal/sampleItemAttributesSaveActive",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.savedTemplates];
    },
    batchFilterIds() {
      return this.batchActive
        ? [null, ...new Set(this.sampleItems.map((item) => item.filter_id))]
        : [];
    },
    editable() {
      return ["create", "update"].includes(this.action);
    },
    fillable() {
      return ["create", "update"].includes(this.action);
    },
    instrumentIsTof() {
      return this.sampleInstrument
        ? this.sampleInstrument.indexOf("ORBI") == -1
        : false;
    },
    mzCalibrationTableRows() {
      return this.mzFitStats ?? [];
    },
    sampleItemAttributes() {
      return this.formFields
        .filter((field) => field.label != "sample_item_name")
        .reduce(
          (acc, cur) => ({
            ...acc,
            [strToSnakeCase(cur.label)]: cur.value || "",
          }),
          {}
        );
    },
    sampleItemName() {
      return this.formFields.filter(
        (field) => field.label == "sample_item_name"
      )[0].value;
    },
    savedTemplates() {
      return this.allTemplates.filter(
        (template) => template.type == this.templateType
      );
    },
  },
  created() {
    this.formFields = this.clone(this.defaultTemplate.template);
  },
  methods: {
    ...call({
      mzCalibrationReset: "calibration/unload",
      calibrationMzFit: "calibration/calibrationMzFit",
      calibrationMzApply: "calibration/calibrationMzApply",
      sampleItemCreate: "sample/create",
      sampleItemUpdate: "sample/update",
      matchSampleRematch: "sample/matchSampleRematch",
      createAttributeTemplate: "sample/createAttributeTemplate",
      deleteAttributeTemplate: "sample/deleteAttributeTemplate",
    }),
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    clone(obj) {
      return JSON.parse(JSON.stringify(obj));
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
          const templateToDelete = this.availableTemplates.find(
            (template) =>
              template.attribute_template_id ==
              this.loadedTemplate.attribute_template_id
          );
          this.deleteAttributeTemplate(templateToDelete);
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
    removeField(event) {
      // Field to remove label is in button element id, find it from the event data
      let targetElement = event.target;
      // Check if the clicked element is not the button itself, then find the closest parent button
      if (targetElement.nodeName !== "BUTTON") {
        targetElement = targetElement.closest("button");
      }
      let fieldToRemove = targetElement?.id || null;
      if (!fieldToRemove) {
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
    async sampleMatch() {
      await this.matchSampleRematch(this.sampleActive);
    },
    async saveSampleItem() {
      await this.saveAttributes();
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
          this.createAttributeTemplate(this.loadedTemplate);
        },
      });
    },
    async saveAttributes() {
      if (this.action == "create") {
        let newSampleItem = {
          filename: this.sampleFilename,
          sample_item_name: this.sampleItemName,
          sample_item_type: this.sampleItemType,
          sample_batch_id: this.batchActive.sample_batch_id,
          sample_item_attributes: this.sampleItemAttributes,
          filter_id: this.sampleItemFilterId,
        };
        await this.sampleItemCreate(newSampleItem);
      } else if (this.action == "update") {
        let newSampleItem = {
          ...this.sampleActive, // To include sample_item_id
          sample_item_name: this.sampleItemName,
          sample_item_type: this.sampleItemType,
          sample_batch_id: this.batchActive.sample_batch_id,
          sample_item_attributes: this.sampleItemAttributes,
          filter_id: this.sampleItemFilterId,
        };
        await this.sampleItemUpdate(newSampleItem);

        this.deactivateModal();
      }
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
    sampleItemFilterId(newValue) {
      if (newValue != this.sampleActive.filter_id) {
        // Reset sample item type when filter ID was changed
        this.sampleItemType = null;
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
    modalActive() {
      if (this.modalActive) {
        this.activeStep = 0;
      } else {
        // Reset template selection when closing modal
        this.loadedTemplate = null;
      }
    },
    modalProps: async function (data) {
      this.action = data.action;
      let newTemplate = {
        name: null,
        type: this.templateType,
        template: [],
      };
      for (let { label, key, required, disabled } of this.defaultTemplate
        .template) {
        if (required) {
          newTemplate.template.push({
            label,
            key,
            required,
            disabled,
            value: data.sampleItemRecordToLoad[label],
          });
        }
      }
      const attributesField = this.templateType + "_attributes";
      if (data.sampleItemRecordToLoad[attributesField]) {
        const attributes = data.sampleItemRecordToLoad[attributesField];
        if (
          attributes &&
          typeof attributes === "object" &&
          Object.keys(attributes).length > 0
        ) {
          Object.keys(attributes).forEach((attr) => {
            newTemplate.template.push({
              label: attr,
              value: attributes[attr],
            });
          });
        }
      }
      this.loadedTemplate = newTemplate;
      this.formFields = newTemplate.template;
      this.sampleFilename = data.sampleItemRecordToLoad.filename;
      this.sampleInstrument = data.sampleItemRecordToLoad.instrument;
      this.sampleItemFilterId = data.sampleItemRecordToLoad.filter_id;
      this.sampleItemType = data.sampleItemRecordToLoad.sample_item_type;
    },
  },
};
</script>
