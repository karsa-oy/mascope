<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="loadWorkspace"
      @close="deactivateModal"
      :type="actionIs('delete') ? 'is-danger' : 'is-primary'"
    >
      <div class="modal-card" style="width: 500px">
        <header class="modal-card-head">
          <h2 class="subtitle">{{ modalTitle }}</h2>
        </header>
        <section class="modal-card-body" style="min-height: 250px">
          <b-field v-if="actionIs('create', 'edit')" label="Name">
            <b-input v-model="workspaceName"></b-input>
          </b-field>
          <b-field v-if="actionIs('create', 'edit')" label="Description">
            <b-input v-model="workspaceDesc"></b-input>
          </b-field>
          <p v-if="actionIs('delete')">
            Are you sure you want to delete this workspace?
          </p>
        </section>
        <footer class="modal-card-foot">
          <b-button
            type="is-warning"
            icon-left="close"
            expanded
            @click="deactivateModal"
          >
            Cancel
          </b-button>

          <b-button
            v-if="actionIs('edit')"
            type="is-primary"
            icon-left="content-save"
            expanded
            @click="
              () => {
                updateWorkspace();
                deactivateModal();
              }
            "
          >
            Save
          </b-button>
          <b-button
            v-if="actionIs('create')"
            type="is-primary"
            icon-left="content-save"
            expanded
            @click="
              () => {
                createWorkspace();
                deactivateModal();
              }
            "
          >
            Create
          </b-button>
          <b-button
            v-if="actionIs('delete')"
            type="is-danger"
            icon-left="delete"
            expanded
            @click="
              () => {
                deleteWorkspace();
                deactivateModal();
              }
            "
          >
            Delete
          </b-button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>

<script>
import { mapMutations } from "vuex";
import { sync, get } from "vuex-pathify";
import httpClient from "../httpClient.js";

import table from "$lib/table";

export default {
  name: "",
  components: {},
  data: function () {
    return {
      workspaceName: null,
      workspaceDesc: null,
    };
  },
  computed: {
    ...get({
      workspaces: "app/workspaces",
    }),
    ...sync({
      modalActive: "modal/workspaceSaveActive",
      modalProps: "modal/workspaceSaveProps",
    }),
    action() {
      return this.modalProps.action;
    },
    oldWorkspace() {
      if (this.actionIs("edit", "delete")) {
        return table.get(this.workspaces, {
          workspace_id: this.modalProps.workspace_id,
        });
      } else {
        return null;
      }
    },
    modalTitle() {
      let title;
      const workspaceName = this.oldWorkspace
        ? this.oldWorkspace.workspace_name
        : "";
      switch (this.action) {
        case "create":
          title = `Create a new workspace`;
          break;
        case "edit":
          title = `Edit workspace ${workspaceName}`;
          break;
        case "delete":
          title = `Delete workspace ${workspaceName}`;
          break;
      }
      return title;
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    async createWorkspace() {
      const newWorkspace = {
        workspace_name: this.workspaceName,
        workspace_description: this.workspaceDesc,
      };
      await httpClient.createWorkspace(newWorkspace);
    },
    async deleteWorkspace() {
      await httpClient.deleteWorkspace(this.oldWorkspace.workspace_id);
    },
    loadWorkspace() {
      this.workspaceName = this.oldWorkspace
        ? this.oldWorkspace.workspace_name
        : null;
      this.workspaceDesc = this.oldWorkspace
        ? this.oldWorkspace.workspace_description
        : null;
    },
    async updateWorkspace() {
      const updatedWorkspace = {
        workspace_name: this.workspaceName,
        workspace_description: this.workspaceDesc,
      };
      await httpClient.updateWorkspace(
        this.oldWorkspace.workspace_id,
        updatedWorkspace
      );
    },
  },
};
</script>
