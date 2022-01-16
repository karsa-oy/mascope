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
            @click="deactivateModal"
            style="float: right"
          >
            Cancel
          </b-button>

          <b-button
            v-if="actionIs('edit', 'create')"
            type="is-primary"
            icon-left="content-save"
            @click="
              () => {
                saveWorkspace(newWorkspace);
                deactivateModal();
              }
            "
          >
            Save
          </b-button>
          <b-button
            v-if="actionIs('delete')"
            type="is-danger"
            icon-left="delete"
            @click="
              () => {
                deleteWorkspace(oldWorkspace);
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
import { bindState } from "$lib/store";

import { mapMutations } from "vuex";

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
    ...bindState({
      modalActive: "ui/modal/workspaceSaveActive",
      modalProps: "ui/modal/workspaceSaveProps",
      $workspaces: "workspace/$rows",
    }),
    action() {
      return this.modalProps.action;
    },
    oldWorkspace() {
      if (this.actionIs("edit", "delete")) {
        return table.get(this.$workspaces, {
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
      deleteWorkspace: "workspace/delete",
      saveWorkspace: "workspace/save",
      deactivateModal: "ui/modal/deactivate",
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