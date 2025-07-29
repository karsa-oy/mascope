import { defineModule } from './lib/module'

import { api } from '@/api'

export const useWorkspace = defineModule({
  name: 'workspace',
  key: 'workspace_id',
  subscribe: true,
  load: {
    method: () =>
      api.http.get(`/workspaces`, {
        use: 'read',
        type: 'load_workspaces'
      }),
    events: ['workspace_reload']
  },
  allowUnfocus: false,
  persist: true,
  read: (workspace_id) =>
    api.http.get(`/workspaces/${workspace_id}`, {
      use: 'read',
      type: 'read_workspace'
    }),
  create: (workspace) =>
    api.http.post(`/workspaces`, workspace, {
      use: 'create',
      type: 'create_workspace'
    }),
  update: (workspace) =>
    api.http.patch(`/workspaces/${workspace.workspace_id}`, workspace, {
      use: 'update',
      type: 'update_workspace'
    }),
  delete: (workspace) =>
    api.http.delete(`/workspaces/${workspace.workspace_id}`, {
      use: 'delete',
      type: 'delete_workspace'
    })
})
