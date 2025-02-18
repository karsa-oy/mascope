import { ref, watch, onMounted } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

export const useAuth = defineStore('app.auth', () => {
  const user = ref(null)
  const requiresOwner = ref(false)

  // Initial auth checks
  onMounted(async () => {
    await checkFirstOwner()
    await identify()
  })

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
        use: 'auth'
      }
    )
    identify()
  }
  const expire = async () => {
    await api.http.post(
      `/auth/logout`,
      {},
      {
        type: 'user_session_expired',
        use: 'auth'
      }
    )
    identify()
  }

  // First owner management
  const checkFirstOwner = async () => {
    try {
      const response = await api.http.get('/users/first-owner/status', {
        type: 'first_owner_status',
        use: 'auth',
        validateStatus: (status) => status < 500
      })
      requiresOwner.value = response.status === 200
    } catch (error) {
      requiresOwner.value = false
    }
  }

  const signupFirstOwner = async ({ email, username, password, serverSecret }) => {
    await api.http.post(
      '/users/first-owner',
      { email, username, password, server_secret: serverSecret },
      {
        type: 'first_owner_sign_up',
        use: 'create'
      }
    )
    checkFirstOwner()
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
    requiresOwner,
    identify,
    login,
    logout,
    expire,
    checkFirstOwner,
    signupFirstOwner,
    onLogin
  }
})
