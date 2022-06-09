<template>
  <div class="card base-tile">
    <header class="card-header">
      <p class="card-header-title" @click="onClick">
        {{ workspace.name }}
      </p>
      <b-dropdown aria-role="list">
        <template #trigger>
          <b-icon icon="dots-horizontal" size="small" role="button"> </b-icon>
        </template>
        <b-dropdown-item
          aria-role="listitem"
          @click="
            () => {
              modalProps = {
                action: 'edit',
                workspaceId: workspace.id,
              };
              activateModal({
                modal: 'workspaceSave',
              });
            }
          "
          >Edit</b-dropdown-item
        >
        <b-dropdown-item
          aria-role="listitem"
          @click="
            () => {
              modalProps = {
                action: 'delete',
                workspaceId: workspace.id,
              };
              activateModal({
                modal: 'workspaceSave',
              });
            }
          "
          >Delete</b-dropdown-item
        >
      </b-dropdown>
    </header>
    <div class="card-content">
      {{ workspace.description }}
    </div>
  </div>
</template>


<script>
import { mapMutations, mapActions } from "vuex";
import { bindState } from "$lib/store";

export default {
  name: "BaseWorkspaceTile",
  props: {
    workspace: {
      type: Object,
      required: true,
    },
  },
  computed: {
    ...bindState({
      modalProps: "modal/workspaceSaveProps",
    }),
  },
  methods: {
    ...mapActions({
      workspaceToggle: "workspace/toggle",
    }),
    ...mapMutations({
      activateModal: "modal/activate",
    }),
    onClick() {
      this.workspaceToggle(this.workspace);
    },
  },
};
</script>

<style scoped>
.base-tile {
  height: 200px;
  width: 200px;
  margin: 10px;
}
</style>
