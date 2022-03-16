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
        :templateType="this.templateType"
        :initialTemplates="this.availableTemplates"
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
  name: "TheModalUpdateStore",
  components: {
    BaseAttributesForm,
  },
  props: {},
  computed: {
    ...bindState({
      modalActive: "modal/updateStoreActive",
      templateListResponse: "template/$listResponse",
    }),
  },
  data: function () {
    return {
      templateType: 'sample',
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
      availableTemplates: [],
    };
  },
  created() {
    this.availableTemplates = [this.defaultTemplate];
  },
  methods: {
    log(...args) {
      console.log('[TheModalUpdateStore]', ...args)
    },
    ...mapMutations({
      sampleSaveAttributes: "sample/saveFileAttributes",
    }),
    ...mapActions({
      // templateListRequest: "template/listRequest",
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
    templateListResponse: function (newValue) {
      this.availableTemplates = [this.defaultTemplate, ...newValue.templates];
    },
  },
};
</script>
