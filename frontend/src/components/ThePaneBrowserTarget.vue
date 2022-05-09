<template>
  <base-browser
    name="Targets"
    :levels="targetLevels"
    :menu="[
      {
        label: 'Import targets',
        onClick: () =>
          activateModal({
            modal: 'targetImport',
          }),
      },
    ]"
  >
  </base-browser>
</template>

<script>
import { mapMutations, mapActions, mapGetters } from "vuex";
import { bindState } from "$lib/store";

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
    ...bindState({
      controlPressed: "key/control",
    }),
    ...mapGetters({
      matchesExist: "match/exists",
    }),
    compoundStats: function () {
      return this.$store.getters["target/stat/rows"]({
        level: "compound",
        selected: false,
      });
    },
    ionStats: function () {
      return this.$store.getters["target/stat/rows"]({
        level: "ion",
        selected: false,
      });
    },
    isotopeStats: function () {
      return this.$store.getters["target/stat/rows"]({
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
          rowClick: this.targetCompoundClick,
          rowStatus: this.$store.getters["target/status"],
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
          rowClick: this.targetIonClick,
          rowStatus: this.$store.getters["target/status"],
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
          rowClick: this.targetIsotopeClick,
          rowStatus: this.$store.getters["target/status"],
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
      activateModal: "modal/activate",
    }),
    ...mapActions({
      toggleTargetCompoundSelection: "target/compoundSelectionToggle",
      toggleTargetIonSelection: "target/ionSelectionToggle",
      toggleTargetIsotopeSelection: "target/isotopeSelectionToggle",
      toggleTargetFocus: "target/focus/toggle",
    }),
    targetCompoundClick(row) {
      if (!this.controlPressed) {
        this.toggleTargetCompoundSelection(row);
      } else {
        this.toggleTargetFocus({
          level: "compound",
          target: row,
        });
      }
    },
    targetIonClick(row) {
      if (!this.controlPressed) {
        this.toggleTargetIonSelection(row);
      } else {
        this.toggleTargetFocus({
          level: "ion",
          target: row,
        });
      }
    },
    targetIsotopeClick(row) {
      if (!this.controlPressed) {
        this.toggleTargetIsotopeSelection(row);
      } else {
        this.toggleTargetFocus({
          level: "isotope",
          target: row,
        });
      }
    },
  },
};
</script>