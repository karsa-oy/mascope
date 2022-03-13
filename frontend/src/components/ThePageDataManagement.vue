<template>
  <the-layout-sidebar>
    <b-tabs>
      <b-tab-item label="Matches" icon="check-decagram">
        <b-tabs>
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
        <b-tabs>
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
import TheLayoutSidebar from "./TheLayoutSidebar";
import BaseTable from "./BaseTable";

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
      return this.$store.getters["match/ratings"]({
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
      return this.$store.getters["match/ratings"]({
        level: "ion",
        selected: true,
      });
    },
    matchIonCols() {
      return [
        { field: "sampleFilename", label: "Sample filename" },
        { field: "targetFormula", label: "Ion formula" },
        { field: "targetIonMech", label: "Ionization mechanism" },
        { field: "samplePeakHeight", label: "Sample peak intensity" },
        { field: "rating", label: "Match rating" },
        { field: "matchScore", label: "Match score" },
        { field: "sampleMethod", label: "Sample method" },
        { field: "sampleProperties", label: "Sample properties" },
      ];
    },
    matchIsotopeRows() {
      return this.$store.getters["match/ratings"]({
        level: "isotope",
        selected: true,
      });
    },
    matchIsotopeCols() {
      return [
        { field: "sampleFilename", label: "Sample filename" },
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
      return this.$store.getters["target/stats"]({
        level: "compound",
        selected: true,
      });
    },
    targetCompoundCols() {
      return [
        { field: "name", label: "Compound name" },
        { field: "formula", label: "Compound formula" },
        { field: "matchCompoundTotalCount", label: "Total match count" },
        { field: "matchCompoundProbableCount", label: "Probable match count" },
        { field: "matchCompoundPossibleCount", label: "Possible match count" },
      ];
    },
    targetIonRows() {
      return this.$store.getters["target/stats"]({
        level: "ion",
        selected: true,
      });
    },
    targetIonCols() {
      return [
        { field: "formula", label: "Compound formula" },
        { field: "ionMech", label: "Compound name" },
        { field: "matchIonTotalCount", label: "Total match count" },
        { field: "matchIonProbableCount", label: "Probable match count" },
        { field: "matchIonPossibleCount", label: "Possible match count" },
      ];
    },
    targetIsotopeRows() {
      return this.$store.getters["target/stats"]({
        level: "isotope",
        selected: true,
      });
    },
    targetIsotopeCols() {
      return [
        { field: "mz", label: "Isotope m/z" },
        { field: "relAbu", label: "Isotope relative abundance" },
        { field: "matchIsotopeTotalCount", label: "Total match count" },
        { field: "matchIsotopeProbableCount", label: "Probable match count" },
        { field: "matchIsotopePossibleCount", label: "Possible match count" },
      ];
    },
    // samples
    sampleItemRows() {
      return this.$store.getters["sample/itemStats"]({
        level: "compound",
        selected: true,
      });
    },
    sampleItemCols() {
      return [
        { field: "filename", label: "Filename" },
        { field: "matchCompoundTotalCount", label: "Total peak match count" },
        {
          field: "matchCompoundProbableCount",
          label: "Probable compound match count",
        },
        {
          field: "matchCompoundPossibleCount",
          label: "Possible compound match count",
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