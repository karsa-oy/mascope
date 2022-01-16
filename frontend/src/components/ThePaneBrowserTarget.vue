<template>
  <base-browser name="Targets" :levels="targetLevels">
    <template v-slot:header>
      <b-button
        icon-left="plus"
        size="is-small"
        @click="
          activateModal({
            modal: 'targetImport',
          })
        "
      >
        <b>import</b>
      </b-button>
    </template>
  </base-browser>
</template>

<script>
import { mapMutations, mapActions, mapGetters } from "vuex";

import BaseBrowser from "./BaseBrowser";

export default {
  name: "ThePaneBrowserTarget",
  components: {
    BaseBrowser,
  },
  data: function () {
    return {
      showOnlyChecked: false,
    };
  },
  computed: {
    ...mapGetters({
      matchesExist: "workspace/match/exists",
    }),
    compoundStats: function () {
      return this.$store.getters["workspace/target/stats"]({
        level: "compound",
        selected: false,
      });
    },
    ionStats: function () {
      return this.$store.getters["workspace/target/stats"]({
        level: "ion",
        selected: false,
      });
    },
    isotopeStats: function () {
      return this.$store.getters["workspace/target/stats"]({
        level: "isotope",
        selected: false,
      });
    },
    targetLevels: function () {
      let hidden = !this.matchesExist;
      return [
        {
          name: "Compound",
          slug: "compound",
          cols: [
            { field: "name", label: "Name", width: "40%" },
            { field: "formula", label: "Compound", width: "40%" },
            {
              field: "matchScore",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.samplePeakHeight),
                };
              },
            },
          ],
          rows: this.compoundStats,
          defaultSort: ["matchScore", "desc"],
          detailsIcon: "default",
          rowClick: this.toggleTargetCompoundSelection,
        },
        {
          name: "Ion",
          slug: "ion",
          cols: [
            { field: "ionMech", label: "Mechanism", width: "45%" },
            { field: "formula", label: "Ion", width: "45%" },
            {
              field: "matchScore",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.peakHeight),
                };
              },
            },
          ],
          rows: this.ionStats,
          defaultSort: ["matchScore", "desc"],
          detailsIcon: "default",
          rowClick: this.toggleTargetIonSelection,
        },
        {
          name: "Isotope",
          slug: "isotope",
          cols: [
            { field: "mz", label: "m/z", width: "45%" },
            { field: "relAbu", label: "Rel. Abu.", width: "45%" },
            {
              field: "matchScore",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.peakHeight),
                  "Rel. abundance": this.formatter.format(row.relAbu),
                };
              },
            },
          ],
          rows: this.isotopeStats,
          defaultSort: ["matchScore", "desc"],
          detailsIcon: null,
          rowClick: this.toggleTargetIsotopeSelection,
        },
      ];
    },
  },
  created: function () {
    this.formatter = new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  },
  methods: {
    ...mapMutations({
      activateModal: "ui/modal/activate",
    }),
    ...mapActions({
      toggleTargetCompoundSelection: "workspace/target/compoundToggleSelection",
      toggleTargetIonSelection: "workspace/target/ionToggleSelection",
      toggleTargetIsotopeSelection: "workspace/target/isotopeToggleSelection",
    }),
  },
};
</script>