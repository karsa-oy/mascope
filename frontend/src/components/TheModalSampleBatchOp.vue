<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="initData"
      :type="actionIs('delete') ? 'is-danger' : 'is-primary'"
    >
      <div class="modal-card" style="width: 500px">
        <header class="modal-card-head">
          <h2 class="subtitle">{{ modalTitle }}</h2>
        </header>
        <section class="modal-card-body" style="min-height: 250px">
          <b-field v-if="actionIs('create', 'update')" label="Name">
            <b-input v-model="batchName"></b-input>
          </b-field>
          <b-field v-if="actionIs('create', 'update')" label="Description">
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
            v-if="actionIs('create')"
            type="is-primary"
            icon-left="content-save"
            expanded
            @click="
              () => {
                createBatch([newBatch]);
                deactivateModal();
              }
            "
          >
            Create
          </b-button>
          <b-button
            v-if="actionIs('update')"
            type="is-primary"
            icon-left="content-save"
            expanded
            @click="
              () => {
                updateBatch([newBatch]);
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
            expanded
            @click="
              () => {
                deleteBatch([oldBatch.id]);
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

import { mapMutations, mapActions, mapGetters } from "vuex";

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
      modalActive: "modal/sampleBatchOpActive",
      modalProps: "modal/sampleBatchOpProps",
      batches: "sample/batch/rows",
    }),
    ...mapGetters({
      workspaceSelected: "workspace/selectedRow",
    }),
    action() {
      return this.modalProps.action;
    },
    oldBatch() {
      return this.modalProps.batch ?? null;
    },
    newBatch() {
      if (this.actionIs("create")) {
        return {
          name: this.batchName,
          description: this.batchDesc,
          workspaceId: this.workspaceSelected.id,
        };
      } else if (this.actionIs("update")) {
        return {
          id: this.oldBatch.id,
          name: this.batchName,
          description: this.batchDesc,
          workspaceId: this.workspaceSelected.id,
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
        case "update":
          title = `Update sample batch ${this.oldBatch.name}`;
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
      deactivateModal: "modal/deactivate",
    }),
    ...mapActions({
      deleteBatch: "sample/batch/delete",
      updateBatch: "sample/batch/update",
      createBatch: "sample/batch/create",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    initData() {
      if (this.oldBatch) {
        this.batchName = this.oldBatch.name;
        this.batchDesc = this.oldBatch.description;
      }
    },
  },
};
</script>