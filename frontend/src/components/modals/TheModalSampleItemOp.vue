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
const sampleItem = computed(
  () => modalStore.state.sampleItemOverviewProps?.sample ?? sampleStore.active
)
const newItemName = ref(
  sampleItem.value && modalStore.state.sampleItemOverviewProps.action === 'copy'
    ? generateCopyName(sampleItem.value.sample_item_name)
    : null
)
const workspaceSelected = ref(null)
const batchSelected = ref(null)
const batches = ref([])
const isCopying = ref(false)

// computed
const action = computed(() => {
  return modalStore.state.sampleItemOverviewProps.action
})

const modalTitle = computed(() => {
  let title = 'Sample item overview'
  if (!sampleItem.value) return title
  if (action.value === 'copy') {
    title = `Copy "${sampleItem.value.sample_item_name}"`
  }
  return title
})

// methods
function actionIs(...actions) {
  return actions.includes(action.value)
}

watch(workspaceSelected, loadWorkspaceData, { deep: true })

async function loadWorkspaceData() {
  console.log('bar', workspaceSelected.value)
  if (!workspaceSelected.value) return

  batches.value =
    (await workspaceStore.getWorkspaceBatches(workspaceSelected.value.workspace_id)) ?? []

  if (!batches.value.length) {
    notificationStore.showWarningNotification({
      notification: 'emptyWorkspace',
      data: `${workspaceSelected.value.workspace_name}`
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
</script>

<template>
  <section>
    <b-modal
      v-model="modalStore.state.sampleItemOverviewActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @close="modalStore.deactivate"
    >
      <div class="box" style="background-color: inherit; display: grid; place-items: center">
        <template v-if="actionIs('copy')">
          <div class="modal-card" style="width: 500px">
            <header class="modal-card-head">
              <h2 class="subtitle">{{ modalTitle }}</h2>
            </header>
            <section class="modal-card-body" style="min-height: 250px">
              <!-- New Item Name Input -->
              <b-field label="New item name">
                <b-input v-model="newItemName" />
              </b-field>

              <!-- Workspace Selection -->
              <b-field label="Select a workspace to copy the item to:">
                <b-select v-model="workspaceSelected" expanded>
                  <option
                    v-for="workspace in appStore.workspaces"
                    :key="workspace.workspace_id"
                    :value="workspace"
                  >
                    {{ workspace.workspace_name }}
                    {{
                      workspace.workspace_id == workspaceStore.active.workspace_id
                        ? '(current)'
                        : ''
                    }}
                  </option>
                </b-select>
              </b-field>

              <!-- Batch Selection -->
              <b-field label="Select a batch to copy the item to:" v-if="batches.length > 0">
                <b-select v-model="batchSelected" expanded>
                  <option v-for="batch in batches" :key="batch.sample_batch_id" :value="batch">
                    {{ batch.sample_batch_name }}
                    {{
                      batch.sample_batch_id === batchStore.active.sample_batch_id ? '(current)' : ''
                    }}
                  </option>
                </b-select>
              </b-field>
            </section>
            <footer class="modal-card-foot">
              <b-button type="is-warning" icon-left="close" expanded @click="modalStore.deactivate">
                Cancel
              </b-button>
              <b-button
                type="is-primary"
                icon-left="content-save"
                expanded
                :loading="isCopying"
                :disabled="!newItemName || !workspaceStore.active || !batchSelected || isCopying"
                @click="copySampleItem"
              >
                {{ isCopying ? 'Please Wait...' : 'Copy Item' }}
              </b-button>
            </footer>
          </div>
        </template>
      </div>
    </b-modal>
  </section>
</template>
