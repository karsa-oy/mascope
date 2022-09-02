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
        formTitle="Save item attributes"
        :showEditFunctions="true"
        :templateType="templateType"
        :initialTemplates="availableTemplates"
        :attributesToLoad="sampleItemRecordToLoad"
        @saveTemplate="saveTemplate"
        @deleteTemplate="deleteTemplate"
        @saveAttributes="saveAttributes"
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
  name: "TheModalSampleItemAttributesSave",
  components: {
    BaseAttributesForm,
  },
  props: {},
  data: function () {
    return {
      action: null,
      templateType: "sample_item",
      batchToAddTo: [],
      sampleItemRecordToLoad: {},
      defaultTemplate: {
        name: "default",
        template: [
          {
            label: "title",
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
      modalProps: "modal/sampleItemAttributesSaveProps",
    }),
    ...sync({
      modalActive: "modal/sampleItemAttributesSaveActive",
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
      let newSampleItem = {
        ...props,
        attributes,
        sample_batch_id: this.batchToAddTo,
        };
      if (this.action == 'create') {
        this.$api.emit('sample_item_create', [newSampleItem]);
      } else if(this.action == 'update') {
        this.$api.emit('sample_item_update', [newSampleItem]);
      }
      this.deactivateModal();
    },
  },
  watch: {
    modalProps: async function (data) {
      this.sampleItemRecordToLoad = {};
      await this.$nextTick();
      this.action = data.action;
      this.batchToAddTo = data.batchToAddTo;
      this.sampleItemRecordToLoad = {
        template: this.defaultTemplate.template,
        row: data.sampleItemRecordToLoad
      };
    },
  },
};
</script>

