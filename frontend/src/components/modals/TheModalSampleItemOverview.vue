<script setup>
import { ref, computed, watch } from 'vue'
import { generateCopyName } from '@/api'

import {
  useAppStore,
  useBatchStore,
  useModalStore,
  useSampleStore,
  useWorkspaceStore,
  useNotificationStore
} from '@/stores'

const appStore = useAppStore()
const batchStore = useBatchStore()
const sampleStore = useSampleStore()
const modalStore = useModalStore()
const workspaceStore = useWorkspaceStore()
const notificationStore = useNotificationStore()

// state
const newItemName = ref(null)
const workspaceSelected = ref(null)
const batchSelected = ref(null)
const batches = ref([])
const sameBatch = ref(null)
const isCopying = ref(false)

// computed
const action = computed(() => {
  return modalStore.state.sampleItemOverviewProps.action
})
const sampleItem = computed(() => {
  return modalStore.state.sampleItemOverviewProps && modalStore.state.sampleItemOverviewProps.sample
    ? modalStore.state.sampleItemOverviewProps.sample
    : sampleStore.active
      ? sampleStore.active
      : null
})
const modalTitle = computed(() => {
  let title = 'Sample item overview'
  if (!sampleItem.value) return title
  if (action.value === 'copy') {
    title = `Copy "${sampleItem.value.sample_item_name}"`
  }
  return title
})
const sameWorkspace = computed(() => {
  return workspaceStore.active ? workspaceStore.active : null
})
const filteredWorkspaces = computed(() => {
  if (workspaceStore.active) {
    return appStore.workspaces.filter((workspace) => {
      return workspace.workspace_id !== workspaceStore.active.workspace_id
    })
  }
  return []
})

// methods
function actionIs(...actions) {
  return actions.includes(action.value)
}
function initData() {
  if (modalStore.state.sampleItemOverviewProps.action === 'copy') {
    newItemName.value = sampleItem.value
      ? generateCopyName(sampleItem.value.sample_item_name)
      : null
    workspaceSelected.value = null
    batchSelected.value = null
    batches.value = []
    sameBatch.value = null
  }
}
async function loadWorkspaceData() {
  if (!workspaceSelected.value) return

  const workspaceBatches = await workspaceStore.getWorkspaceBatches(
    workspaceSelected.value.workspace_id
  )

  batches.value = workspaceBatches || []

  if (!batches.value.length) {
    notificationStore.showWarningNotification({
      notification: 'emptyWorkspace',
      data: `${workspaceSelected.value.workspace_name}`
    })
  }

  // Check if the active batch is present in the selected workspace
  sameBatch.value =
    batches.value.find((batch) => batch.sample_batch_id === batchStore.active.sample_batch_id) ||
    null

  // Filter out the same batch from batches options
  if (sameBatch.value) {
    batches.value = batches.value.filter((batch) => {
      return batch.sample_batch_id !== sameBatch.value.sample_batch_id
    })
  }
}
async function copySampleItem() {
  isCopying.value = true
  const sample = {
    // for http client
    sample_item_id: sampleItem.value.sample_item_id,
    sample_batch_id: batchSelected.value.sample_batch_id,
    sample_item_name: newItemName.value,
    // for notification
    sample_batch_name: batchSelected.value.sample_batch_name,
    workspace_name: workspaceSelected.value.workspace_name
  }
  await sampleStore.copySample(sample)
  isCopying.value = false
  modalStore.deactivate()
}

// watchers
watch(
  computed(() => modalStore.state.sampleItemOverviewActive),
  (newVal) => {
    if (newVal) {
      initData()
    }
  },
  { immediate: true }
)
</script>

<template>
  <section>
    <b-modal
      v-model="modalStore.state.sampleItemOverviewActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="initData"
      @close="modalStore.deactivate"
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
