<template>
  <section :class="dynamic('base-browser-container')">
    <section :class="dynamic('base-browser-header')">
      <h2>{{ name }}</h2>
      <slot name="header"></slot>
      <b-dropdown v-if="menu" aria-role="list" position="is-bottom-left">
        <template #trigger>
          <b-button :icon-left="contextMenuIcon" size="is-small" />
        </template>
        <template v-for="item of menu">
          <b-dropdown-item
            aria-role="listitem"
            :key="item.label"
            @click="item.onClick"
          >
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
              :match-score="
                props.row.matched === undefined || props.row.matched
                  ? props.row[col.field]
                  : null
              "
              :tooltip="col.tooltip ? col.tooltip(props.row) : {}"
            ></base-tag-match>
          </template>
          <template v-else>
            {{ parseValue(props.row[col.field]) }}
          </template>
        </b-table-column>
        <template v-if="levels.length > 1" slot="detail" slot-scope="props">
          <tr>
            <td :colspan="cols.length + 1">
              <base-browser
                v-if="getChildLevels(props.row).length > 0"
                :levels="getChildLevels(props.row)"
                :isRoot="false"
                :rootRefresh="refresh"
              >
              </base-browser>
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

<script>
import BaseTagMatch from "./BaseTagMatch.vue";

import { cloneDeep } from "lodash";

let doNothing = () => ({});

export default {
  name: "BaseBrowser",
  components: {
    BaseBrowser: () => import("./BaseBrowser.vue"),
    BaseTagMatch,
  },
  props: {
    contextMenuIcon: {
      type: String,
      required: false,
      default: "dots-horizontal",
    },
    name: {
      type: String,
      required: false,
      default: null,
    },
    levels: {
      type: Array,
      required: true,
    },
    menu: {
      type: Array,
      required: false,
    },
    // recursion props
    // don't use these externally
    isRoot: {
      type: Boolean,
      required: false,
      default: true,
    },
    rootRefresh: {
      type: Function,
      required: false,
    },
  },
  created: function () {
    this.formatter = new Intl.NumberFormat("en-US", {
      minimumFractionDigits: this.minPrecision,
      maximumFractionDigits: this.maxPrecision,
    });
  },
  computed: {
    currentLevel: function () {
      return this.levels[0];
    },
    slug: function () {
      return this.currentLevel.slug;
    },
    levelName: function () {
      return this.currentLevel[this.currentLevel.slug + "_name"];
    },
    rows: function () {
      return this.currentLevel.rows;
    },
    cols: function () {
      return this.currentLevel.cols;
    },
    showHeader: function () {
      return this.currentLevel.showHeader ?? true;
    },
    defaultSort: function () {
      return this.currentLevel.defaultSort ?? null;
    },
    detailsIcon: function () {
      let icon;
      switch (this.currentLevel.detailsIcon) {
        case "default":
          icon = "chevron-right";
          break;
        case null:
          icon = "";
          break;
        default:
          icon = this.currentLevel.detailsIcon;
          break;
      }
      return icon;
    },
    detailsOpen: function () {
      if (!this.currentLevel.detailsOpen) return doNothing;
      let handleDetailsOpen = (row) => {
        this.currentLevel.detailsOpen(row);
        this.refresh();
      };
      return handleDetailsOpen;
    },
    rowClick: function () {
      let handleClick = (row) => {
        this.currentLevel.rowClick(row);
        this.refresh();
      };
      return handleClick ?? doNothing;
    },
    opened: function () {
      return this.currentLevel.opened ?? null;
    },
    minPrecision: function () {
      return this.currentLevel.minPrecision ?? 1;
    },
    maxPrecision: function () {
      return this.currentLevel.maxPrecision ?? 3;
    },
  },
  methods: {
    getChildLevels: function (...parentRows) {
      // TODO: Currently only looks one level up for parent id.
      // Should check all levels (e.g. target_ion_id -> target_compound_id -> target_collection_id)

      let childLevels = [];
      // init iteration parameters
      let currentLevel = cloneDeep(this.currentLevel);
      currentLevel.rows = cloneDeep(parentRows);
      let nextLevels = cloneDeep(this.levels).splice(1);
      // loop through next levels, removing as we go
      while (nextLevels.length > 0) {
        let parentIdField = currentLevel.slug + "_id";
        let parentIds = currentLevel.rows.map((row) => row[parentIdField]);
        let childLevel = nextLevels.shift();
        if (childLevel.rows && childLevel.rows.length > 0) {
          childLevel.rows = childLevel.rows.filter((childRow) =>
            parentIds.includes(childRow[parentIdField])
          );
          // push results
          childLevels.push(childLevel);
          // update iteration parameters
          currentLevel = childLevel;
        } else {
          break;
        }
      }
      return childLevels;
    },
    parseValue: function (value) {
      let isNumeric = typeof value == "number";
      return isNumeric ? this.formatter.format(value) : value;
    },
    dynamic: function (className) {
      if (this.isRoot) {
        return `${className}-root`;
      } else {
        return `${className}-other`;
      }
    },
    rowClass: function (row) {
      switch (row.selection) {
        case 3:
          return "base-browser-row-focused";
        case 2:
          return "base-browser-row-fully-selected";
        case 1:
          return "base-browser-row-partially-selected";
        case 0:
          return "";
      }
    },
    refresh: function () {
      if (this.isRoot) {
        this.$forceUpdate();
      } else {
        this.rootRefresh();
      }
    },
    open: function (row) {
      this.$refs.table.openDetailRow(row);
    },
    close: function (row) {
      this.$refs.table.closeDetailRow(row);
    },
  },
  watch: {
    opened: function (openedRows) {
      if (this.opened) {
        this.$nextTick(() => {
          this.rows.forEach((row) => {
            if (openedRows.includes(row)) {
              this.open(row);
            } else {
              this.close(row);
            }
          });
        });
      }
    },
  },
};
</script>

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

.base-browser-row-focused {
  background: #a5690e;
}

.base-browser-row-fully-selected {
  background: #4c7799;
}

.base-browser-row-partially-selected {
  background: #496275;
}

.icon > .mdi-chevron-right,
.mdi-chevron-down {
  color: rgb(255, 255, 255) !important;
}
</style>
