<template>
  <section class="experiment-attribute-modal">
    <b-modal
      :active.sync="modalNewExperimentActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
    >
      <div class="modal-card" style="width: 500px">
        <div class="columns">
          <div class="column">
            <header class="modal-card-head">
              <p class="modal-card-title">New experiment</p>
            </header>
            <section class="modal-card-body">
              <!-- Experiment attributes form -->
              <BaseMetadataForm
                formTitle="Experiment attributes"
                :defaultTemplate="experimentAttributesDefaultTemplate"
                :editable="true"
                :templatePath="experimentAttributesTemplatePath"
                @metaDataUpdated="experimentAttributesFields = $event"
              >
              </BaseMetadataForm>
              <!-- End of experiment attributes form -->
              <div><br /></div>
              <div hidden>
                <div><br /></div>
                <!-- Sample attributes form -->
                <BaseMetadataForm
                  :key="sampleAttributesKey"
                  formTitle="Sample attribute template"
                  :defaultTemplate="sampleAttributesDefaultTemplate"
                  :initialTemplate="
                    sampleAttributesTemplate.length
                      ? sampleAttributesTemplate
                      : null
                  "
                  :editable="true"
                  :fillable="false"
                  :templatePath="sampleAttributesTemplatePath"
                  @metaDataUpdated="sampleAttributesFields = $event"
                >
                </BaseMetadataForm>
                <!-- End of sample attributes form -->
              </div>
            </section>
          </div>
        </div>
        <!-- Footer -->
        <footer class="modal-card-foot">
          <b-button @click="saveExperiment()"> Save </b-button>
          <b-button @click="cancelNewExperiment()"> Cancel </b-button>
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
  methods: {},
};
</script>