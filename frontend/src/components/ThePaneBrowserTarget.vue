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
      // matchesExist: "match/exists",
      // sampleItemFocused: "sample/item/focusedRow",
      targetCollections: "batch/targetCollections",
      targetCompounds: "batch/targetCompounds",
      targetIons: "batch/targetIons",
      targetIsotopes: "batch/targetIsotopes",
      // targetCollectionsSelected: "target/collection/selectedRows",
      // uniqueTargetCollection: "target/collection/uniqueRow",
    }),
    targetLevels: function () {
      let hidden = !(this.matchesExist && this.sampleItemFocused);
      return [
        {
          name: "Collection",
          slug: "target_collection",
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
          rows: this.targetCollections,
          defaultSort: ["matchScore", "desc"],
          detailsIcon: "default",
          rowClick: this.targetCollectionToggle,
        },
        {
          name: "Compound",
          slug: "target_compound",
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
          rows: this.targetCompounds,
          defaultSort: ["matchScore", "desc"],
          detailsIcon: "default",
          rowClick: this.targetCompoundToggle,
        },
        {
          name: "Ion",
          slug: "target_ion",
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
          rows: this.targetIons,
          defaultSort: ["matchScore", "desc"],
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
          rows: this.targetIsotopes,
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