import { defineModule } from './lib/module'

import { api } from '@/api'

export const useWorkspace = defineModule({
  name: 'workspace',
  key: 'workspace_id',
  subscribe: true,
  load: async () =>
    (
      await api.request.read({
        method: 'getAllWorkspaces'
      })
    )?.data,
  read: async (workspace_id) =>
    await api.request.read({
      method: 'getWorkspace',
      body: { workspaceId: workspace_id }
    }),
  create: async (workspace) =>
    await api.request.create({
      method: 'createWorkspace',
      body: workspace
    }),
  update: async (workspace) =>
    await api.request.update({
      method: 'updateWorkspace',
      body: {
        workspaceId: workspace.workspace_id,
        body: workspace
      }
    }),
  delete: async (workspace) =>
    await api.request.delete({
      method: 'deleteWorkspace',
      body: workspace
    })
})
