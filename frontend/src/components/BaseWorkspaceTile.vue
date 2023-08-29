<template>
  <div class="base-tile">
    <header class="tile-card-header">
      <p class="card-header-title" @click="onClick">
        {{ workspace.workspace_name }}
      </p>
      <b-dropdown aria-role="list">
        <template #trigger>
          <b-icon
            icon="dots-horizontal"
            size="small"
            type="is-dark"
            role="button"
          ></b-icon>
        </template>
        <b-dropdown-item
          aria-role="listitem"
          @click="
            () => {
              modalProps = {
                action: 'edit',
                workspace_id: workspace.workspace_id,
              };
              activateModal({
                modal: 'workspaceSave',
              });
            }
          "
        >
          Edit
        </b-dropdown-item>
        <b-dropdown-item
          aria-role="listitem"
          @click="
            () => {
              modalProps = {
                action: 'delete',
                workspace_id: workspace.workspace_id,
              };
              activateModal({
                modal: 'workspaceSave',
              });
            }
          "
        >
          Delete
        </b-dropdown-item>
      </b-dropdown>
    </header>
    <div class="tile-card-content">
      {{ workspace.workspace_description }}
    </div>
  </div>
</template>

<script>
import { mapMutations } from "vuex";
import { sync, call } from "vuex-pathify";

export default {
  name: "BaseWorkspaceTile",
  props: {
    workspace: {
      required: true,
    },
  },
  computed: {
    ...sync({
      modalProps: "modal/workspaceSaveProps",
    }),
  },
  methods: {
    ...call({
      workspaceLoad: "workspace/load",
    }),
    ...mapMutations({
      activateModal: "modal/activate",
    }),
    onClick() {
      this.workspaceLoad(this.workspace);
    },
  },
};
</script>
