<template>
  <section>
    <the-layout-sidebar>
      <div class="columns" style="margin: 0 auto; width: 70vw;">
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
              @selectRows="selectInstrument"
            >
            </base-table>
          </b-field>
          <div v-if="instrumentActive">
            <section style="padding: 2em 2em 2em 2em">
              <h1 class="title is-4">Acquisitions:</h1>
            </section>
            <b-collapse
              :open.sync="browseAcquisitions"
              animation="slide"
            >
              <template #trigger>
                <section style="padding: 0.5em">
                  <b-button
                    icon-left="calendar"
                    size="is-small"
                    @click="
                      (props) => {
                        props.open = !props.open;
                      }
                    "
                  >
                  </b-button>
                </section>
              </template>
              <div class="columns">
                <div class="column is-half">
                  <b-datetimepicker
                    placeholder="Starting from..."
                    v-model="sampleFileMinDatetime"
                  >
                  </b-datetimepicker>
                </div>
                <div class="column is-half">
                  <b-datetimepicker
                    placeholder="Until..."
                    v-model="sampleFileMaxDatetime"
                  >
                  </b-datetimepicker>
                </div>
              </div>
            </b-collapse>
            <base-table
              :key="sampleFileTableDataKey"
              :rows="acquisitions ? acquisitions : []"
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
                :disabled="!workspaceActive || !batchActive || sampleFilesSelected.length != 1"
                @click="launchProcessSelectedModal"
              >
                Process selected
              </b-button>
              <b-button
                type="is-primary"
                style="position: fixed; left: 15em; bottom: 2em"
                :disabled="!workspaceActive || !batchActive || sampleFilesSelected.length > 0"
                @click="launchProcessBatchModal"
              >
                Process batch
              </b-button>
            </section>
          </div>
        </div>
        <div class="column is-half">
          <template v-if="!workspaceActive">
            <section style="padding: 2em 2em 2em 2em">
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
            <the-pane-browser-sample></the-pane-browser-sample>
            <b-collapse
              v-if="batchActive"
              :open="false"
              animation="slide"
            >
              <template #trigger>
                <section style="padding: 0.5em">
                  <b-button
                    icon-left="wrench"
                    size="is-small"
                    @click="
                      (props) => {
                        props.open = !props.open;
                      }
                    "
                  >
                  </b-button>
                </section>
              </template>
              <the-pane-settings-batch></the-pane-settings-batch>
            </b-collapse>
            <the-pane-browser-target></the-pane-browser-target>
          </template>
        </div>
      </div>
    </the-layout-sidebar>
  </section>
</template>

<script>
import BaseTable from "./BaseTable.vue";
import BaseWorkspaceTile from "./BaseWorkspaceTile.vue";
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import ThePaneBrowserSample from "./ThePaneBrowserSample.vue";
import ThePaneBrowserTarget from "./ThePaneBrowserTarget.vue";
import ThePaneSettingsBatch from "./ThePaneSettingsBatch.vue";


import { mapMutations } from "vuex";
import { call, get, sync } from "vuex-pathify";

export default {
  name: "ThePageHome",
  components: {
    BaseTable,
    BaseWorkspaceTile,
    TheLayoutSidebar,
    ThePaneBrowserTarget,
    ThePaneBrowserSample,
    ThePaneSettingsBatch,
  },
  data: function () {
    return {
      browseAcquisitions: false,
      sampleFileMinDatetime: new Date(
        new Date().getTime() - (24*60*60*1000)
        ), // now - 24h
      sampleFileMaxDatetime: new Date(), // now
      sampleFilesSelected: [],
      sampleFileTableDataKey: 0,
    };
  },
  computed: {
    ...sync({
      sampleItemAttributesSaveProps: "modal/sampleItemAttributesSaveProps",
      workspaceModalProps: "modal/workspaceSaveProps",
    }),
    ...get({
      batchActive: "batch/active",
      instrumentActive: "instrument/active",
      instruments: "app/instruments",
      acquisitionsInRange: "instrument/acquisitions",
      recentAcquisitions: "instrument/recentAcquisitions",
      sampleBatches: "workspace/batches",
      sampleFileSchema: "app/schema@sample_file",
      workspaceActive: "workspace/active",
      workspaces: "app/workspaces",
    }),
    acquisitions() {
      return this.browseAcquisitions
        ? this.acquisitionsInRange
        : this.recentAcquisitions;
    },
    sampleFileCols() {
      return [
        {field: 'filename', label: 'Filename'}
      ];
    },
    sampleFileTableHeight() {
      return "calc(50vh)";
    },
    workspaceHomeText() {
      if (this.workspaceActive) {
        return `${this.workspaceActive.workspace_name}`;
      } else {
        return `Loading workspace...`;
      }
    },
  },
  created: function () {
    this.getAcquisitionsInRange();
  },
  methods: {
    ...call({
      getAcquisitions: "instrument/getAcquisitions",
      loadInstrument: "instrument/load",
      unloadInstrument: "instrument/unload",
    }),
    ...mapMutations({
      activateModal: "modal/activate",
    }),
    getAcquisitionsInRange() {
      this.getAcquisitions({
        min: this.sampleFileMinDatetime,
        max: this.sampleFileMaxDatetime
      });
    },
    launchProcessBatchModal() {
      this.activateModal({
        modal: 'sampleBatchImport',
      });
    },
    launchProcessSelectedModal() {
      this.sampleItemAttributesSaveProps = {
        action: 'create',
        sampleItemRecordToLoad: this.sampleFilesSelected[0],
      };
      this.activateModal({
        modal: 'sampleItemAttributesSave',
      });
    },
    selectInstrument(newRows, oldRows) {
      const instrument = newRows.length ? newRows[0].instrument : null;
      if (instrument) {
        this.loadInstrument(instrument);
        this.getAcquisitionsInRange();
      } else {
        this.unloadInstrument();
      }
    },
    selectSampleFiles(newRows, oldRows) {
      this.sampleFilesSelected = newRows;
    },
  },
  watch: {
    sampleFileMinDatetime: function () {
      this.getAcquisitionsInRange();
    },
    sampleFileMaxDatetime: function () {
      this.getAcquisitionsInRange();
    },
    recentAcquisitions: function() {
      // This watcher triggers on database reload
      if (this.browseAcquisitions) this.getAcquisitionsInRange();
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
