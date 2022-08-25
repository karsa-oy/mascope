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
      templateType: "sample_item",
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
      batchActive: "batch/active",
      itemsSelected: "batch/sampleItemsSelected",
      allTemplates: "app/attributeTemplates",
    }),
    ...sync({
      modalActive: "modal/sampleItemAttributesSaveActive",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.savedTemplates];
    },
    itemSelected() {
      return this.itemsSelected.length == 1 ? this.itemsSelected[0] : null;
    },
    savedTemplates() {
      return this.allTemplates.filter(
        (template) => template.type == this.templateType
        );
    },
    itemSelectedTemplate() {
      return {
        template: this.defaultTemplate.template,
        row: this.itemSelected,
      };
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
        ...this.itemSelected,
        ...props,
        attributes
        };
      this.$api.emit('sample_item_update', [newSampleItem]);
    },
  },
  watch: {
    modalActive: async function (active) {
      if (active) {
        this.sampleItemRecordToLoad = {};
        await this.$nextTick();
        this.sampleItemRecordToLoad = this.itemSelectedTemplate;
      }
    },
  },
};
</script>

