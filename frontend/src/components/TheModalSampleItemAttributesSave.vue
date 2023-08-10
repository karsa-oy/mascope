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
                <b-field :label="item.label.replaceAll('_', ' ')">
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
                  <b-dropdown-item aria-role="listitem" value="BACKGROUND"
                    >Background</b-dropdown-item
                  >
                  <b-dropdown-item aria-role="listitem" value="HOT"
                    >Hot</b-dropdown-item
                  >
                  <b-dropdown-item aria-role="listitem" value="BLANK"
                    >Blank</b-dropdown-item
                  >
                  <b-dropdown-item aria-role="listitem" value="UNKNOWN"
                    >Unknown</b-dropdown-item
                  >
                </b-dropdown>
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
import { genId } from "../lib/util";

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
          {
            label: "filename",
            required: true,
            placeholder: "",
            disabled: true,
          },
        ],
      },
      formFields: [],
      loadedTemplate: null,
      // TEMP
      loadingInstance: null,
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
    savedTemplates() {
      return this.allTemplates.filter(
        (template) => template.type == this.templateType
      );
    },
  },
  created() {
    this.loadedTemplate = this.clone(this.availableTemplates[0]);
    // TEMP
    this.$api.socket.on(
      "match_item_compute_finished",
      this.onMatchItemComputeFinished
    );
    this.$api.socket.on(
      "match_item_compute_failed",
      this.onMatchItemComputeFailed
    );
  },
  methods: {
    ...call({
      mzCalibrationReset: "calibration/unload",
    }),
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    clone(obj) {
      return JSON.parse(JSON.stringify(obj));
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
    generateFilterId() {
      this.sampleItemFilterId = genId(6, false);
    },
    async mzCalibrationApply() {
      await this.$api.httpClient.mzCalibrationApply(
        {
          fit: this.mzFit,
          sample_filenames: [this.sampleFilename],
        },
        true
      );
    },

    mzCalibrationFit() {
      this.mzCalibrationReset();
      this.$api.emit(
        "calibration_mz_fit",
        this.sampleActive.sample_item_id,
        this.mzCalibrationParams
      );
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
    sampleMatch() {
      this.$api.emit("subscribe", this.sampleInstrument);
      this.$api.emit("match_item_compute", this.sampleActive);
      // TEMP
      this.loadingInstance = this.$buefy.loading.open();
    },
    onMatchItemComputeFinished() {
      if (this.loadingInstance) {
        this.loadingInstance.close();
        this.loadingInstance = null;
      }
    },
    onMatchItemComputeFailed() {
      if (this.loadingInstance) {
        this.loadingInstance.close();
        this.loadingInstance = null;
      }
    },
    async saveSampleItem() {
      this.saveAttributes();
    },
    saveTemplate() {
      this.$buefy.dialog.prompt({
        title: "Template name",
        confirmText: "Save",
        inputAttrs: {
          placeholder:
            this.loadedTemplate.name === "default"
              ? "template name"
              : this.loadedTemplate.name,
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
          // copy loadedTempate fields with user input
          let newTemplate = {
            name: templateName,
            type: this.templateType,
            template: this.clone(this.formFields),
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
    saveAttributes() {
      // convert [{label, value...}, ...] to object
      let props = {};
      let sample_item_attributes = {};
      this.formFields.forEach((field) => {
        if (field.required) props[field.label] = field.value;
        else sample_item_attributes[field.label] = field.value;
      });
      if (this.action == "create") {
        let newSampleItem = {
          ...props,
          sample_item_attributes,
          sample_item_type: this.sampleItemType,
          sample_batch_id: this.batchActive.sample_batch_id,
          filter_id: this.sampleItemFilterId,
        };
        this.$api.emit("sample_item_create", [newSampleItem]);
      } else if (this.action == "update") {
        let newSampleItem = {
          ...this.sampleActive,
          ...props,
          sample_item_attributes,
          sample_item_type: this.sampleItemType,
          sample_batch_id: this.batchActive.sample_batch_id,
          filter_id: this.sampleItemFilterId,
        };
        this.$api.emit("sample_item_update", [newSampleItem]);
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
    loadedTemplate: {
      handler(newValue) {
        if (newValue) {
          // Make a copy to avoid mutating the loaded template directly
          this.formFields = this.clone(newValue.template);
        }
      },
      deep: true,
    },
    modalActive() {
      if (this.modalActive) this.activeStep = 0;
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
        Object.keys(data.sampleItemRecordToLoad[attributesField]).forEach(
          (attr) =>
            newTemplate.template.push({
              label: attr,
              value: data.sampleItemRecordToLoad[attributesField][attr],
            })
        );
      }
      this.loadedTemplate = newTemplate;
      this.sampleFilename = data.sampleItemRecordToLoad.filename;
      this.sampleInstrument = data.sampleItemRecordToLoad.instrument;
      this.sampleItemFilterId = data.sampleItemRecordToLoad.filter_id;
      this.sampleItemType = data.sampleItemRecordToLoad.sample_item_type;
    },
  },
  // TEMP
  beforeDestroy() {
    // Cleanup the socket.io event listener
    this.$api.socket.off(
      "match_item_compute_finished",
      this.onMatchItemComputeFinished
    );
    this.$api.socket.off(
      "match_item_compute_failed",
      this.onMatchItemComputeFailed
    );
    this.$api.emit("unsubscribe", this.sampleInstrument);
  },
};
</script>
