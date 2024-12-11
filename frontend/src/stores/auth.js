import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

export const useAuth = defineStore('app.auth', () => {
  const user = ref(null)
  const ownerRegistrationStatus = ref(false)

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
      type: 'user_sign_in',
      use: 'auth'
    })
    identify()
  }
  const logout = async () => {
    await api.http.post(
      `/auth/logout`,
      {},
      {
        type: 'user_sign_out',
        user: 'auth'
      }
    )
    identify()
  }
  // Owner sign-up
  const getOwnerRegistrationStatus = async () => {
    try {
      const response = await api.http.get('/users/owner-registration/status', {
        type: 'owner_sign_up_status',
        use: 'auth',
        validateStatus: (status) => status < 500
      })
      ownerRegistrationStatus.value = response.status === 200
    } catch (error) {
      ownerRegistrationStatus.value = false
    }
  }

  const ownerSignUp = async ({ email, username, password, serverSecret }) => {
    await api.http.post(
      '/users/owner-registration',
      { email, username, password, server_secret: serverSecret },
      {
        type: 'owner_sign_up',
        use: 'create'
      }
    )
    getOwnerRegistrationStatus()
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
    ownerRegistrationStatus,
    identify,
    login,
    logout,
    getOwnerRegistrationStatus,
    ownerSignUp,
    onLogin
  }
})
