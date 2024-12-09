import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useUi } from './ui'

export const useAuth = defineStore('app.auth', () => {
  const ui = useUi()

  const user = ref(null)

  const identify = async () => {
    user.value =
      (await api.http.get('/users/me', {
        type: 'identify_user',
        use: 'auth',
        validateStatus: (status) => status < 500
      })) ?? false
  }
  const login = async ({ email, password }) => {
    const params = new URLSearchParams()
    params.append('grant_type', 'password')
    params.append('username', email)
    params.append('password', password)
    await api.http.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      type: 'signin_user',
      use: 'auth'
    })
    identify()
  }
  const logout = async () => {
    await api.http.post(
      `/auth/logout`,
      {},
      {
        type: 'signout_user',
        user: 'auth'
      }
    )
    identify()
  }

  // hooks

  const handlers = ref([])

  function onLogin(callback) {
    handlers.value.push({ callback })
  }

  watch(
    () => user.value,
    (newUser, oldUser) => {
      if (newUser && oldUser !== newUser) {
        handlers.value.forEach(({ callback }) => callback())
      }
      if (oldUser) {
        api.socket.emit('unsubscribe', `user-${oldUser.id}`)
      }
      if (newUser) {
        api.socket.emit('subscribe', `user-${newUser.id}`)
      }
    }
  )
  api.socket.on('user_reload_me', identify)

  return {
    user,
    identify,
    login,
    logout,
    onLogin
  }
})
