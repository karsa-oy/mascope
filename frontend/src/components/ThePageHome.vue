<template>
  <the-layout-sidebar>
    <section style="padding: 1em 0em 2em 0em">
      <h1 class="title is-3">Karsa Mascope</h1>
    </section>
    <div class="columns">
      <div class="column is-half">
        <template v-if="!workspaceSelected">
          <section style="padding: 1em 0em 2em 0em">
            <h1 class="title is-4">Workspaces:</h1>
          </section>
          <section class="base-tile-container">
            <base-workspace-tile
              v-for="workspace in workspaces"
              :key="workspace.id"
              :workspace="workspace"
            ></base-workspace-tile>
          </section>
          <section style="padding: 0.5em">
            <b-button
              type="is-primary"
              style="position: fixed; left: 5em; bottom: 2em"
              @click="
                () => {
                  modalProps = {
                    action: 'create',
                  };
                  activateModal({
                    modal: 'workspaceSave',
                  });
                }
              "
            >
              Create workspace
            </b-button>
          </section>
        </template>
        <template v-else>
          <section style="padding: 2em 2em 2em 2em">
            <h1 class="title is-3">{{ workspaceHomeText }}</h1>
          </section>
        </template>
      </div>
      <div class="column is-half">
        <section style="padding: 1em 0em 2em 0em">
          <h1 class="title is-4">Recent acquisitions:</h1>
        </section>
        <section>
          <b-button type="is-primary" @click="getRecentAcquisitions">
            <b-icon icon="reload"></b-icon>
          </b-button>
        </section>
        <base-table
          :key="sampleFileTableDataKey"
          :rows="sampleFileRows"
          :cols="sampleFileCols"
          :checkable="false"
          :searchable="true"
          :height="sampleFileTableHeight"
        >
        </base-table>
        <section style="padding: 0.5em">
          <b-button
            type="is-primary"
            style="position: fixed; right: 5em; bottom: 2em"
            @click="
              () => {
                modalProps = {
                  action: 'create',
                };
                activateModal({
                  modal: 'sampleFileAttributesSave',
                });
              }
            "
          >
            Save Sample File Attributes
          </b-button>
        </section>
      </div>
    </div>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import BaseTable from "./BaseTable.vue";
import BaseWorkspaceTile from "./BaseWorkspaceTile.vue";

import { bindState } from "$lib/store";

import { mapActions, mapMutations, mapGetters } from "vuex";

export default {
  name: "ThePageHome",
  components: {
    BaseTable,
    BaseWorkspaceTile,
    TheLayoutSidebar,
  },
  data: function () {
    return {
      sampleFileTableDataKey: 0,
    };
  },
  computed: {
    ...bindState({
      workspaces: "workspace/rows",
      modalProps: "modal/workspaceSaveProps",
      sampleFileRows: "sample/file/rows",
      sampleFileSchema: "sample/file/schema/row",
    }),
    ...mapGetters({
      workspaceSelected: "workspace/selectedRow",
    }),
    sampleFileCols() {
      let result = [];
      if (!this.sampleFileSchema) return result;
      this.sampleFileSchema.forEach((el) => {
        if (el !== "id") result.push({ field: el, label: el });
      });
      return result;
    },
    sampleFileTableHeight() {
      return "calc(75vh)";
    },
    workspaceHomeText() {
      if (this.workspaceSelected) {
        return `Welcome to workspace ${this.workspaceSelected.name}!`;
      } else {
        return `Loading workspace...`;
      }
    },
  },
  created: function () {
    this.getRecentAcquisitions();
  },
  methods: {
    ...mapActions({
      listSampleFiles: "sample/file/listFiles",
    }),
    ...mapMutations({
      activateModal: "modal/activate",
    }),
    getRecentAcquisitions() {
      let d1 = new Date();
      d1.setHours(0, 0, 0, 0);
      this.listSampleFiles({
        filters: {
          column: "datetime_utc",
          min_value: d1.toISOString(),
          max_value: new Date().toISOString(),
        },
      });
    },
  },
};
</script>

<style scoped>
.base-home-page {
  display: flex;
  flex-flow: column nowrap;
  min-height: 100vh;
  max-width: 1190px;
  padding: 2em;
}

.base-tile-container {
  flex: 1;
  display: flex;
  flex-flow: row wrap;
  justify-content: flex-start;
  align-content: flex-start;
  gap: 10px 10px;
}
</style>
