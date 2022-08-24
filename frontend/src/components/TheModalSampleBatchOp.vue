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
                  deleteBatch([oldBatch.sample_batch_id]);
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
        ionMechanisms:  [
          "fVuWwQ82sJI", // +Br-
          "SbcztiBgxHg"  // -H-
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
      batches: "workspace/batches",
      probableMatchThreshold: "param/probableMatchThreshold",
      possibleMatchThreshold: "param/possibleMatchThreshold",
      workspaceActive: "workspace/active",
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
          workspace_id: this.workspaceActive.workspace_id,
          attributes: null,
          build_params: {
            ion_mechanisms: this.ionMechanismIds,
            },
          filter_params: {
            mz_tolerance: this.mzTolerance,
            probable_match_threshold: this.probableMatchThreshold,
            possible_match_threshold: this.possibleMatchThreshold,
            iso_ratio_tolerance: this.isotopeRatioTolerance,
            peak_min_intensity: this.peakIntensityMin,
            peak_min_separation: this.peakSeperationMin,
            mz_range: null,
            t_range: null
            },
          target_collection_id: this.targetCollectionIds,
        };
      } else if (this.actionIs("update")) {
        return {
          sample_batch_id: this.oldBatch.sample_batch_id,
          name: this.batchName,
          description: this.batchDesc,
          workspace_id: this.workspaceActive.workspace_id,
          attributes: null,
          build_params: {
            ion_mechanisms: this.ionMechanismIds,
          },
          filter_params: {
            mz_tolerance: this.mzTolerance,
            probable_match_threshold: this.probableMatchThreshold,
            possible_match_threshold: this.possibleMatchThreshold,
            iso_ratio_tolerance: this.isotopeRatioTolerance,
            peak_min_intensity: this.peakIntensityMin,
            peak_min_separation: this.peakSeperationMin,
            mz_range: null,
            t_range: null
            },
          target_collection_id: this.targetCollectionIds,
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
    ionMechanismIds() {
      return this.ionMechanisms
        ? this.ionMechanisms.map(
            (row) => row.mechanism_id
          )
        : []
    },
    targetCollectionIds() {
      return this.targetCollections
        ? this.targetCollections.map(
            (row) => row.target_collection_id
          )
        : []
    },
  },
  methods: {
    ...mapMutations({
      deactivateModal: "modal/deactivate",
    }),
    actionIs(...actions) {
      return actions.includes(this.action);
    },
    createBatch(newBatch) {
      this.$api.emit('sample_batch_create', newBatch);
    },
    deleteBatch(batches) {
      this.$api.emit('sample_batch_delete', batches);
    },
    initData() {
      if (this.oldBatch) {
        this.batchName = this.oldBatch.name;
        this.batchDesc = this.oldBatch.description;
      }
    },
    updateBatch(batches) {
      this.$api.emit('sample_batch_update', batches);
    },
  },
};
</script>