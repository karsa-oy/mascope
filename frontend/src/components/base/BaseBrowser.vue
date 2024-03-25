<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import BaseTagMatch from './BaseTagMatch.vue'

import { cloneDeep } from 'lodash'

const noop = () => ({})

const props = defineProps({
  contextMenuIcon: {
    type: String,
    default: 'dots-horizontal'
  },
  name: {
    type: String,
    default: null
  },
  levels: {
    type: Array,
    required: true
  },
  menu: {
    type: Array
  },
  // for recursion - don't use externally
  isRoot: {
    type: Boolean,
    default: true
  },
  rootRefresh: {
    type: Function
  }
})

const emit = defineEmits(['tagClicked'])

// reactivity

const table = ref(null)

const currentLevel = computed(() => props.levels[0])
const slug = computed(() => currentLevel.value.slug)
const rows = computed(() => currentLevel.value.rows)
const cols = computed(() => currentLevel.value.cols)
const showHeader = computed(() => currentLevel.value.showHeader ?? true)
const defaultSort = computed(() => currentLevel.value.defaultSort ?? null)
const detailsIcon = computed(() => {
  let icon
  switch (currentLevel.value.detailsIcon) {
    case 'default':
      icon = 'chevron-right'
      break
    case null:
      icon = ''
      break
    default:
      icon = currentLevel.value.detailsIcon
      break
  }
  return icon
})
const detailsOpen = computed(() => {
  if (!currentLevel.value.detailsOpen) return noop
  let handleDetailsOpen = (row) => {
    currentLevel.value.detailsOpen(row)
    refresh()
  }
  return handleDetailsOpen
})
const rowClick = computed(() => {
  let handleClick = (row) => {
    currentLevel.value.rowClick(row)
    refresh()
  }
  return handleClick ?? noop
})
const opened = computed(() => currentLevel.value.opened ?? null)
const minPrecision = computed(() => currentLevel.value.minPrecision ?? 1)
const maxPrecision = computed(() => currentLevel.value.maxPrecision ?? 3)
const formatter = computed(
  () =>
    new Intl.NumberFormat('en-US', {
      minimumFractionDigits: minPrecision.value,
      maximumFractionDigits: maxPrecision.value
    })
)

watch(currentLevel, () => {
  console.dir(currentLevel.value)
})

function getChildLevels(...parentRows) {
  // TODO: Currently only looks one level up for parent id.
  // Should check all levels (e.g. target_ion_id -> target_compound_id -> target_collection_id)

  // FAQ: parentRow and childRow should have the target_collection_id.
  // Both parentIdField and parentCollectionId are used for childRow to be correcly assigned to the right collection and to avoid dublicates.
  // If the parentRow do not have the target_collection_id (undefined) then childRow will assigned only by parentIdField.

  let childLevels = []
  // init iteration parameters
  let currLevel = cloneDeep(currentLevel.value)
  currLevel.rows = cloneDeep(parentRows)
  let nextLevels = cloneDeep(props.levels).splice(1)

  while (nextLevels.length > 0) {
    const parentIdField = `${currLevel.slug}_id`
    const parentIds = currLevel.rows.map((row) => row[parentIdField])
    // set the parentCollectionId if available
    const parentCollectionId = parentRows[0]?.target_collection_id ?? undefined

    let childLevel = nextLevels.shift()
    if (childLevel.rows && childLevel.rows.length > 0) {
      childLevel.rows = childLevel.rows.filter(
        (childRow) =>
          parentIds.includes(childRow[parentIdField]) &&
          // check if the childRow is assigned to the same collection as the parentRow.This condition is ignored if parentCollectionId is undefined
          (parentCollectionId === undefined || childRow.target_collection_id === parentCollectionId)
      )
      // push results
      childLevels.push(childLevel)
      // update iteration parameters
      currLevel = childLevel
    } else {
      break
    }
  }
  return childLevels
}
function parseValue(value) {
  let isNumeric = typeof value == 'number'
  return isNumeric ? formatter.value.format(value) : value
}
function dynamic(className) {
  if (props.isRoot) {
    return `${className}-root`
  } else {
    return `${className}-other`
  }
}
function matchScoreTagClicked(row) {
  emit('tagClicked', row)
}
function rowClass(row) {
  switch (row.selection) {
    case 3:
      return 'base-browser-row-focused'
    case 2:
      return 'base-browser-row-fully-selected'
    case 1:
      return 'base-browser-row-partially-selected'
    case 0:
      return ''
  }
}
function refresh() {
  if (props.isRoot) {
    //forceUpdate()
  } else {
    props.rootRefresh()
  }
}
function open(row) {
  table.value?.openDetailRow(row)
}
function close(row) {
  table.value?.closeDetailRow(row)
}

