import { ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useUi } from './ui'

export const useAuth = defineStore('app.auth', () => {
  const ui = useUi()

  const user = ref(null)

  const identify = async () => {
    try {
      user.value =
        (
          await api.http.get('/users/me', {
            type: 'identify_user'
          })
        )?.data ?? false
    } catch (e) {
      user.value = false
    }
  }

  const signup = async ({ username, email, password }) => {
    try {
      const { status } = await api.http.post(
        `/auth/register`,
        {
          email,
          password,
          username
        },
        { type: 'register_user' }
      )
      if (status == 201) {
        return {
          status: 'success'
        }
      } else {
        return {
          status: 'failure'
        }
      }
    } catch (e) {
      const message =
        e.message == 'REGISTER_USER_ALREADY_EXISTS'
          ? 'a user with this email already exists; please use a different email.'
          : e.message
      ui.notification.push({
        type: 'user_signup',
        status: 'error',
        message: `Failed to sign up: ${message}`
      })
      return {
        status: 'failure',
        email,
        message
      }
    }
  }
  const login = async ({ email, password }) => {
    try {
      const params = new URLSearchParams()
      params.append('grant_type', 'password')
      params.append('username', email)
      params.append('password', password)
      await api.http.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        type: 'signin_user'
      })
    } catch (e) {
      ui.notification.push({
        type: 'user_login',
        status: 'error',
        message: `Failed to login: ${e.message}`
      })
      return
    }
    identify()
  }
  const logout = async () => {
    try {
      await api.http.post(
        `/auth/logout`,
        {},
        {
          type: 'signout_user'
        }
      )
    } catch (e) {
      ui.notification.push({
        type: 'user_logout',
        status: 'error',
        message: `Failed to logout: ${e.message}`
      })
      return
    }
    identify()
  }

  return {
    user,
    identify,
    signup,
    login,
    logout
  }
})
