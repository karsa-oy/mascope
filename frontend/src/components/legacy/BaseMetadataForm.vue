<template>
  <div>
    <!-- Modals -->
    <!-- End of modals -->

    <!-- Main content -->
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
      <h1 style="font-size: 16px; text-align: center">
        <p>
          <b>{{ formTitle }}</b>
        </p>
      </h1>
      <div><br /></div>
      <div v-for="item in formFields" :key="item.label">
        <template>
          <b-field :label="item.label" custom-class="dark">
            <b-input
              v-model="item.value"
              :placeholder="showEditFunctions ? 'default value' : ''"
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
                @click="removeField($event)"
                type="is-danger"
                icon-right="delete"
              >
              </b-button>
            </div>
          </b-field>
          <!-- <div><br></div> -->
        </template>
      </div>
      <div v-if="showEditFunctions">
        <b-field label="New field" custom-class="dark">
          <b-button @click="addField()" expanded>
            <b>+</b>
          </b-button>
        </b-field>
      </div>
      <div><br /></div>
      <b-field
        label="Reuse template"
        v-if="Boolean(loadTemplatePath) || Boolean(saveTemplatePath)"
        custom-class="dark"
      >
        <div class="container">
          <div class="row">
            <div class="columns">
              <div
                class="column is-half"
                style="text-align: center"
                v-if="Boolean(loadTemplatePath)"
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
                class="column is-one-seventh"
                style="text-align: left"
                v-if="showEditFunctions"
              >
                <b-button
                  :disabled="
                    !loadedTemplate ||
                    loadedTemplate.name == 'default template'
                  "
                  @click="deleteTemplate()"
                  type="is-danger"
                  icon-right="delete"
                >
                </b-button>
              </div>
              <div
                class="column is-one-third"
                style="text-align: center"
                v-if="Boolean(saveTemplatePath)"
              >
                <b-button
                  @click="saveTemplate()"
                  :disabled="!formFields.length"
                  expanded
                >
                  Save
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
    <!-- End of main content -->
  </div>
</template>
    
<script type="text/javascript">
import { makeValidFilename } from "$lib/filename";

var fs = require("fs");
var path = require("path");
const _ = require("underscore");

export default {
  name: "BaseMetadataForm",
  props: {
    defaultTemplate: {
      type: Array,
      required: false,
      default: function () {
        return [];
      },
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
      required: false,
      default: "",
    },
    initialTemplate: {
      type: Array,
      required: false,
      default: null,
    },
    templatePath: {
      type: String,
      required: false,
      default: null,
    },
    loadTemplatePath: {
      type: String,
      required: false,
      default: function () {
        return this.templatePath;
      },
    },
    saveTemplatePath: {
      type: String,
      required: false,
      default: function () {
        return this.templatePath;
      },
    },
  },

  data() {
    return {
      alwaysAvailableTemplates: [
        {
          name: "default template",
          template: this.defaultTemplate,
        },
      ],
      availableTemplates: [],
      formFields: [],
      loadedTemplate: null,
      showEditFunctions: true,
    };
  },
  created() {
    if (this.loadTemplatePath) {
      this.findTemplates();
    }
    if (this.initialTemplate) {
      this.loadedTemplate = { name: null, template: this.initialTemplate };
    } else {
      this.loadedTemplate = {
        name: "default template",
        template: this.defaultTemplate,
      };
    }
  },
  mounted() {
    this.$nextTick(() => {
      // When creating the form, showEditFunctions is true to render space
      // for the buttons etc, now set it to false by default
      this.showEditFunctions = false;
    });
  },
  methods: {
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
          this.formFields.push({ label: fieldToAdd, value: "" });
          this.loadedTemplate = null;
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
          fs.unlinkSync(this.loadedTemplate.path);
          this.loadedTemplate = null;
          this.findTemplates();
        },
      });
    },
    findTemplates() {
      var self = this;
      self.availableTemplates = _.clone(this.alwaysAvailableTemplates);
      // Read templates from disk
      fs.readdir(this.loadTemplatePath, function (err, files) {
        if (err) {
          throw new Error(err);
        }
        files.forEach(function (file) {
          var filePath = path.join(self.loadTemplatePath, file);
          var stat = fs.statSync(filePath);
          if (stat.isFile()) {
            // Found a file
            let fileExt = path.parse(file).ext;
            if (_.isEqual(fileExt, ".json")) {
              let template = JSON.parse(fs.readFileSync(filePath, "utf8"));
              template.path = filePath;
              self.availableTemplates.push(template);
            }
          }
        });
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
      for (let i = 0; i < this.formFields.length; ++i) {
        if (_.isEqual(fieldToRemove, this.formFields[i].label)) {
          this.formFields.splice(i, 1);
          break;
        }
      }
      this.loadedTemplate = null;
    },
    saveTemplate() {
      this.$buefy.dialog.prompt({
        message: "Template name",
        confirmText: "Save",
        inputAttrs: {
          placeholder: "template name",
          maxlength: 100,
        },
        trapFocus: true,
        onConfirm: (templateName) => this.writeTemplate(templateName),
      });
    },
    writeTemplate(templateName) {
      const filename = makeValidFilename(templateName) + ".json";
      const templatePath = path.join(this.saveTemplatePath, filename);
      if (fs.existsSync(templatePath)) {
        this.$buefy.dialog.alert({
          title: "Failed to save template",
          message:
            "Template with given name exists already. Please choose a different name",
          type: "is-danger",
        });
        return;
      }
      const templateData = {
        name: templateName,
        template: this.formFields,
      };
      const templateJson = JSON.stringify(templateData, null, 4);
      fs.writeFileSync(templatePath, templateJson);
      // Add to list of available templates
      this.availableTemplates.push(templateData);
      // Set as loaded
      this.loadedTemplate = templateData;
    },
  },
  watch: {
    formFields: {
      handler(newValue) {
        this.$emit("metaDataUpdated", newValue);
      },
      deep: true,
    },
    loadedTemplate: function (newValue) {
      if (newValue) {
        // Make a copy to avoid mutating the loaded template directly
        this.formFields = _.clone(newValue.template);
      }
    },
  },
};
</script>