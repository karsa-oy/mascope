<template>
  <section>
    <the-layout-sidebar>
      <section style="padding: 1em 0em 2em 0em">
        <h1 class="title is-3">Karsa Mascope</h1>
      </section>
      <div class="columns">
        <div class="column is-half">
          <section style="padding: 2em 2em 2em 2em">
            <h1 class="title is-4">Instruments:</h1>
          </section>
          <b-field label="Select instrument to monitor">
            <base-table
              :rows="instruments"
              :cols="[{ field: 'instrument', label: 'Instrument' }]"
              :checkable="true"
              :checkSingle="true"
              @selectRows="selectInstruments"
            >
            </base-table>
          </b-field>
          <div v-if="instrumentActive">
            <section style="padding: 2em 2em 2em 2em">
              <h1 class="title is-4">Recent acquisitions:</h1>
            </section>
            <section>
              <b-button type="is-primary" @click=";">
                <b-icon icon="reload"></b-icon>
              </b-button>
            </section>
            <base-table
              :key="sampleFileTableDataKey"
              :rows="recentAcquisitions ? recentAcquisitions : []"
              :cols="sampleFileCols ? sampleFileCols : []"
              :checkable="true"
              :checkSingle="true"
              @selectRows="selectSampleFiles"
              :searchable="true"
              :height="sampleFileTableHeight"
            >
            </base-table>
            <section style="padding: 0.5em">
              <b-button
                type="is-primary"
                style="position: fixed; left: 5em; bottom: 2em"
                :disabled="!workspaceActive || !batchToAddTo || sampleFilesSelected.length != 1"
                @click="
                  () => {
                    sampleItemAttributesSaveProps = {
                      action: 'create',
                      batchToAddTo: batchToAddTo,
                      sampleItemRecordToLoad: sampleFilesSelected[0],
                    };
                    activateModal({
                      modal: 'sampleItemAttributesSave',
                    });
                  }
                "
              >
                Process
              </b-button>
            </section>
          </div>
        </div>
        <div class="column is-half">
          <template v-if="!workspaceActive">
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
                style="position: fixed; right: 5em; bottom: 2em"
                @click="
                  () => {
                    workspaceModalProps = {
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
              <h1 class="title is-4">{{ workspaceHomeText }}</h1>
            </section>
            <b-field label="Sample batches">
              <base-table
                :rows="sampleBatches"
                :cols="[{ field: 'name', label: 'Batch' }]"
                :checkable="true"
                :checkSingle="true"
                @selectRows="selectBatchToAddTo"
              >
              </base-table>
            </b-field>
          </template>
        </div>
      </div>
    </the-layout-sidebar>
  </section>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import BaseTable from "./BaseTable.vue";
import BaseWorkspaceTile from "./BaseWorkspaceTile.vue";

import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";

export default {
  name: "ThePageHome",
  components: {
    BaseTable,
    BaseWorkspaceTile,
    TheLayoutSidebar,
  },
  data: function () {
    return {
      batchToAddTo: [],
      sampleFileTableDataKey: 0,
      sampleFilesSelected: [],
    };
  },
  computed: {
    ...sync({
      sampleItemAttributesSaveProps: "modal/sampleItemAttributesSaveProps",
      workspaceModalProps: "modal/workspaceSaveProps",
    }),
    ...get({
      instrumentActive: "instrument/active",
      instruments: "app/instruments",
      recentAcquisitions: "instrument/recentAcquisitions",
      sampleBatches: "workspace/batches",
      sampleFileCols: "app/schema@sample_file",
      workspaceActive: "workspace/active",
      workspaces: "app/workspaces",
    }),
    sampleFileTableHeight() {
      return "calc(75vh)";
    },
    workspaceHomeText() {
      if (this.workspaceActive) {
        return `${this.workspaceActive.name}`;
      } else {
        return `Loading workspace...`;
      }
    },
  },
  created: function () {
  },
  methods: {
    ...call({
      loadInstrument: "instrument/load",
      unloadInstrument: "instrument/unload",
    }),
    ...mapMutations({
      activateModal: "modal/activate",
    }),
    selectBatchToAddTo(newRows, oldRows) {
      // single selection
      for (let row of oldRows.filter((row) => !newRows.includes(row))) {
        this.$api.emit('unsubscribe', row.sample_batch_id);
      }
      for (let row of newRows.filter((row) => !oldRows.includes(row))) {
        this.$api.emit('subscribe', row.sample_batch_id);
      }
      this.batchToAddTo = newRows.map((row) => row.sample_batch_id);
    },
    selectInstruments(newRows, oldRows) {
      for (let row of oldRows.filter((row) => !newRows.includes(row))) {
        this.$api.emit('unsubscribe', row.instrument);
      }
      for (let row of newRows.filter((row) => !oldRows.includes(row))) {
        this.$api.emit('subscribe', row.instrument);
      }
      const instrument = newRows.length ? newRows[0].instrument : null;
      if (instrument) {
        this.loadInstrument(instrument);
      } else {
        this.unloadInstrument();
      }
    },
    selectSampleFiles(newRows, oldRows) {
      this.sampleFilesSelected = newRows;
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
