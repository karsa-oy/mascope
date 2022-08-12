<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
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
import { mapMutations, mapGetters } from "vuex";
import { sync, call, get } from "vuex-pathify";

export default {
  name: "TheModalSampleItemAttributesSave",
  components: {
    BaseAttributesForm,
  },
  props: {},
  data: function () {
    return {
      templateType: "sampleItem",
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
      modalActive: "modal/sampleItemAttributesSaveActive",
      templateRows: "app/attributeTemplates",
    }),
    ...mapGetters({
      batchActive: "batch/activeRow",
      itemsSelected: "sample/item/selectedRows",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.templateRows];
    },
    itemSelected() {
      return this.itemsSelected.length == 1 ? this.itemsSelected[0] : null;
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    ...call({
      sampleItemUpdate: "sample/item/update",
      templateListRequest: "template/requestTemplates",
      templateSaveRequest: "template/save",
      templateDeleteRequest: "template/delete",
    }),
    saveTemplate(newValue) {
      newValue["type"] = this.templateType;
      this.templateSaveRequest(newValue);
    },
    deleteTemplate(newValue) {
      this.templateDeleteRequest(newValue.name);
    },
    saveAttributes(newValue) {
      // convert [{label, value...}, ...] to object
      let row = {};
      newValue.forEach((field) => (row[field.label] = field.value || ""));
      row.id = this.itemSelected.id;
      row.sampleBatchId = this.itemSelected.sampleBatchId;
      this.sampleItemUpdate([row]);
      this.deactivateModal();
    },
  },
  watch: {
    itemSelected: function () {
      if (!this.itemSelected) {
        this.sampleItemRecordToLoad = {};
        return;
      }
    },
    modalActive: async function (active) {
      if (active) {
        this.templateListRequest({ type: this.templateType });
        await this.$nextTick();
        this.sampleItemRecordToLoad = {
          template: this.defaultTemplate.template,
          row: this.itemSelected,
        };
      }
    },
  },
};
</script>

