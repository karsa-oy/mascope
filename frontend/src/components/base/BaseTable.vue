<script setup>
  import { ref, watch } from 'vue';

  const props = defineProps({
    checkable: {
      type: Boolean,
      required: false,
      default: false,
    },
    checkSingle: {
      type: Boolean,
      required: false,
      default: false,
    },
    cols: {
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
      default: '100%',
    },
    maxPrecision: {
      type: Number,
      required: false,
      default: 2,
    },
    minPrecision: {
      type: Number,
      required: false,
      default: 2,
    },
    rows: {
      type: Array,
      required: true,
    },
    searchable: {
      type: Boolean,
      required: false,
      default: false,
    },
    sortable: {
      type: Boolean,
      required: false,
      default: true,
    },
  })

  const emit = defineEmits(['selectRows'])
  const selected = ref([])

  const formatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: props.minPrecision,
    maximumFractionDigits: props.maxPrecision,
  })

  function parseValue(value) {
    let isNumeric = typeof value == 'number'
    return isNumeric ? formatter.format(value) : value
  }

  watch(props.rows, () => {
    selected.value = []
  })
  watch(selected, (newRows, oldRows) => {
    if (props.checkSingle && newRows.length > 1) {
      selected.value = newRows.filter((row) => !oldRows.includes(row))
      return
    }
    emit('selectRows', newRows, oldRows)
  })
</script>

<template>
  <b-table v-if="rows.length > 0" :data="rows" narrowed hoverable :default-sort="defaultSort" show-header sticky-header
    :height="height" :header-checkable="checkable && !checkSingle" :checkable="checkable"
    v-bind:checked-rows="selected">
    <b-table-column v-for="col in cols" v-slot="props" :key="col.field" :field="col.field" :label="col.label"
      :width="col.width" :subheading="col.subheading" :searchable="searchable" :sortable="sortable" left>
      {{ parseValue(props.row[col.field]) }}
    </b-table-column>
  </b-table>
</template>