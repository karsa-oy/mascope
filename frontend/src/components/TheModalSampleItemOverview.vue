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
      <div class="modal-card" style="width: 500px">
        <header class="modal-card-head">
          <h2 class="subtitle">{{ modalTitle }}</h2>
        </header>
        <section class="modal-card-body" style="min-height: 250px"></section>
        <footer class="modal-card-foot"></footer>
      </div>
    </b-modal>
  </section>
</template>

<script>
import { mapMutations } from "vuex";
import { get, sync } from "vuex-pathify";

export default {
  name: "TheModalSampleItemOverview",
  components: {},
  props: {},
  data: function () {
    return {};
  },
  computed: {
    ...get({
      modalProps: "modal/sampleItemOverviewProps",
      sampleItem: "sample/active",
    }),
    ...sync({
      modalActive: "modal/sampleItemOverviewActive",
    }),
    modalTitle() {
      return this.sampleItem ? this.sampleItem.sample_item_name : "";
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
  },
  watch: {},
};
</script>
