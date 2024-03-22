<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="initData"
      @close="deactivateModal"
    >
      <template v-if="actionIs('copy')">
        <div class="modal-card" style="width: 500px">
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <!-- New Item Name Input -->
            <b-field label="New item name">
              <b-input v-model="newItemName"></b-input>
            </b-field>

            <!-- Workspace Selection -->
            <b-field label="Select a workspace to copy the item to:">
              <b-select v-model="workspaceSelected" @input="loadWorkspaceData" expanded>
                <option :value="sameWorkspace" v-if="sameWorkspace">
                  Same workspace: {{ sameWorkspace.workspace_name }}
                </option>
                <option
                  v-for="workspace in filteredWorkspaces"
                  :key="workspace.workspace_id"
                  :value="workspace"
                >
                  {{ workspace.workspace_name }}
                </option>
              </b-select>
            </b-field>

            <!-- Batch Selection -->
            <b-field
              label="Select a batch to copy the item to:"
              v-if="sameBatch || batches.length > 0"
            >
              <b-select v-model="batchSelected" expanded>
                <option :value="sameBatch" v-if="sameBatch">
                  Same batch: {{ sameBatch.sample_batch_name }}
                </option>
                <option v-for="batch in batches" :key="batch.sample_batch_id" :value="batch">
                  {{ batch.sample_batch_name }}
                </option>
              </b-select>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button type="is-warning" icon-left="close" expanded @click="deactivateModal">
              Cancel
            </b-button>
            <b-button
              type="is-primary"
              icon-left="content-save"
              expanded
              :loading="isCopying"
              :disabled="!newItemName || !workspaceSelected || !batchSelected || isCopying"
              @click="copySampleItem"
            >
              {{ isCopying ? 'Please Wait...' : 'Copy Item' }}
            </b-button>
          </footer>
        </div>
      </template>
    </b-modal>
  </section>
</template>

<script>
import { mapMutations } from 'vuex'
import { call, get, sync } from 'vuex-pathify'
import { generateCopyName } from '../store/modules/apiHelper'

export default {
  name: 'TheModalSampleItemOverview',
  components: {},
  data: function () {
    return {
      newItemName: null,
      workspaceSelected: null,
      batchSelected: null,
      batches: [],
      sameBatch: null,
      isCopying: false,
    }
  },
  computed: {
    ...get({
      modalProps: 'modal/sampleItemOverviewProps',
      sampleItemActive: 'sample/active',
      activeBatch: 'batch/active',
      allWorkspaces: 'app/workspaces',
      activeWorkspace: 'workspace/active',
    }),
    ...sync({
      modalActive: 'modal/sampleItemOverviewActive',
    }),
    action() {
      return this.modalProps.action
    },
    sampleItem() {
      return this.modalProps && this.modalProps.sample
        ? this.modalProps.sample
        : this.sampleItemActive
          ? this.sampleItemActive
          : null
    },
    modalTitle() {
      let title = 'Sample item overview'
      if (!this.sampleItem) return title
      if (this.action === 'copy') {
        title = `Copy "${this.sampleItem.sample_item_name}"`
      }
      return title
    },
    sameWorkspace() {
      return this.activeWorkspace ? this.activeWorkspace : null
    },
    filteredWorkspaces() {
      if (this.activeWorkspace) {
        return this.allWorkspaces.filter((workspace) => {
          return workspace.workspace_id !== this.activeWorkspace.workspace_id
        })
      }
      return []
    },
  },
  methods: {
    ...call({
      gethWorkspaceBatches: 'workspace/gethWorkspaceBatches',
      copySample: 'sample/copySample',
      showWarningNotification: 'notification/showWarningNotification',
    }),
    ...mapMutations({
      deactivateModal: 'modal/deactivate',
    }),
    actionIs(...actions) {
      return actions.includes(this.action)
    },
    initData() {
      if (this.modalProps.action === 'copy') {
        this.newItemName = this.sampleItem
          ? generateCopyName(this.sampleItem.sample_item_name)
          : null
        this.workspaceSelected = null
        this.batchSelected = null
        this.batches = []
        this.sameBatch = null
      }
    },
    async loadWorkspaceData() {
      if (!this.workspaceSelected) return

      const workspaceBatches = await this.gethWorkspaceBatches(this.workspaceSelected.workspace_id)

      this.batches = workspaceBatches || []

      if (!this.batches.length) {
        this.showWarningNotification({
          notification: 'emptyWorkspace',
          data: `${this.workspaceSelected.workspace_name}`,
        })
      }

      // Check if the active batch is present in the selected workspace
      this.sameBatch =
        this.batches.find((batch) => batch.sample_batch_id === this.activeBatch.sample_batch_id) ||
        null

      // Filter out the same batch from batches options
      if (this.sameBatch) {
        this.batches = this.batches.filter((batch) => {
          return batch.sample_batch_id !== this.sameBatch.sample_batch_id
        })
      }
    },
    async copySampleItem() {
      this.isCopying = true
      const sample = {
        // for http client
        sample_item_id: this.sampleItem.sample_item_id,
        sample_batch_id: this.batchSelected.sample_batch_id,
        sample_item_name: this.newItemName,
        // for notification
        sample_batch_name: this.batchSelected.sample_batch_name,
        workspace_name: this.workspaceSelected.workspace_name,
      }
      await this.copySample(sample)
      this.isCopying = false
      this.deactivateModal()
    },
  },
  watch: {
    modalActive: {
      immediate: true,
      handler(newVal) {
        if (newVal) {
          this.initData()
        }
      },
    },
  },
}
</script>
