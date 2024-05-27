import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useBatchStore } from './batch'
import { useTargetsStore } from './targets'
import { useNotification } from './notification'
import { useAppStore } from './app'

export const useWorkspaceStore = defineStore('workspace', () => {
  const notification = useNotification()

  const active = ref(null)
  const batches = ref([])

  // getters

  const sampleBatch = computed(
    () => (sampleBatchId) => batches.value.find((batch) => batch.sample_batch_id == sampleBatchId)
  )
  const sampleBatches = computed(() => batches.value ?? [])
  const sampleBatchesSelected = computed(() =>
    sampleBatches.value.filter((sampleBatch) => sampleBatch.selection >= 2)
  )

  // actions

  async function load(workspaceId) {
    const targetsStore = useTargetsStore()
    if (active.value) await unload(false)
    api.emit('subscribe', workspaceId)
    active.value = await getWorkspace(workspaceId)
    batches.value = (await getWorkspaceBatches(workspaceId)).map((batch) => {
      return { ...batch, selection: 0 }
    })
    await targetsStore.load()
  }

  async function reload() {
    const batchStore = useBatchStore()
    if (active.value) {
      const activeWorkspace = { ...active.value }
      const activeBatch = batchStore.active
      await unload(false)
      await load(activeWorkspace.workspace_id)
      if (activeBatch) {
        const batch = sampleBatch.value(activeBatch.sample_batch_id)
        if (!batch) return
        batch.selection = 2
        await batchStore.reload(batch)
      }
    }
  }

  async function unload(propagate = true) {
    if (!active.value) return
    api.emit('unsubscribe', active.value.workspace_id)
    active.value = null
    batches.value = []
    if (propagate) {
      const batchStore = useBatchStore()
      await batchStore.unload(true)
      const targetsStore = useTargetsStore()
      await targetsStore.unload(null)
    }
  }
  // http client endpoints
  async function getWorkspace(workspaceId) {
    return await api.request.read({
      method: 'getWorkspace',
      body: { workspaceId }
    })
  }
  async function getWorkspaceBatches(workspaceId) {
    const batches = await api.request.read({
      method: 'getAllBatches',
      body: {
        workspace_id: workspaceId
      },
      errorMessage: `Failed to load the workspace batches.`
    })
    return batches.data
  }

  async function createWorkspace(newWorkspace) {
    return await api.request.create({
      method: 'createWorkspace',
      body: newWorkspace
    })
  }

  async function updateWorkspace(newWorkspace) {
    const workspaceId = newWorkspace.workspace_id
    const body = newWorkspace
    return await api.request.update({
      method: 'updateWorkspace',
      body: { workspaceId, body }
    })
  }
  async function deleteWorkspace(workspace) {
    return await api.request.delete({
      method: 'deleteWorkspace',
      body: workspace
    })
  }

  // backend notifications
  async function onWorkspaceReload() {
    await reload()
  }

  notification.on('create_workspace', ({ status, data }) => {
    const appStore = useAppStore()
    if (status == 'success') {
      const workspace_id = data.response.data.workspace_id
      active.value = appStore.workspaces.find((workspace) => workspace.workspace_id == workspace_id)
    }
  })()

  return {
    // state
    active,
    batches,
    // getters
    sampleBatch,
    sampleBatches,
    sampleBatchesSelected,
    // actions
    load,
    reload,
    unload,
    getWorkspace,
    getWorkspaceBatches,
    createWorkspace,
    updateWorkspace,
    deleteWorkspace,
    onWorkspaceReload
  }
})
