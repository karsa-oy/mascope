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

  // --- First owner management ---
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
  // --- Login callback system (pub-sub pattern) ---
  // Stores register callbacks via auth.onLogin(() => sync())
  // When user actually logs in, all registered callbacks fire
  const handlers = ref([])

  function onLogin(callback) {
    handlers.value.push({ callback })
  }

  // Watch user changes for side effects
  watch(
    () => user.value,
    async (newUser, oldUser) => {
      // Compare by ID, not object references (prevents false positives on profile updates)
      const oldId = oldUser && typeof oldUser === 'object' ? oldUser.id : null
      const newId = newUser && typeof newUser === 'object' ? newUser.id : null
      // Fire login callbacks ONLY when user ID changes from null to valid (user login)
      if (newId && !oldId) {
        handlers.value.forEach(({ callback }) => callback())
      }

      // Socket subscriptions to user room - if user ID changed
      if (oldId !== newId) {
        if (oldId) {
          api.socket.emit('unsubscribe', `user-${oldId}`)
        }
        if (newId) {
          api.socket.emit('subscribe', `user-${newId}`)
        }
      }

      // Check first owner status only when no authenticated user found
      if (newUser === false && requiresOwner.value === null) {
        await checkFirstOwner()
      }
    }
  )

  // Listen for profile updates via socket and refresh user data
  api.socket.on('user_me_updated', identify)

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
