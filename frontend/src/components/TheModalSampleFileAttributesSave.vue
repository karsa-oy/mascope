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
import { bindState } from "$lib/store";
import { mapActions, mapMutations } from "vuex";

export default {
  name: "TheModalSampleFileAttributesSave",
  components: {
    BaseAttributesForm,
  },
  props: {},
  computed: {
    ...bindState({
      modalActive: "modal/sampleFileAttributesSaveActive",
      templateRows: "template/rows",
      sampleFileRows: "sample/file/rows",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.templateRows];
    },
  },
  data: function () {
    return {
      templateType: "sampleFile",
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
  methods: {
    ...mapMutations({
      sampleFileUpdate: "sample/file/UPDATE",
    }),
    ...mapActions({
      getSampleFile: "sample/file/listFiles",
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
      this.sampleFileUpdate(row);
    },
    loadAttributes(filters) {
      this.getSampleFile({ filters });
    },
  },
  watch: {
    modalActive: function (active) {
      if (active) this.templateListRequest({ type: this.templateType });
    },
    sampleFileRows: function () {
      if (this.sampleFileRows.length != 1) {
        this.sampleFileRecordToLoad = {};
        return;
      }
      this.sampleFileRecordToLoad = {
        template: this.defaultTemplate.template,
        row: this.sampleFileRows[0],
      };
    },
  },
};
</script>

