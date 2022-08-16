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
                updateWorkspace([newWorkspace]);
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
                createWorkspace([newWorkspace]);
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
                deleteWorkspace([oldWorkspace.id]);
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
import { sync, call, get } from "vuex-pathify";

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
      modalActive: "modal/workspaceSaveActive",
      workspaces: "app/workspaces",
    }),
    ...sync({
      modalProps: "modal/workspaceSaveProps",
    }),
    action() {
      return this.modalProps.action;
    },
    oldWorkspace() {
      if (this.actionIs("edit", "delete")) {
        return table.get(this.workspaces, {
          id: this.modalProps.workspaceId,
        });
      } else {
        return null;
      }
    },
    newWorkspace() {
      if (this.actionIs("create", "edit")) {
        return {
          id: this.oldWorkspace ? this.oldWorkspace.id : null,
          name: this.workspaceName,
          description: this.workspaceDesc,
        };
      } else {
        return null;
      }
    },
    modalTitle() {
      let title;
      switch (this.action) {
        case "create":
          title = `Create a new workspace`;
          break;
        case "edit":
          title = `Edit workspace ${this.oldWorkspace.name}`;
          break;
        case "delete":
          title = `Delete workspace ${this.oldWorkspace.name}`;
          break;
      }
      return title;
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    ...call({
      deleteWorkspace: "workspace/delete",
      updateWorkspace: "workspace/update",
      createWorkspace: "workspace/create",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    loadWorkspace() {
      if (this.oldWorkspace) {
        this.workspaceName = this.oldWorkspace.name;
        this.workspaceDesc = this.oldWorkspace.description;
      }
    },
  },
};
</script>