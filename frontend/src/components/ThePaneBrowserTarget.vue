<template>
  <section>
    <base-browser
      name="Targets"
      :levels="targetLevels"
      :menu="menu"
      :contextMenuIcon="contextMenuIcon"
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
      modalSampleItemTargetIonProps: "modal/sampleItemTargetIonProps",
      modalTargetCollectionOpProps: "modal/targetCollectionOpProps",
    }),
    ...get({
      batchActive: "batch/active",
      matchCollections: "sample/matchCollections",
      matchCompounds: "sample/matchCompounds",
      matchIons: "sample/matchIons",
      matchIsotopes: "sample/matchIsotopes",
      mzTolerance: "batch/paramMzTolerance",
      minIsotopeAbundance: "batch/paramMinIsotopeAbundance",
      peakMinIntensity: "batch/paramPeakMinIntensity",
      sampleItemFocused: "sample/active",
      targetCollections: "batch/targetCollections",
      targetCollectionsSelected: "batch/targetCollectionsSelected",
      targetCompounds: "batch/targetCompounds",
      targetIons: "batch/targetIons",
      targetIsotopes: "batch/targetIsotopes",
    }),
    contextMenuIcon() {
      return this.targetCollectionsSelected.length == 1
        ? "dots-horizontal"
        : "plus"
    },
    targetCollectionRows: function() {
      return this.sampleItemFocused && this.matchCollections
      ? this.matchCollections
      : this.targetCollections;
    },
    targetCompoundRows: function() {
      return this.sampleItemFocused && this.matchCompounds
      ? this.matchCompounds
      : this.targetCompounds;

    },
    targetIonRows: function() {
      return this.sampleItemFocused && this.matchIons
      ? this.matchIons
      : this.targetIons;
    },
    targetIsotopeRows: function() {
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
            { field: "target_collection_name", label: "Collection", width: "30%" },
            { field: "target_collection_description", label: "Description", width: "60%" },
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
          rowClick: doNothing,
        },
        {
          name: "Compound",
          slug: "target_compound",
          cols: [
            { field: "target_compound_formula", label: "Compound", width: "45%" },
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
                  "Peak intensity": this.formatter.format(
                    row.sample_peak_area
                  ),
                };
              },
            },
          ],
          rows: this.targetIsotopeRows,
          defaultSort: ["mz", "asc"],
          detailsIcon: this.sampleItemFocused ? "magnify" : null,
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
      let addCollectionToBatchButton = {
        label: "Add target collection to batch",
        onClick: this.collectionAddToBatch,
      };
      if (this.targetCollectionsSelected.length == 1) {
        return [
          addCollectionToBatchButton,
          createCollectionButton,
          // updateCollectionButton,
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
    ...call({
      resetIonVisualization: "visualization/reset",
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
    ionShow(row) {
      this.resetIonVisualization();
      this.$api.emit(
        'visualization_ion_focus',
        this.sampleItemFocused.sample_item_id,
        row.target_ion_id,
        this.minIsotopeAbundance,
        this.peakMinIntensity,
        this.mzTolerance,
        )
      const targetIon = this.targetIons.filter(
        (ion) => ion.target_ion_id == row.target_ion_id
        )[0];
      this.modalSampleItemTargetIonProps = {
        ...row,
        target_ion_formula: targetIon.target_ion_formula
        };
      this.activateModal({
        modal: "sampleItemTargetIon",
      });
    },
  },
};
</script>