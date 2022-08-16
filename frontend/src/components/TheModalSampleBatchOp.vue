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
      @close="deactivateModal"
      :type="actionIs('delete') ? 'is-danger' : 'is-primary'"
    >
      <template v-if="actionIs('create', 'update')">
        <div class="modal-card" style="height: 800px">
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <b-tabs type="is-boxed">
              <b-tab-item label="Info">
                <b-field label="Name">
                  <b-input v-model="batchName"></b-input>
                </b-field>
                <b-field label="Description">
                  <b-input v-model="batchDesc"></b-input>
                </b-field>
              </b-tab-item>
              <b-tab-item label="Target collections">
                <b-table
                  :data="allTargetCollections"
                  :columns="[
                    { field: 'name', label: 'Name' },
                    { field: 'description', label: 'Description' },
                  ]"
                  checkable
                  :checked-rows.sync="targetCollections"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item label="Ionization mechanisms">
                {{ ionMechanisms }}
                <b-table
                  :data="allIonMechanisms"
                  :columns="[
                    { field: 'mechanism', label: 'Mechanism' },
                    { field: 'polarity', label: 'Polarity' },
                  ]"
                  checkable
                  :checked-rows.sync="ionMechanisms"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item label="Settings"> MATCHP - todo </b-tab-item>
            </b-tabs>
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
              type="is-primary"
              icon-left="content-save"
              expanded
              @click="
                () => {
                  actionIs('create')
                    ? createBatch([newBatch])
                    : updateBatch([newBatch]);
                  deactivateModal();
                }
              "
            >
              Save
            </b-button>
          </footer>
        </div>
      </template>
      <template v-if="actionIs('delete')">
        <div class="modal-card" style="width: 500px">
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <p>Are you sure you want to delete this sample batch?</p>
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
      </template>
    </b-modal>
  </section>
</template>

<script>
import { mapMutations } from "vuex";
import { get, sync } from "vuex-pathify";

export default {
  name: "TheModalSampleBatchOp",
  components: {},
  data: function () {
    return {
      batchName: null,
      batchDesc: null,
      defaultConfig: {
        // target params
        targetCollections: [],
        ionMechanisms: [
          "fVuWwQ82sJI", // +Br-
          "5rm2sP6epAs", // +H+
        ],
        isotopeAbundanceMin: 10, // %
        // match params
        mzTolerance: 10, // ppm
        isotopeRatioTolerance: 10, // %
        // peak params
        peakIntensityMin: 1,
        peakSeperationMin: 3,
      },
      ionMechanisms: [],
      targetCollections: [],
    };
  },
  created() {},
  computed: {
    ...sync({
      modalActive: "modal/sampleBatchOpActive",
      modalProps: "modal/sampleBatchOpProps",
      allIonMechanisms: "app/ionMechanisms",
      allTargetCollections: "app/targetCollections",
    }),
    ...get({
      workspaceActive: "workspace/active",
      batches: "workspace/batches",
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
          workspaceId: this.workspaceActive.id,
        };
      } else if (this.actionIs("update")) {
        return {
          id: this.oldBatch.id,
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