watch(opened, (openedRows) => {
  if (openedRows) {
    nextTick(() => {
      rows.value.forEach((row) => {
        if (openedRows.includes(row)) {
          open(row)
        } else {
          close(row)
        }
      })
    })
  }
})
</script>

<template>
  <section :class="dynamic('base-browser-container')">
    <section :class="dynamic('base-browser-header')">
      <h2>{{ name }}</h2>
      <slot name="header"></slot>
      <b-dropdown v-if="menu" aria-role="list" position="is-bottom-left">
        <template #trigger>
          <b-button :icon-left="contextMenuIcon" size="is-small" />
        </template>
        <template v-for="item of menu" :key="item.label">
          <b-dropdown-item aria-role="listitem" @click="item.onClick">
            {{ item.label }}
          </b-dropdown-item>
        </template>
      </b-dropdown>
    </section>
    <section :class="dynamic('base-browser-content')">
      <b-table
        v-if="rows.length > 0"
        ref="table"
        :data="rows"
        narrowed
        hoverable
        detailed
        :default-sort="defaultSort"
        custom-detail-row
        :detail-key="slug + '_id'"
        :detail-icon="detailsIcon"
        :opened-details="opened"
        :show-header="showHeader"
        :row-class="rowClass"
        @click="rowClick"
        @details-open="detailsOpen"
      >
        <b-table-column
          v-for="col in cols"
          v-slot="props"
          :key="col.field"
          :field="col.field"
          :label="col.label"
          :width="col.width"
          sortable
          :visible="!col.hidden"
          left
        >
          <template v-if="col.field == 'match_score'">
            <base-tag-match
              :display-match-score="col.displayMatchScore"
              :row="props.row"
              :tooltip="col.tooltip ? col.tooltip(props.row) : {}"
              @tagClicked="matchScoreTagClicked"
            ></base-tag-match>
          </template>
          <template v-else>
            {{ parseValue(props.row[col.field]) }}
          </template>
        </b-table-column>
        <template v-if="levels.length > 1" v-slot:detail="props">
          <tr>
            <td :colspan="cols.length + 1">
              <BaseBrowser
                v-if="getChildLevels(props.row).length > 0"
                :levels="getChildLevels(props.row)"
                :isRoot="false"
                :rootRefresh="refresh"
                @tagClicked="matchScoreTagClicked"
              >
              </BaseBrowser>
            </td>
          </tr>
        </template>
      </b-table>
    </section>
    <section :class="dynamic('base-browser-footer')">
      <slot name="footer"></slot>
    </section>
  </section>
</template>

<style>
.base-browser-container-root {
  flex: 1 1 50% !important;
  display: flex !important;
  flex-direction: column !important;
  min-height: 100px;
  max-height: 50vh;
}

.base-browser-container-other {
  flex: 1 1 min-content !important;
}

.base-browser-header-root {
  padding: 0.5em 0em;
  display: flex !important;
  flex-direction: flow !important;
  justify-content: space-between;
}

.base-browser-content-root {
  min-height: 10px;
  flex: 1;
  overflow-y: auto;
}

.base-browser-footer-root {
  display: flex;
  padding: 0.5em;
  flex-flow: row-reverse nowrap;
}

.base-browser-header-other {
  display: none;
}

.base-browser-footer-other {
  display: none;
}

.icon > .mdi-chevron-right,
.mdi-chevron-down {
  color: white !important;
}
</style>
