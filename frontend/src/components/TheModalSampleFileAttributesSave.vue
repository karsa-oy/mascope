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
import { call, get } from "vuex-pathify";

export default {
  name: "TheModalSampleFileAttributesSave",
  components: {
    BaseAttributesForm,
  },
  props: {},
  computed: {
    ...get({
      templateRows: "app/attributeTemplates",
      modalActive: "modal/sampleFileAttributesSaveActive",
    }),
    availableTemplates() {
      return [this.defaultTemplate, ...this.templateRows];
    },
  },
  data: function () {
    return {
      templateType: "sampleFile",
      sampleFiles: [],
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
      deactivateModal: "modal/deactivate",
      sampleFileUpdate: "sample/file/UPDATE",
    }),
    ...call({
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
            row: res.toArray()[0],
          };
        });
    },
  },
};
</script>

