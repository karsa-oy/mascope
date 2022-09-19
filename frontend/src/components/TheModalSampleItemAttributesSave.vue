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
          <h1 style="font-size: 16px; text-align: center">
            <p>
              <b>{{ formTitle }}</b>
            </p>
          </h1>
        </div>
        <div v-for="item in formFields" :key="item.label">
          <template>
            <b-field :label="item.label.replaceAll('_', ' ')">
              <b-input
                v-model="item.value"
                :placeholder="
                  showEditFunctions ? item.placeholder || 'default value' : ''
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
          <b-field label="Sample type">
            <b-dropdown
              aria-role="list"
              v-model="sampleItemType"
              expanded
              >
              <template #trigger>
                  <b-button
                      :label="sampleItemType"
                      icon-right="menu-down"
                      expanded
                      style="align:left"
                  />
              </template>
              <b-dropdown-item aria-role="listitem" value="SAMPLE">Sample</b-dropdown-item>
              <b-dropdown-item aria-role="listitem" value="BLANK">Blank</b-dropdown-item>
              <b-dropdown-item aria-role="listitem" value="CALIBRATION">Calibration</b-dropdown-item>
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
                      !this.sampleItemType
                      || (
                        this.formFields.filter((f) => f.required).length !=
                        this.formFields
                        .filter((f) => f.required)
                        .filter((f) => f.value).length
                      )
                    "
                    type="is-success"
                    icon-left="content-save"
                    @click="saveAttributes"
                  >
                    Save sample
                  </b-button>
                </div>
              </div>
            </div>
            <div class="row">
              <br />
            </div>
          </div>
        </b-field>
      </div>
    </b-modal>
  </section>
</template>

<script>

import * as _ from "underscore";
import { mapMutations } from "vuex";
import { get, sync } from "vuex-pathify";

export default {
  name: "TheModalSampleItemAttributesSave",
  components: {
  },
  props: {},
  data: function () {
    return {
      action: null,
      defaultTemplate: {
        name: "default",
        template: [
          {
            label: "sample_item_name",
            required: true,
            placeholder: "visible title of the item in batches",
          },
          {
            label: "filename",
            required: true,
            placeholder: "filename",
            disabled: true,
          },
          {
            label: "sample_item_description",
            required: true,
            placeholder: "description",
          },
        ],
      },
      formFields: [],
      loadedTemplate: null,
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
      sampleActive: "sample/active",
    }),
    ...sync({
      modalActive: "modal/sampleItemAttributesSaveActive",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.savedTemplates];
    },
    editable() {
      return ['create', 'update'].includes(this.action);
    },
    fillable() {
      return ['create', 'update'].includes(this.action);
    },
    formTitle() {
      return "Sample information";
    },
    savedTemplates() {
      return this.allTemplates.filter(
        (template) => template.type == this.templateType
        );
    },
  },
  created() {
    this.loadedTemplate = this.clone(this.availableTemplates[0]);
  },
  methods: {
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
            'attribute_template_delete',
            this.availableTemplates.filter(
              (template) => 
              (template.attribute_template_id == this.loadedTemplate.attribute_template_id)
            ).map((template) => template.attribute_template_id)
          );
        }
      });
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
          this.$api.emit('attribute_template_create', [this.loadedTemplate]);
        },
      });
    },
    saveAttributes() {
      this.$buefy.dialog.confirm({
        title: this.formTitle,
        message:
          `${this.formTitle} for <b>` + this.formFields[0].value + "</b>?",
        confirmText: "Save",
        onConfirm: () => {
          // convert [{label, value...}, ...] to object
          let props = {};
          let sample_item_attributes = {};
          this.formFields.forEach(
            (field) => {
              if (field.required) props[field.label] = field.value;
              else sample_item_attributes[field.label] = field.value;
              }
            );
          let newSampleItem = {
            ...props,
            sample_item_attributes,
            sample_item_type: this.sampleItemType,
            sample_batch_id: this.batchActive.sample_batch_id,
            };
          if (this.action == 'create') {
            this.$api.emit('sample_item_create', [newSampleItem]);
          } else if(this.action == 'update') {
            newSampleItem.sample_item_id = this.sampleActive.sample_item_id;
            this.$api.emit('sample_item_update', [newSampleItem]);
          }
        },
      });
      this.deactivateModal();
    },
  },
  watch: {
    loadedTemplate: {
      handler(newValue) {
        if (newValue) {
          // Make a copy to avoid mutating the loaded template directly
          this.formFields = this.clone(newValue.template);
        }
      },
      deep: true,
    },
    modalProps: async function (data) {
      this.action = data.action;
      let newTemplate = {
          name: null,
          type: this.templateType,
          template: [],
        };
        for (let { label, key, required, disabled } of this.defaultTemplate.template) {
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
        const attributesField = this.templateType + '_attributes';
        if (data.sampleItemRecordToLoad[attributesField]) {
          Object.keys(data.sampleItemRecordToLoad[attributesField]).forEach((attr) =>
            newTemplate.template.push({
              label: attr,
              value: data.sampleItemRecordToLoad[attributesField][attr],
            })
          );
        }
        this.loadedTemplate = newTemplate;
        this.sampleItemType = data.sampleItemRecordToLoad.sample_item_type;
    },
  },
};
</script>

