<template>
  <base-browser name="Targets" :levels="targetLevels" :menu="menu">
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
      sampleItemFocused: "sample/item/focusedRow",
      modalTargetCollectionOpProps: "modal/targetCollectionOpProps",
      targetCollectionsSelected: "target/collection/selectedRows",
    }),
    ...mapGetters({
      matchesExist: "match/exists",
    }),
    collectionStats: function () {
      return this.$store.getters["target/stat/rows"]({
        level: "collection",
        selected: false,
        itemFocused: true,
      });
    },
    compoundStats: function () {
      return this.$store.getters["target/stat/rows"]({
        level: "compound",
        selected: false,
        itemFocused: true,
      });
    },
    ionStats: function () {
      return this.$store.getters["target/stat/rows"]({
        level: "ion",
        selected: false,
        itemFocused: true,
      });
    },
    isotopeStats: function () {
      return this.$store.getters["target/stat/rows"]({
        level: "isotope",
        selected: false,
        itemFocused: true,
      });
    },
    targetLevels: function () {
      let hidden = !(this.matchesExist && this.sampleItemFocused);
      return [
        {
          name: "Collection",
          slug: "targetCollection",
          cols: [
            { field: "name", label: "Name", width: "40%" },
            { field: "formula", label: "Collection", width: "40%" },
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
          rows: this.collectionStats,
          defaultSort: ["matchScore", "desc"],
          detailsIcon: "default",
          rowClick: this.targetCollectionToggle,
        },
        {
          name: "Compound",
          slug: "targetCompound",
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
          rowClick: this.targetCompoundToggle,
        },
        {
          name: "Ion",
          slug: "targetIon",
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
          rowClick: this.targetIonToggle,
        },
        {
          name: "Isotope",
          slug: "targetIsotope",
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
          defaultSort: ["mz", "asc"],
          detailsIcon: null,
          rowClick: this.targetIsotopeToggle,
        },
      ];
    },
    menu() {
      // target collection
      let createCollectionButton = {
        label: "Create target collection",
        onClick: this.collectionCreate,
      };
      let updateCollectionButton = {
        label: "Update target collection",
        onClick: this.collectionUpdate,
      };
      let deleteCollectionButton = {
        label: "Delete target collection",
        onClick: this.collectionDelete,
      };
      switch (this.collectionStats.length) {
        case 0:
          return [createCollectionButton];
        case 1:
          return [
            createCollectionButton,
            updateCollectionButton,
            deleteCollectionButton,
          ];
        default:
          return [createCollectionButton];
      }
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
      targetCollectionToggle: "target/collection/toggle",
      targetCompoundToggle: "target/compound/toggle",
      targetIonToggle: "target/ion/toggle",
      targetIsotopeToggle: "target/isotope/toggle",
    }),
    collectionCreate() {
      this.modalTargetCollectionOpProps = {
        action: "create",
      };
      this.activateModal({
        modal: "targetCollectionOp",
      });
    },
    collectionUpdate() {
      this.modalTargetCollectionOpProps = {
        action: "update",
        collection: this.targetCollectionsSelected[0],
      };
      this.activateModal({
        modal: "targetCollectionOp",
      });
    },
    collectionDelete() {
      this.modalTargetCollectionOpProps = {
        action: "delete",
        collection: this.targetCollectionsSelected[0],
      };
      this.activateModal({
        modal: "targetCollectionOp",
      });
    },
  },
};
</script>