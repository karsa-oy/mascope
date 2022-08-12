<template>
  <section>
    <base-browser name="Targets" :levels="targetLevels" :menu="menu">
    </base-browser>
  </section>
</template>

<script>
import { mapMutations, mapActions, mapGetters } from "vuex";
import { bindState } from "$lib/store";

import BaseBrowser from "./BaseBrowser.vue";

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
      modalTargetCollectionOpProps: "modal/targetCollectionOpProps",
    }),
    ...mapGetters({
      batchActive: "batch/activeRows",
      matchesExist: "match/exists",
      sampleItemFocused: "sample/item/focusedRow",
      targetCollectionsSelected: "target/collection/selectedRows",
      uniqueTargetCollection: "target/collection/uniqueRow",
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
            { field: "name", label: "Collection", width: "90%" },
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
            { field: "formula", label: "Compound", width: "45%" },
            { field: "name", label: "", width: "45%" },
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
            { field: "formula", label: "Ion", width: "45%" },
            { field: "ionMech", label: "", width: "45%" },
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
            { field: "mz", label: "Isotope", width: "45%" },
            { field: "relativeAbundance", label: "", width: "45%" },
            {
              field: "matchScore",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.peakHeight),
                  "Rel. abundance": this.formatter.format(
                    row.relativeAbundance
                  ),
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
      let addCollectionToBatchButton = {
        label: "Add target collection to batch",
        onClick: this.collectionAddToBatch,
      };
      if (this.uniqueTargetCollection) {
        return [
          addCollectionToBatchButton,
          createCollectionButton,
          updateCollectionButton,
          deleteCollectionButton,
        ];
      } else {
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
      targetCollectionRead: "target/collection/read",
      targetCollectionToggle: "target/collection/toggle",
      targetCompoundToggle: "target/compound/toggle",
      targetIonToggle: "target/ion/toggle",
      targetIsotopeToggle: "target/isotope/toggle",
    }),
    collectionAddToBatch() {
      this.modalTargetCollectionOpProps = {
        action: "addToBatch",
        collection: this.targetCollectionsSelected[0],
      };
      this.activateModal({
        modal: "targetCollectionOp",
      });
    },
    collectionCreate() {
      this.modalTargetCollectionOpProps = {
        action: "create",
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
    collectionGetAll() {
      this.targetCollectionRead();
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
  },
  watch: {
    batchActive: function () {
      if (!this.batchActive.length) {
        this.collectionGetAll();
      }
    },
  },
};
</script>