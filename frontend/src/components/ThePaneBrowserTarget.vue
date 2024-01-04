<template>
  <section>
    <base-browser
      name="Targets"
      :levels="targetLevels"
      :menu="menu"
      :contextMenuIcon="contextMenuIcon"
      @tagClicked="matchScoreTagClicked"
    >
    </base-browser>
  </section>
</template>

<script>
import { mapMutations } from "vuex";

import { sync, get, call } from "vuex-pathify";

import BaseBrowser from "./BaseBrowser.vue";

const doNothing = () => {};

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
    ...sync({
      modalTargetCollectionOpProps: "modal/targetCollectionOpProps",
      activeIon: "visualization/activeIon",
    }),
    ...get({
      sampleBatchesSelected: "workspace/sampleBatchesSelected",
      matchCollections: "sample/matchCollections",
      matchCompounds: "sample/matchCompounds",
      matchIons: "sample/matchIons",
      matchIsotopes: "sample/matchIsotopes",
      sampleItemFocused: "sample/active",
      targetCollections: "batch/targetCollections",
      targetCollectionsSelected: "batch/targetCollectionsSelected",
      targetCompounds: "batch/targetCompounds",
      targetIons: "batch/targetIons",
      targetIsotopes: "batch/targetIsotopes",
    }),
    contextMenuIcon() {
      if (this.targetCollectionsSelected.length === 1) return "menu";
      if (this.sampleBatchesSelected.length === 1) return "dots-horizontal";
      if (this.sampleBatchesSelected.length !== 1) return "plus";
    },
    targetCollectionRows: function () {
      return this.sampleItemFocused && this.matchCollections
        ? this.matchCollections
        : this.targetCollections;
    },
    targetCompoundRows: function () {
      if (!this.sampleItemFocused || !this.matchCompounds) {
        return this.targetCompounds;
      }
      return this.targetCompounds.map((targetCompound) => {
        const matchCompound = this.matchCompounds.find(
          (mc) => mc.target_compound_id === targetCompound.target_compound_id
        );

        return matchCompound
          ? { ...targetCompound, ...matchCompound }
          : targetCompound;
      });
    },
    targetIonRows: function () {
      return this.sampleItemFocused && this.matchIons
        ? this.matchIons
        : this.targetIons;
    },
    targetIsotopeRows: function () {
      return this.sampleItemFocused && this.matchIsotopes
        ? this.matchIsotopes
        : this.targetIsotopes;
    },
    targetLevels: function () {
      let hidden = this.matchIsotopes ? false : true;
      return [
        {
          name: "Collection",
          slug: "target_collection",
          cols: [
            {
              field: "target_collection_name",
              label: "Collection",
              width: "30%",
            },
            {
              field: "target_collection_description",
              label: "Description",
              width: "60%",
            },
            {
              field: "match_score",
              label: "Score",
              width: "10%",
              displayMatchScore: true,
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(
                    row.sample_peak_area_sum
                  ),
                };
              },
            },
          ],
          rows: this.targetCollectionRows,
          defaultSort: ["match_score", "desc"],
          detailsIcon: "default",
          rowClick: this.targetCollectionToggle,
        },
        {
          name: "Compound",
          slug: "target_compound",
          cols: [
            {
              field: "target_compound_formula",
              label: "Compound",
              width: "45%",
            },
            { field: "target_compound_name", label: "", width: "45%" },
            {
              field: "match_score",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(
                    row.sample_peak_area_sum
                  ),
                };
              },
            },
          ],
          rows: this.targetCompoundRows,
          defaultSort: ["match_score", "desc"],
          detailsIcon: "default",
          rowClick: doNothing,
        },
        {
          name: "Ion",
          slug: "target_ion",
          cols: [
            { field: "target_ion_formula", label: "Ion", width: "45%" },
            { field: "ionMech", label: "", width: "45%" },
            {
              field: "match_score",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(
                    row.sample_peak_area_sum
                  ),
                };
              },
            },
          ],
          rows: this.targetIonRows,
          defaultSort: ["match_score", "desc"],
          detailsIcon: "default",
          rowClick: doNothing,
        },
        {
          name: "Isotope",
          slug: "target_isotope",
          cols: [
            { field: "mz", label: "Isotope", width: "45%" },
            { field: "relative_abundance", label: "Fraction", width: "45%" },
            {
              field: "match_score",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.sample_peak_area),
                };
              },
            },
          ],
          rows: this.targetIsotopeRows,
          defaultSort: ["mz", "asc"],
          detailsIcon: this.sampleItemFocused ? "chart-bell-curve" : null,
          detailsOpen: this.sampleItemFocused ? this.ionShow : null,
          rowClick: doNothing,
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
      let copySelectedCollectionToOtherBatchesButton = {
        label: "Manage selected collection batches",
        onClick: this.manageSelectedCollectionBatches,
      };
      let editBatchCollectionsButton = {
        label: "Edit collections of selected batch",
        onClick: this.editBatchCollections,
      };
      let rematchBatchesButton = {
        label: "Rematch selected batch (debug)",
        onClick: this.rematchBatches,
      };
      if (
        this.targetCollectionsSelected.length == 0 &&
        this.sampleBatchesSelected.length == 1
      ) {
        return [
          createCollectionButton,
          editBatchCollectionsButton,
          rematchBatchesButton,
        ];
      }
      if (this.targetCollectionsSelected.length == 0) {
        return [createCollectionButton];
      }
      if (this.targetCollectionsSelected.length == 1) {
        return [
          // updateCollectionButton,
          createCollectionButton,
          editBatchCollectionsButton,
          copySelectedCollectionToOtherBatchesButton,
          deleteCollectionButton,
          rematchBatchesButton,
        ];
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
    ...call({
      matchBatchesCompute: "batch/matchBatchesCompute",
      loadSampleIon: "visualization/load",
      targetCollectionToggle: "batch/targetCollectionToggle",
    }),
    manageSelectedCollectionBatches() {
      this.modalTargetCollectionOpProps = {
        action: "manageSelectedCollectionBatches",
        collection: this.targetCollectionsSelected[0],
      };
      this.activateModal({
        modal: "targetCollectionOp",
      });
    },
    async editBatchCollections() {
      this.modalTargetCollectionOpProps = {
        action: "editBatchCollections",
        collection: this.targetCollectionsSelected[0],
      };
      this.activateModal({
        modal: "targetCollectionOp",
      });
    },
    collectionRemoveFromBatch() {
      this.modalTargetCollectionOpProps = {
        action: "removeFromBatch",
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
    async ionShow(row) {
      const activeIon = this.matchIons.filter(
        (ion) => ion.target_ion_id === row.target_ion_id
      )[0];

      await this.loadSampleIon(activeIon);

      this.activateModal({
        modal: "sampleItemTargetIon",
      });
    },
    matchScoreTagClicked(row) {
      if (row.target_compound_id) {
        // Compound or Ion match score tag clicked
        if (!row.target_ion_id) {
          // Compound tag clicked -> fetch corresponding ion id
          // Note: This picks the first matching target ion if there are many
          row = this.matchIons.filter(
            (ion) => ion.target_compound_id === row.target_compound_id
          )[0];
        }
        this.ionShow(row);
      }
    },
    async rematchBatches() {
      await this.matchBatchesCompute(this.sampleBatchesSelected);
    },
  },
};
</script>
