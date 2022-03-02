<template>
  <section class="landing-modal">
    <b-modal
      :active.sync="modalLandingActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      :destroy-on-hide="false"
      aria-role="dialog"
      aria-modal
    >
      <div class="columns">
        <div class="modal-card" style="width: auto">
          <header class="modal-card-head">
            <p class="modal-card-title">Select project and experiment</p>
          </header>
          <section class="modal-card-body">
            <b-field label="Project" custom-class="dark">
              <b-select
                placeholder="Select a project"
                @input="selectProject($event)"
                required
                expanded
              >
                <option v-for="p in $projects" :value="p.title" :key="p.title">
                  {{ p.title }}
                </option>
              </b-select>
            </b-field>

            <b-button expanded @click="launchProjectAttributesModal('new')">
              New Project
            </b-button>

            <div><br /></div>

            <b-field label="Experiment" custom-class="dark">
              <b-select
                placeholder="Select an experiment"
                @input="selectExperiment($event)"
                :disabled="!$projectSelected.title"
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

            <b-button
              expanded
              @click="launchNewExperimentModal()"
              :disabled="!$projectSelected.title"
            >
              New Experiment
            </b-button>
          </section>
          <footer class="modal-card-foot">
            <b-button
              @click="modalLandingActive = false"
              is-dark
              :disabled="
                !(
                  $projectSelected.title.length &&
                  $experimentSelected.title.length
                )
              "
            >
              Proceed
            </b-button>
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
  methods: {},
  watch: {},
};
</script>