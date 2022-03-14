<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="loadBatch"
      :type="actionIs('delete') ? 'is-danger' : 'is-primary'"
    >
      <div class="modal-card" style="width: 500px">
        <header class="modal-card-head">
          <h2 class="subtitle">{{ modalTitle }}</h2>
        </header>
        <section class="modal-card-body" style="min-height: 250px">
          <b-field v-if="actionIs('create', 'edit')" label="Name">
            <b-input v-model="batchName"></b-input>
          </b-field>
          <b-field v-if="actionIs('create', 'edit')" label="Description">
            <b-input v-model="batchDesc"></b-input>
          </b-field>
          <p v-if="actionIs('delete')">
            Are you sure you want to delete this sample batch?
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
                updateBatch(newBatch);
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
                createBatch(newBatch);
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
                deleteBatch(oldBatch);
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
      batchName: null,
      batchDesc: null,
    };
  },
  computed: {
    ...bindState({
      modalActive: "modal/batchSaveActive",
      modalProps: "modal/batchSaveProps",
      batches: "sample/batchRows",
      workspaceActive: "workspace/active",
    }),
    action() {
      return this.modalProps.action;
    },
    oldBatch() {
      if (this.actionIs("edit", "delete")) {
        return table.get(this.batches, {
          id: this.modalProps.batchId,
        });
      } else {
        return null;
      }
    },
    newBatch() {
      if (this.actionIs("create", "edit")) {
        return {
          id: this.oldBatch ? this.oldBatch.id : null,
          name: this.batchName,
          description: this.batchDesc,
          workspaceId: this.workspaceActive.id,
        };
      } else {
        return null;
      }
    },
    modalTitle() {
      let title;
      switch (this.action) {
        case "create":
          title = `Create a new sample batch`;
          break;
        case "edit":
          title = `Edit sample batch ${this.oldBatch.name}`;
          break;
        case "delete":
          title = `Delete sample batch ${this.oldBatch.name}`;
          break;
      }
      return title;
    },
  },
  methods: {
    ...mapMutations({
      deleteBatch: "sample/batchDelete",
      updateBatch: "sample/batchUpdate",
      createBatch: "sample/batchCreate",
      deactivateModal: "modal/deactivate",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    loadBatch() {
      if (this.oldBatch) {
        this.batchName = this.oldBatch.name;
        this.batchDesc = this.oldBatch.description;
      }
    },
  },
};
</script>