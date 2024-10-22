import { ref } from "vue";
import { defineStore } from "pinia";

import { api } from "@/api";

import { useUi } from "./ui";

export const useAuth = defineStore('app.auth', () => {

  const ui = useUi()

  const user = ref()

  const identify = async () => {
    try {
      user.value = (await api.http.me())?.data;
    } catch (e) {
      ui.notification.push({
        type: 'user_identification',
        status: 'error',
        message: `Failed to identify user: ${e.message}`
      })
      console.error(e)
      user.value = null
    }
  }

  const signup = async ({ username, email, password }) => {
    try {
      const { status } = await api.http.register({ email, username, password })
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
      const message = e.message == 'REGISTER_USER_ALREADY_EXISTS'
        ? "a user with this email already exists; please use a different email."
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
      await api.http.login({ username: email, password })
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
      await api.http.logout()
    } catch (e) {
      ui.notification.push({
        type: 'user_logout',
        status: 'error',
        message: `Failed to login: ${e.message}`
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
