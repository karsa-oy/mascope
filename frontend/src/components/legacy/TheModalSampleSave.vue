<template>
  <section class="sample-attribute-modal">
    <b-modal
      :active.sync="modalSampleAttributesActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      :destroy-on-hide="true"
      aria-role="dialog"
      aria-modal
    >
      <div class="columns">
        <div class="modal-card" style="width: auto">
          <header class="modal-card-head">
            <p class="modal-card-title">{{ sampleFormProps.filename }}</p>
          </header>
          <section class="modal-card-body writeSampleAttribute">
            <BaseMetadataForm
              :key="sampleFormKey"
              :formTitle="sampleFormProps.title"
              :defaultTemplate="sampleFormProps.attributes"
              :initialTemplate="sampleFormProps.attributes"
              :loadTemplatePath="sampleFormProps.loadTemplatePath"
              @metaDataUpdated="sampleAttributesFields = $event"
            >
            </BaseMetadataForm>

            <div><br /></div>
            <b-field label="Project" custom-class="dark">
              <b-select
                placeholder="Select a project"
                v-model="$projectSelected.title"
                @input="selectProject($event)"
                :disabled="autosave"
                required
                expanded
              >
                <option v-for="p in $projects" :value="p.title" :key="p.title">
                  {{ p.title }}
                </option>
              </b-select>
            </b-field>

            <b-field label="Experiment" custom-class="dark">
              <b-select
                placeholder="Select an experiment"
                v-model="$experimentSelected.title"
                @input="selectExperiment($event)"
                :disabled="autosave"
                required
                expanded
              >
                <option
                  v-for="e in $experiments"
                  :value="e.title"
                  :key="e.title"
                >
                  {{ e.title }}
                </option>
              </b-select>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button
              :type="sampleAttributesSaveButtonType"
              @click="saveSample()"
              :disabled="false"
            >
              Save
            </b-button>
            <b-button @click="modalSampleAttributesActive = false">
              Close
            </b-button>
            <div style="position: absolute; right: 20px">
              <b-tooltip
                label="Remove sample from this experiment"
                position="is-left"
                :delay="1000"
              >
                <b-button
                  type="is-danger"
                  icon-left="delete"
                  @click="removeSample(sampleFormProps.filename)"
                >
                </b-button>
              </b-tooltip>
            </div>
          </footer>
        </div>
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
    saveSample() {
      let $experimentSelected = this.$experimentSelected.title.length > 0;
      let $projectSelected = this.projectSelect.title.length > 0;
      if ($projectSelected && $experimentSelected) {
        this.modalSampleAttributesActive = false;
        this.$sampleSaveRequest = {
          filename: this.sampleFormProps.filename,
          experiment: this.sampleFormProps.experiment,
          project: this.sampleFormProps.project,
          attributes: this.sampleAttributesFields,
          method: this.sampleFormProps.method,
        };
      } else {
        this.$buefy.toast.open({
          duration: 3000,
          message:
            "Project and experiment must be selected to store sample attributes.",
          type: "is-danger",
        });
        return;
      }
    },
    removeSample(filename) {
      this.modalSampleAttributesActive = false;
      this.$sampleDeleteRequest = this.getSample(filename);
    },
  },
};
</script>