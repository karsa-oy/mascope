<template>
  <the-layout-sidebar>
    <b-tabs type="is-boxed">
      <b-tab-item label="Matches" icon="check-decagram">
        <b-tabs type="is-toggle">
          <b-tab-item label="Compounds">
            <base-table
              :rows="matchCompoundRows"
              :cols="matchCompoundCols"
              :defaultSort="['matchScore', 'desc']"
              :height="tableHeight"
            >
            </base-table>
          </b-tab-item>
          <b-tab-item label="Ions">
            <base-table
              :rows="matchIonRows"
              :cols="matchIonCols"
              :defaultSort="['matchScore', 'desc']"
              :height="tableHeight"
            >
            </base-table>
          </b-tab-item>
          <b-tab-item label="Isotopes">
            <base-table
              :rows="matchIsotopeRows"
              :cols="matchIsotopeCols"
              :defaultSort="['matchScore', 'desc']"
              :height="tableHeight"
            >
            </base-table>
          </b-tab-item>
        </b-tabs>
      </b-tab-item>
      <b-tab-item label="Targets" icon="target">
        <b-tabs type="is-toggle">
          <b-tab-item label="Compounds">
            <base-table
              :rows="targetCompoundRows"
              :cols="targetCompoundCols"
              :height="tableHeight"
            >
            </base-table>
          </b-tab-item>
          <b-tab-item label="Ions">
            <base-table
              :rows="targetIonRows"
              :cols="targetIonCols"
              :height="tableHeight"
            >
            </base-table>
          </b-tab-item>
          <b-tab-item label="Isotopes">
            <base-table
              :rows="targetIsotopeRows"
              :cols="targetIsotopeCols"
              :height="tableHeight"
            >
            </base-table>
          </b-tab-item>
        </b-tabs>
      </b-tab-item>
      <b-tab-item label="Samples" icon="test-tube">
        <base-table
          :rows="sampleItemRows"
          :cols="sampleItemCols"
          :height="tableHeight"
        >
        </base-table>
      </b-tab-item>
    </b-tabs>
    <b-button
      @click="exportSpreadsheet"
      style="position: fixed; right: 5em; bottom: 2em"
      icon-left="content-save"
      type="is-primary"
      rounded
    >
      Export spreadsheet
    </b-button>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import BaseTable from "./BaseTable.vue";

import table from "$lib/table";

