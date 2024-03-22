import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { handleApiRequest, getApiData } from './lib/api'

import { useBatchStore } from './batch'
import { useApiStore } from './api'
import { useTargetsStore } from './targets'

export const useWorkspaceStore = defineStore('workspace', () => {
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
    if (active.value) await unload(false)
    const apiStore = useApiStore()
    apiStore.emit('subscribe', workspaceId)
    await loadWorkspace(workspaceId)
    await loadBatches(workspaceId)
  }

  async function loadWorkspace(workspaceId) {
    const workspace = await getWorkspace(workspaceId)
    active.value = workspace
  }

  async function loadBatches(workspaceId) {
    const workspaceBatches = await getWorkspaceBatches(workspaceId)

    const batches = workspaceBatches.map((batch) => {
      return { ...batch, selection: 0 }
    })
    batches.value = batches
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
    const apiStore = useApiStore()
    apiStore.emit('unsubscribe', active.value.workspace_id)
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
    return await getApiData({
      httpMethod: 'getWorkspace',
      requestData: workspaceId,
      errorMessage: `Failed to load workspace.`
    })
  }
  async function getWorkspaceBatches(workspaceId) {
    const batches = await getApiData({
      httpMethod: 'getAllBatches',
      requestData: {
        workspace_id: workspaceId
      },
      errorMessage: `Failed to load the workspace batches.`
    })
    return batches.value.data
  }

  async function createWorkspace(newWorkspace) {
    const apiStore = useApiStore()
    await apiStore.http.createWorkspace(newWorkspace)
  }

  async function updateWorkspace(newWorkspace) {
    const apiStore = useApiStore()
    await apiStore.http.updateWorkspace(newWorkspace)
  }

  async function deleteWorkspace(workspace) {
    return await handleApiRequest({
      httpMethod: 'deleteWorkspace',
      requestData: workspace,
      successNotificationType: 'deleted',
      successMessage: `Workspace ${workspace.workspace_name} was deleted successfully!`,
      errorMessage: `Failed to delete workspace ${workspace.workspace_name}. Please try again.`
    })
  }

  // backend notifications
  async function onWorkspaceReload() {
    await reload()
  }

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
    loadWorkspace,
    loadBatches,
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
