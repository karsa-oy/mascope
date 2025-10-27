import { ref, watch, onMounted } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

export const useAuth = defineStore('app.auth', () => {
  const user = ref(null)
  const requiresOwner = ref(null)

  // Initial auth checks
  onMounted(async () => {
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
    await identify()
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
    await identify()
  }
  // First owner management
  const checkFirstOwner = async () => {
    const response = await api.http.get('/users/first-owner/status', {
      type: 'first_owner_status',
      use: 'auth'
    })
    requiresOwner.value = response?.status === 'available'
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
    await checkFirstOwner()
  }
  // Hooks
  const handlers = ref([])

  function onLogin(callback) {
    handlers.value.push({ callback })
  }

  // Watch user changes for side effects
  watch(
    () => user.value,
    async (newUser, oldUser) => {
      // Trigger login callbacks when user logs in
      if (newUser && oldUser !== newUser) {
        handlers.value.forEach(({ callback }) => callback())
      }

      // Socket subscriptions
      if (oldUser) {
        api.socket.emit('unsubscribe', `user-${oldUser.id}`)
      }
      if (newUser) {
        api.socket.emit('subscribe', `user-${newUser.id}`)
      }

      // Check first owner status only when no authenticated user found
      if (newUser === false && requiresOwner.value === null) {
        await checkFirstOwner()
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
    checkFirstOwner,
    signupFirstOwner,
    onLogin
  }
})
