import { defineStore } from 'pinia'

import { api } from '@/api'

import { useData } from '@/lib/store'

export const useWorkspace = defineStore('app.data.workspace', () => {
  const name = 'workspace'
  const key = 'workspace_id'

  const data = useData(
    name,
    () =>
      api.http.get(`/workspaces`, {
        use: 'read',
        type: 'load_workspaces'
      }),
    {
      key,
      selection: {
        mode: 'binary',
        persist: true
      }
    }
  )

  return {
    ...data,
    // backend
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
      }),
    // membership
    getMembers: (workspace_id) =>
      api.http.get(`/workspaces/${workspace_id}/members`, {
        use: 'read',
        type: 'load_workspace_members'
      }),
    addMember: (workspace_id, member) =>
      api.http.post(`/workspaces/${workspace_id}/members`, member, {
        use: 'create',
        type: 'add_workspace_member'
      }),
    updateMember: (workspace_id, user_id, member) =>
      api.http.patch(`/workspaces/${workspace_id}/members/${user_id}`, member, {
        use: 'update',
        type: 'update_workspace_member'
      }),
    removeMember: (workspace_id, user_id) =>
      api.http.delete(`/workspaces/${workspace_id}/members/${user_id}`, {
        use: 'delete',
        type: 'remove_workspace_member'
      })
  }
})
