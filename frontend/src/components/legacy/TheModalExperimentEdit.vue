<template>
  <section class="experiment-attribute-modal">
    <b-modal
      :active.sync="modalExperimentAttributesActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
    >
      <div class="modal-card" style="width: 500px">
        <div class="columns">
          <div class="column">
            <header class="modal-card-head">
              <p class="modal-card-title">Edit experiment</p>
            </header>
            <section class="modal-card-body">
              <BaseMetadataForm
                formTitle="Experiment attributes"
                :initialTemplate="experimentEditFormProps.attributes"
                :editable="true"
                @metaDataUpdated="experimentAttributesFields = $event"
              >
              </BaseMetadataForm>
              <div><br /></div>
              <BaseMetadataForm
                formTitle="Sample attribute template"
                :initialTemplate="
                  experimentEditFormProps.sampleAttributesTemplate
                "
                :editable="false"
                :fillable="false"
              >
              </BaseMetadataForm>
            </section>
          </div>
        </div>
        <!-- Footer -->
        <footer class="modal-card-foot">
          <b-button :disabled="false" @click="saveExperiment()">
            Save
          </b-button>
          <b-button @click="modalExperimentAttributesActive = false">
            Cancel
          </b-button>
          <div style="position: absolute; right: 20px">
            <b-tooltip
              label="Delete experiment"
              position="is-left"
              :delay="1000"
            >
              <b-button
                type="is-danger"
                icon-left="delete"
                @click="
                  deleteExperiment(experimentEditFormProps.attributes[0].value)
                "
              >
              </b-button>
            </b-tooltip>
          </div>
        </footer>
      </div>
    </b-modal>
  </section>
</template>

<script>
export default {
  name: "",
  components: {},
  props: {},
  computed: {},
  data: function () {},
  methods: {
    launchExperimentAttributesModal(experiment) {
      this.experimentEditFormProps = {
        project: experiment.project,
        experiment: experiment.title,
        attributes: experiment.attributes,
        sampleAttributesTemplate: experiment.sampleAttributesTemplate,
      };
      this.modalExperimentAttributesActive = true;
    },
    deleteExperiment(title) {
      const experimentToDelete = this.getExperiment(title);
      this.$experimentDeleteRequest = {
        project: experimentToDelete.project,
        experiment: experimentToDelete.title,
      };
    },
  },
};
</script>