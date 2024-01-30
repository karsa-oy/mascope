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
      if (!this.sampleItemFocused || !this.matchIons) {
        return this.targetIons;
      }
      return this.targetIons.map((targetIon) => {
        const matchIon = this.matchIons.find(
          (mi) => mi.target_ion_id === targetIon.target_ion_id
        );

        return matchIon ? { ...targetIon, ...matchIon } : targetIon;
      });
    },
    targetIsotopeRows: function () {
      if (!this.sampleItemFocused || !this.matchIsotopes) {
        return this.targetIsotopes;
      }

      const matchIsotopeIds = new Set(
        this.matchIsotopes.map((mi) => mi.target_isotope_id)
      );

      return this.targetIsotopes
        .filter(({ target_isotope_id }) =>
          matchIsotopeIds.has(target_isotope_id)
        )
        .map((targetIsotope) => {
          const matchIsotope = this.matchIsotopes.find(
            (mis) => mis.target_isotope_id === targetIsotope.target_isotope_id
          );

          return matchIsotope
            ? { ...targetIsotope, ...matchIsotope }
            : targetIsotope;
        });
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
          detailsOpen: this.sampleItemFocused
            ? this.matchScoreTagClicked
            : null,
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
          createCollectionButton,
          editBatchCollectionsButton,
          rematchBatchesButton,
          updateCollectionButton,
          copySelectedCollectionToOtherBatchesButton,
          deleteCollectionButton,
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
      matchBatchesRematch: "batch/matchBatchesRematch",
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
    async ionShow({ ionId, collectionId }) {
      const sampleId = this.sampleItemFocused.sample_item_id;

      // pass the ion specific filter params if acvailable to the loadSampleIon function
      const filterParams =
        this.matchIons.filter((ion) => ion.target_ion_id === ionId)[0]
          ?.filter_params[this.sampleItemFocused.instrument] || null;

      await this.loadSampleIon({ sampleId, ionId, collectionId, filterParams });

      this.activateModal({
        modal: "sampleItemTargetIon",
      });
    },
    matchScoreTagClicked(row) {
      const ionId =
        // Ion or isotope tag clicked
        row?.target_ion_id ??
        // Compound tag clicked -> fetch corresponding ion id
        this?.matchIons.filter(
          (ion) => ion.target_compound_id === row.target_compound_id
        )[0]?.target_ion_id ??
        // Collection tag clicked
        null;
      if (!ionId) return;
      const collectionId = row?.target_collection_id;
      this.ionShow({ ionId, collectionId });
    },
    async rematchBatches() {
      await this.matchBatchesRematch(this.sampleBatchesSelected);
    },
  },
};
</script>
