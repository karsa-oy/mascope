import { defineModule } from './lib/module'

import { api } from '@/api'
import { useApp } from '@/stores'

import { useAuth } from '../auth'

// helper to execute route with a role if
// superuser and do nothing otherwise:
const sudo = (execute) => {
  const auth = useAuth()
  const role = auth.user.role_name
  if (role == 'owner' || role == 'admin') {
    return execute(role)
  } else {
    return null
  }
}

export const useUser = defineModule({
  name: 'user',
  key: 'id',
  reloadOn: 'user_reload_all',
  load: () =>
    sudo(() =>
      api.http.get(`/users`, {
        use: 'read',
        type: 'load_users'
      })
    ) ?? [],
  read: (id) =>
    api.http.get(`/users/${id}`, {
      use: 'read',
      type: 'read_user'
    }),
  create: (user) =>
    sudo((role) =>
      api.http.post(`/users/${role}/register`, user, {
        use: 'create',
        type: 'register_user'
      })
    ),
  update: ({ id, username, email, role_id, password }) => {
    const app = useApp()
    return id && id !== app.auth.user.id
      ? sudo((role) =>
          api.http.patch(
            `/users/${role}/${id}`,
            { username, email, role_id },
            {
              use: 'update',
              type: 'update_user'
            }
          )
        )
      : api.http.patch(`/users/me`, { username, password }, { use: 'update', type: 'update_user' })
  },
  delete: (user) =>
    sudo((role) =>
      api.http.delete(`/users/${role}/${user.id}`, {
        use: 'delete',
        type: 'delete_user'
      })
    ),
  resetPassword: (user) =>
    sudo((role) =>
      api.http.get(`/users/${role}/${user.id}/reset-password`, {
        use: 'read',
        type: 'reset_password'
      })
    ),
  deleteAccessTokens: (user) =>
    sudo((role) =>
      api.http.delete(`/users/${role}/${user.id}/access-tokens`, {
        use: 'read',
        type: 'delete_access_tokens'
      })
    )
})
