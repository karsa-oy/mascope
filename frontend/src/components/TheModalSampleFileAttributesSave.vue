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
        :templateType="templateType"
        :initialTemplates="availableTemplates"
        :showEditFunctions="true"
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
    }),
    availableTemplates () {
      return [this.defaultTemplate, ...this.templateRows];
    },
  },
  data: function () {
    return {
      templateType: 'sampleFile',
      defaultTemplate: {
        name: 'default',
        template: [
          {
            label: 'filename',
            required: true,
            placeholder: 'filename',
          },
          {
            label: 'description',
          },
        ],
      },
    };
  },
  methods: {
    ...mapMutations({
      sampleSaveAttributes: "sample/saveFileAttributes",
    }),
    ...mapActions({
      templateListRequest: "template/listRequest",
      templateSaveRequest: "template/save",
      templateDeleteRequest: "template/delete",
    }),
    saveTemplate(newValue) {
      newValue['type'] = this.templateType;
      this.templateSaveRequest(newValue);
    },
    deleteTemplate(newValue) {
      this.templateDeleteRequest(newValue.name);
    },
    saveAttributes(newValue) {
      this.sampleSaveAttributes({attribs: newValue});
    },

  },
  watch: {
    modalActive: function (active) {
      if (active)
        this.templateListRequest({type: this.templateType});
    },
  },
};
</script>
