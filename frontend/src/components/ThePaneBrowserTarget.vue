<template>
  <section>
    <base-browser name="Targets" :levels="targetLevels" :menu="menu">
    </base-browser>
  </section>
</template>

<script>
import { mapMutations } from "vuex";
import { sync, get, call } from "vuex-pathify";

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
    ...sync({
      modalTargetCollectionOpProps: "modal/targetCollectionOpProps",
    }),
    ...get({
      batchActive: "batch/active",
      matchCompounds: "batch/matchCompounds",
      matchIons: "batch/matchIons",
      sampleItemFocused: "batch/sampleItemFocused",
      targetCollections: "batch/targetCollections",
      targetCollectionsSelected: "batch/targetCollectionsSelected",
      targetCompounds: "batch/targetCompounds",
      targetIons: "batch/targetIons",
      targetIsotopes: "batch/targetIsotopes",
    }),
    targetCollectionRows: function() {
      return this.targetCollections;
    },
    targetCompoundRows: function() {
      return this.targetCompounds;
    },
    targetIonRows: function() {
      return this.targetIons;
    },
    targetIsotopeRows: function() {
      return this.targetIsotopes;
    },
    targetLevels: function () {
      let hidden = true;
      return [
        {
          name: "Collection",
          slug: "target_collection",
          cols: [
            { field: "target_collection_name", label: "Collection", width: "90%" },
            {
              field: "match_score",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.sample_peak_height_sum),
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
            { field: "target_compound_formula", label: "Compound", width: "45%" },
            { field: "target_compound_name", label: "", width: "45%" },
            {
              field: "match_score",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.sample_peak_height_sum),
                };
              },
            },
          ],
          rows: this.targetCompoundRows,
          defaultSort: ["match_score", "desc"],
          detailsIcon: "default",
          rowClick: this.targetCompoundToggle,
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
                  "Peak intensity": this.formatter.format(row.sample_peak_height_sum),
                };
              },
            },
          ],
          rows: this.targetIonRows,
          defaultSort: ["match_score", "desc"],
          detailsIcon: "default",
          rowClick: this.targetIonToggle,
        },
        {
          name: "Isotope",
          slug: "target_isotope",
          cols: [
            { field: "mz", label: "Isotope", width: "45%" },
            { field: "relativeAbundance", label: "", width: "45%" },
            {
              field: "match_score",
              label: "Score",
              width: "10%",
              hidden,
              tooltip: (row) => {
                return {
                  "Peak intensity": this.formatter.format(row.sample_peak_height_sum),
                  "Rel. abundance": this.formatter.format(
                    row.relative_abundance
                  ),
                };
              },
            },
          ],
          rows: this.targetIsotopeRows,
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
      targetCollectionToggle: "batch/targetCollectionToggle",
      targetCompoundToggle: "batch/targetCompoundToggle",
      targetIonToggle: "batch/targetIonToggle",
      targetIsotopeToggle: "batch/targetIsotopeToggle",
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
};
</script>