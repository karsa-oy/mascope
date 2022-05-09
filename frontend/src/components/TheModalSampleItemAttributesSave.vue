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
        @loadAttributes="loadAttributes"
      >
      </base-attributes-form>
    </b-modal>
  </section>
</template>

<script>
import BaseAttributesForm from "./BaseAttributesForm.vue";
import { bindState } from "$lib/store";
import { mapActions, mapMutations } from "vuex";

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
    ...bindState({
      modalActive: "modal/sampleItemAttributesSaveActive",
      templateRows: "template/rows",
      $sampleItemListResponse: "sample/$itemListResponse",
      batchSelected: "sample/batch/selection/row",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.templateRows];
    },
    itemSelected: function () {
      let items = this.$store.state.sample.item.selection.rows;
      return items.length == 1 ? items[0] : null;
    },
  },
  methods: {
    ...mapMutations({
      sampleItemUpdate: "sample/item/update",
      sampleItemRead: "sample/item/read",
      deactivateModal: "modal/deactivate",
    }),
    ...mapActions({
      templateListRequest: "template/listRequest",
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
      row.batchId = this.itemSelected.batchId;
      this.sampleItemUpdate([row]);
      this.deactivateModal();
    },
    loadAttributes(newValue) {
      this.sampleItemRead(newValue);
    },
  },
  watch: {
    modalActive: function (active) {
      if (active) this.templateListRequest({ type: this.templateType });
    },
    $sampleItemListResponse: function (response) {
      let row = (response.records && response.records[0]) || {};
      this.sampleItemRecordToLoad = {
        template: this.defaultTemplate.template,
        row: row,
      };
    },
  },
};
</script>

