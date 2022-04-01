<template>
  <b-table
    v-if="rows.length > 0"
    :data="rows"
    narrowed
    hoverable
    :default-sort="defaultSort"
    show-header
    sticky-header
    :height="height"
    :checkable="checkable"
    :checked-rows.sync="selected"
  >
    <b-table-column
      v-for="col in cols"
      v-slot="props"
      :key="col.field"
      :field="col.field"
      :label="col.label"
      :width="col.width"
      :searchable="searchable"
      sortable
      left
    >
      {{ parseValue(props.row[col.field]) }}
    </b-table-column>
  </b-table>
</template>

<script>
export default {
  name: "BaseTable",
  components: {},
  props: {
    cols: {
      type: Array,
      required: true,
    },
    rows: {
      type: Array,
      required: true,
    },
    defaultSort: {
      type: Array,
      required: false,
      default: null,
    },
    height: {
      type: String,
      required: false,
      default: "100%",
    },
    checkable: {
      type: Boolean,
      required: false,
      default: false,
    },
    searchable: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  data() {
    return {
      selected: [],
    }
  },
  created: function () {
    this.formatter = new Intl.NumberFormat("en-US", {
      minimumFractionDigits: this.minPrecision,
      maximumFractionDigits: this.maxPrecision,
    });
  },
  methods: {
    parseValue: function (value) {
      let isNumeric = typeof value == "number";
      return isNumeric ? this.formatter.format(value) : value;
    },
  },
  watch: {
    selected(rows) {
      this.$emit("selectRows", rows);
    },
  },
};
</script>

<style>
.b-table .table-wrapper.has-sticky-header tr:first-child th {
  background-color: #2b3e50 !important;
}
</style>