export default {
  name: "ThePageDataManagement",
  components: {
    TheLayoutSidebar,
    BaseTable,
  },
  computed: {
    // layout
    tableHeight() {
      return "calc(100vh - 140px)";
    },
    // matches
    matchCompoundRows() {
      return this.$store.getters["match/rating/rows"]({
        level: "compound",
        selected: true,
      });
    },
    matchCompoundCols() {
      return [
        { field: "sampleFilename", label: "Sample filename" },
        { field: "targetName", label: "Compound name" },
        { field: "targetFormula", label: "Compound formula" },
        { field: "samplePeakHeight", label: "Sample peak intensity" },
        { field: "rating", label: "Match rating" },
        { field: "matchScore", label: "Match score" },
        { field: "sampleMethod", label: "Sample method" },
        { field: "sampleProperties", label: "Sample properties" },
      ];
    },
    matchIonRows() {
      return this.$store.getters["match/rating/rows"]({
        level: "ion",
        selected: true,
      });
    },
    matchIonCols() {
      return [
        { field: "sampleFilename", label: "Sample filename" },
        { field: "targetCompoundName", label: "Compound name" },
        { field: "targetCompoundFormula", label: "Compound formula" },
        { field: "targetIonMech", label: "Ionization mechanism" },
        { field: "targetFormula", label: "Ion formula" },
        { field: "samplePeakHeight", label: "Sample peak intensity" },
        { field: "rating", label: "Match rating" },
        { field: "matchScore", label: "Match score" },
        { field: "sampleMethod", label: "Sample method" },
        { field: "sampleProperties", label: "Sample properties" },
      ];
    },
    matchIsotopeRows() {
      return this.$store.getters["match/rating/rows"]({
        level: "isotope",
        selected: true,
      });
    },
    matchIsotopeCols() {
      return [
        { field: "sampleFilename", label: "Sample filename" },
        { field: "targetCompoundName", label: "Compound name" },
        { field: "targetCompoundFormula", label: "Compound formula" },
        { field: "targetIonMech", label: "Ionization mechanism" },
        { field: "targetIonFormula", label: "Ion formula" },
        { field: "targetMz", label: "Isotope m/z" },
        { field: "targetRelAbu", label: "Relative abundance" },
        { field: "samplePeakHeight", label: "Sample peak intensity" },
        { field: "rating", label: "Match rating" },
        { field: "matchScore", label: "Match score" },
        { field: "sampleMethod", label: "Sample method" },
        { field: "sampleProperties", label: "Sample properties" },
      ];
    },
    // targets
    targetCompoundRows() {
      return this.$store.getters["target/stat/rows"]({
        level: "compound",
        selected: true,
      });
    },
    targetCompoundCols() {
      return [
        { field: "name", label: "Compound name" },
        { field: "formula", label: "Compound formula" },
        { field: "matchCompoundProbableCount", label: "Probable match count" },
        { field: "matchCompoundPossibleCount", label: "Possible match count" },
        { field: "matchCompoundTotalCount", label: "Total match count" },
      ];
    },
    targetIonRows() {
      return this.$store.getters["target/stat/rows"]({
        level: "ion",
        selected: true,
      });
    },
    targetIonCols() {
      return [
        { field: "compoundName", label: "Compound name" },
        { field: "compoundFormula", label: "Compound formula" },
        { field: "ionMech", label: "Ionization mechanism" },
        { field: "formula", label: "Ion formula" },
        { field: "matchIonProbableCount", label: "Probable match count" },
        { field: "matchIonPossibleCount", label: "Possible match count" },
        { field: "matchIonTotalCount", label: "Total match count" },
      ];
    },
    targetIsotopeRows() {
      return this.$store.getters["target/stat/rows"]({
        level: "isotope",
        selected: true,
      });
    },
    targetIsotopeCols() {
      return [
        { field: "compoundName", label: "Compound name" },
        { field: "compoundFormula", label: "Compound formula" },
        { field: "ionMech", label: "Ionization mechanism" },
        { field: "ionFormula", label: "Ion formula" },
        { field: "mz", label: "Isotope m/z" },
        { field: "relAbu", label: "Isotope relative abundance" },
        { field: "matchIsotopeProbableCount", label: "Probable match count" },
        { field: "matchIsotopePossibleCount", label: "Possible match count" },
        { field: "matchIsotopeTotalCount", label: "Total match count" },
      ];
    },
    // samples
    sampleItemRows() {
      return this.$store.getters["sample/item/stat/rows"]({
        level: "compound",
        selected: true,
      });
    },
    sampleItemCols() {
      return [
        {
          field: "filename",
          label: "Filename",
        },
        {
          field: "matchCompoundProbableCount",
          label: "Probable compound match count",
        },
        {
          field: "matchCompoundPossibleCount",
          label: "Possible compound match count",
        },
        {
          field: "matchCompoundTotalCount",
          label: "Total peak match count",
        },
      ];
    },
  },
  methods: {
    exportSpreadsheet() {
      table.toSpreadsheet("test.xlsx", [
        {
          name: "Matches (compound)",
          rows: this.matchCompoundRows,
          cols: this.matchCompoundCols,
        },
        {
          name: "Matches (ion)",
          rows: this.matchIonRows,
          cols: this.matchIonCols,
        },
        {
          name: "Matches (isotope)",
          rows: this.matchIsotopeRows,
          cols: this.matchIsotopeCols,
        },
        {
          name: "Targets (compound)",
          rows: this.targetCompoundRows,
          cols: this.targetCompoundCols,
        },
        {
          name: "Targets (ion)",
          rows: this.targetIonRows,
          cols: this.targetIonCols,
        },
        {
          name: "Targets (isotope)",
          rows: this.targetIsotopeRows,
          cols: this.targetIsotopeCols,
        },
        {
          name: "Sample items",
          rows: this.sampleItemRows,
          cols: this.sampleItemCols,
        },
      ]);
    },
  },
};
</script>