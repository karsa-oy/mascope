<template>
  <the-layout-sidebar>
    <section style="padding: 1em 0em 2em 0em">
      <h1 class="title is-3">Karsa Mascope</h1>
    </section>
    <template v-if="!workspaceActive">
      <div class="columns">
        <div class="column is-half">
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
        </div>
        <div class="column is-half">
          <section style="padding: 1em 0em 2em 0em">
            <h1 class="title is-4">Acquisitions:</h1>
          </section>
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
    </template>
    <template v-else>
      <section style="padding: 2em 2em 2em 2em">
        <h1 class="title is-3">{{ workspaceHomeText }}</h1>
      </section>
    </template>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar";
import BaseWorkspaceTile from "./BaseWorkspaceTile";

import { bindState } from "$lib/store";

import { mapMutations } from "vuex";

export default {
  name: "ThePageHome",
  components: {
    TheLayoutSidebar,
    BaseWorkspaceTile,
  },
  computed: {
    ...bindState({
      workspaceActive: "workspace/active",
      workspaces: "workspace/rows",
      modalProps: "modal/workspaceSaveProps",
    }),
    workspaceHomeText() {
      if (this.workspaceActive) {
        return `Welcome to workspace ${this.workspaceActive.name}!`;
      } else {
        return `Loading workspace...`;
      }
    },
  },
  methods: {
    ...mapMutations({
      activateModal: "modal/activate",
    }),
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
