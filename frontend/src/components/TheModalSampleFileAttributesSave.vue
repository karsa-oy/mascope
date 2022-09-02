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
      <base-attributes-form
        formTitle="Save sample attributes"
        :showEditFunctions="true"
        :templateType="templateType"
        :initialTemplates="availableTemplates"
        :attributesToLoad="sampleFileRecordToLoad"
        @saveTemplate="saveTemplate"
        @deleteTemplate="deleteTemplate"
        @saveAttributes="saveAttributes"
        @loadAttributes="loadAttributes"
      >
      </base-attributes-form>
    </b-modal>
  </section>
</template>

<script>
import BaseAttributesForm from "./BaseAttributesForm.vue";
import { mapMutations } from "vuex";
import { get, sync } from "vuex-pathify";

export default {
  name: "TheModalSampleFileAttributesSave",
  components: {
    BaseAttributesForm,
  },
  props: {},
  data: function () {
    return {
      templateType: "sample_file",
      sampleFileRecordToLoad: {},
      defaultTemplate: {
        name: "default",
        template: [
          {
            label: "filename",
            required: true,
            placeholder: "filename",
            key: true, // the field is a key to load data from db
          },
          {
            label: "title",
            required: true,
            placeholder: "visible title of the file in batches",
          },
          {
            label: "description",
            required: true,
            placeholder: "description",
          },
        ],
      },
    };
  },
  computed: {
    ...get({
      allTemplates: "app/attributeTemplates",
    }),
    ...sync({
      modalActive: "modal/sampleFileAttributesSaveActive",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.savedTemplates];
    },
    savedTemplates() {
      return this.allTemplates.filter(
        (template) => template.type == this.templateType
        );
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    saveTemplate(newTemplate) {
      newTemplate["type"] = this.templateType;
      this.$api.emit('attribute_template_create', [newTemplate]);
    },
    deleteTemplate(templates) {
      this.$api.emit('attribute_template_delete', templates);
    },
    saveAttributes(attributeTemplate) {
      // convert [{label, value...}, ...] to object
      let props = {};
      let attributes = {};
      attributeTemplate.forEach(
        (field) => {
          if (field.required) props[field.label] = field.value;
          else attributes[field.label] = field.value;
          }
        );
      let newSampleFile = {
        ...this.sampleFileRecordToLoad.row,
        ...props,
        attributes
        };
      if (newSampleFile.sample_file_id) {
        this.$api.emit('sample_file_update', [newSampleFile]);
      } else {
        this.$api.emit('sample_file_create', [newSampleFile]);
      }
      this.deactivateModal();
    },
    loadAttributes(filters) {
      const filename = filters.filename;
      this.$api
        .query(
          `--sql
          SELECT *
          FROM sample_file
          WHERE filename == '${filename}';`
        )
        .then((res) => {
          this.sampleFileRecordToLoad = {
            template: this.defaultTemplate.template,
            row: res[0],
          };
        });
    },
  },
};
</script>

