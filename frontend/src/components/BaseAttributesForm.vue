<template>
  <div>
    <div class="box" style="background-color: inherit">
      <div style="text-align: right" v-if="editable">
        <b-button
          icon-right="settings"
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
          <b-field :label="item.label" custom-class="dark">
            <b-input
              v-model="item.value"
              :placeholder="showEditFunctions ? item.placeholder||'default value' : ''"
              :required="fillable && item.required"
              :disabled="!fillable || item.disabled"
              lazy
              expanded
            >
            </b-input>
            <div v-if="item.key">
              <b-button
                :id="item.label"
                :disabled="!item.value || item.value.length==0"
                @click="loadAttributes({[item.label]: item.value})"
                type="is-warning"
                icon-right="database"
                hover title="Load attributes"
              >
              </b-button>
            </div>
            <div v-if="showEditFunctions">
              <b-button
                :id="item.label"
                :disabled="item.required"
                @click="removeField"
                type="is-danger"
                icon-right="delete"
                hover title="Delete Field"
              >
              </b-button>
            </div>
          </b-field>
        </template>
      </div>
      <div v-if="showEditFunctions" style="padding-top: 2em">
        <b-field custom-class="dark">
          <b-button @click="addField" expanded>
            <b>Add new field</b>
          </b-button>
        </b-field>
      </div>
      <div><br /></div>
      <b-field
        label="Reuse template"
        custom-class="dark"
      >
        <div class="container">
          <div class="row">
            <div class="columns">
              <div
                class="column is-half"
                style="text-align: center"
              >
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
                  hover title="Delete Template"
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
                  hover title="Save Template"
                >
                </b-button>
              </div>
              <div
                class="column is-one-half"
                style="text-align: right"
              >
                <b-button
                  :disabled="
                    this.formFields.filter(f => f.required).length !=
                    this.formFields.filter(f => f.required).filter(f => f.value).length
                  "
                  type="is-success"
                  icon-left="content-save"
                  @click="saveAttributes"
                >
                  {{ formTitle }}
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
  </div>
</template>
    
<script type="text/javascript">
const _ = require("underscore");

export default {
  name: "BaseMetadataForm",
  props: {
    initialTemplates: {
      type: Array,
      required: true,
      default: function () {
        return [];
      },
    },
    attributesToLoad: {
      type: Object,
      required: false,
      default: function () {
        return {};
      },
    },
    showEditFunctions: {
      type: Boolean,
      required: false,
      default: false,
    },
    editable: {
      type: Boolean,
      required: false,
      default: false,
    },
    fillable: {
      type: Boolean,
      required: false,
      default: true,
    },
    formTitle: {
      type: String,
      required: true,
      default: "",
    },
    templateType: {
      type: String,
      required: true,
      default: "",
    },
  },

  data() {
    return {
      loadedTemplate: null,
      formFields: [],
    };
  },
  computed: {
    availableTemplates () { return this.initialTemplates },
  },
  created() {
    this.loadedTemplate = this.clone(this.availableTemplates[0]);
  },
  methods: {
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
            template: [...this.formFields, { label: fieldToAdd, value: "" },]
          }
        },
      });
    },
    removeField(event) {
      // Field to remove label is in button element id, find it from the event data
      let fieldToRemove = "";
      for (let i in event.path) {
        fieldToRemove = event.path[i].id;
        if (fieldToRemove) break;
      }
      if (!fieldToRemove) {
        // Failed to find the button id
        console.log("fieldToRemove not found at event.path[1].id: ", event);
        return;
      }
      for (let i = 0; i < this.loadedTemplate.template.length; ++i) {
        if (_.isEqual(fieldToRemove, this.loadedTemplate.template[i].label)) {
          this.loadedTemplate = {
            name: null,
            template: [...this.loadedTemplate.template.slice(0,i), ...this.loadedTemplate.template.slice(i+1)],
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
          for(let i=0; i<this.availableTemplates.length; ++i) {
            if ( this.loadedTemplate.name === this.availableTemplates[i].name ) {
              this.$emit('deleteTemplate', this.availableTemplates[i]);
              this.availableTemplates.splice(i, 1);
              break;
            }
          }
          this.loadedTemplate = this.availableTemplates.length > 0 ? this.clone(this.availableTemplates[0]) : null;
        },
      });
    },
    saveTemplate() {
      this.$buefy.dialog.prompt({
        title: "Template name",
        confirmText: "Save",
        inputAttrs: {
          placeholder: this.loadedTemplate.name === 'default' ? "template name":this.loadedTemplate.name,
          maxlength: 100,
        },
        trapFocus: true,
        onConfirm: (templateName) => {
            if (templateName.toLowerCase() === 'default') {
              this.$buefy.toast.open({
                message: `Name "${templateName}" is not allowed`,
                duration: 5000,
                type: 'is-danger'
              });
              return;
            }
            // copy loadedTempate fields with user input
            let newTemplate = {name: templateName, type: this.templateType, template: this.clone(this.formFields)};
            let i = 0;
            // set loaded template
            for (i = 0; i < this.availableTemplates.length; ++i) {
              if (_.isEqual(templateName, this.availableTemplates[i].name))
                break;
            }
            if ( i < this.availableTemplates.length ) {
              // existing template
              this.availableTemplates[i] = this.clone(newTemplate);
            } else {
              // new template
              this.availableTemplates.push(this.clone(newTemplate));
            }
            this.loadedTemplate = this.clone(newTemplate);
            // push new template
            this.$emit('saveTemplate', this.loadedTemplate);
        },
      });
    },
    saveAttributes() {
      this.$buefy.dialog.confirm({
        title: this.formTitle,
        message:
          `${this.formTitle} for <b>` +
          this.formFields[0].value +
          "</b>?",
        confirmText: "Save",
        onConfirm: () => {
          this.$emit('saveAttributes', this.formFields);
        },
      });
    },
    loadAttributes(requestObject) {
      this.$emit('loadAttributes', requestObject);
    },
  },
  watch: {
    formFields: {
      handler(newValue) {
        this.$emit("metaDataUpdated", newValue);
      },
      deep: true,
    },
    loadedTemplate: {
      handler (newValue) {
        if (newValue) {
          // Make a copy to avoid mutating the loaded template directly
          this.formFields = this.clone(newValue.template);
        }
      },
      deep: true,
    },
    attributesToLoad: function (data) {
      if ( _.isEmpty(data) || _.isEmpty(data.row) ) {
        return;
      }
      let newTemplate = {
        name: null,
        type: this.templateType,
        template: [],
      }
      for(let {label, key, required} of data.template) {
        if (required) {
          newTemplate.template.push({label, key, required, value: data.row[label]});
        }
      }
      Object.keys(data.row.attributes).forEach( (attr) =>
        newTemplate.template.push({label: attr, value: data.row.attributes[attr]})
      );
      this.loadedTemplate = newTemplate;
    },
  },
};
</script>