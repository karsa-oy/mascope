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
      <div class="modal-card" style="width:100%; height:100%">
        <header class="modal-card-head">
          <h2 class="subtitle">{{ modalTitle }}</h2>
        </header>
        <section class="modal-card-body">
          <the-pane-sample-signal></the-pane-sample-signal>
        </section>
        <footer class="modal-card-foot">

        </footer>
      </div>
    </b-modal>
  </section>
</template>

<script>
import ThePaneSampleSignal from "./ThePaneSampleSignal.vue";

import { mapMutations } from "vuex";
import { get, sync } from "vuex-pathify";

export default {
  name: "TheModalSampleItemTargetIon",
  components: {
    ThePaneSampleSignal,
  },
  props: {},
  data: function () {
    return {

    };
  },
  computed: {
    ...get({
      modalProps: "modal/sampleItemTargetIonProps",
      sampleItem: "sample/active",
    }),
    ...sync({
      modalActive: "modal/sampleItemTargetIonActive",
    }),
    modalTitle() {
      return this.sampleItem
      ? this.sampleItem.sample_item_name + ": " + this.modalProps.target_ion_formula
      : "";
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
  },
  watch: {
  },
};
</script>

