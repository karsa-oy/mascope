<template>
  <the-layout>
    <div class="container">
      <section class="base-home-page">
        <section style="padding: 1em 0em 2em 0em">
          <h1 class="title">Karsa Mascope</h1>
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
            style="float: right"
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
      </section>
    </div>
  </the-layout>
</template>

<script>
import TheLayout from "./TheLayout";
import BaseWorkspaceTile from "./BaseWorkspaceTile";

import { bindState } from "$lib/store";

import { mapMutations } from "vuex";

export default {
  name: "ThePageLanding",
  components: {
    TheLayout,
    BaseWorkspaceTile,
  },
  computed: {
    ...bindState({
      workspaces: "workspace/$rows",
      modalProps: "modal/workspaceSaveProps",
    }),
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
