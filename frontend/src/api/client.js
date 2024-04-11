import { io } from 'socket.io-client'

import { useNotificationStore } from '@/stores/notification'

import { createHttpClient } from './http.js'

// LOAD ENV VARS
const mode = import.meta.env.MASCOPE_PUBLIC_MODE
const host = location.hostname
const api_port = import.meta.env.MASCOPE_PUBLIC_API_PORT

export const api = await initApi()

async function initApi() {
  const [socket, emit] = await initSocket()
  const http = createHttpClient(host, api_port)

  async function process({
    httpMethod,
    requestData,
    successNotificationType = 'submitted',
    successMessage = null, // empty for progress notification
    errorMessage = 'An error occurred while processing your request.',
    progressNotificationPayload = null // parameter for progress notification
  }) {
    try {
      const response = await http[httpMethod](requestData)
      if (response.status === 200 || response.status === 201) {
        const notificationStore = useNotificationStore()
        if (progressNotificationPayload) {
          notificationStore.showProgressNotification(progressNotificationPayload)
        } else {
          notificationStore.showGeneralNotification({
            notification: successNotificationType,
            message: successMessage
          })
        }
      }
      return response
    } catch (error) {
      // TODO_error_handling
      console.error(`Failed to process ${httpMethod}.`, error)
      const userErrorMessage = `${errorMessage}. ${error}`
      const notificationStore = useNotificationStore()
      notificationStore.showGeneralNotification({
        notification: 'error',
        message: userErrorMessage
      })
    }
  }

  async function request({ httpMethod, requestData = {} }) {
    try {
      const response = await http[httpMethod](requestData)
      if (response.status === 200) {
        const { data } = response
        return data
      }
    } catch (error) {
      console.error(`Failed to process ${httpMethod}.`, error)
      const notificationStore = useNotificationStore()
      notificationStore.showGeneralNotification({
        notification: 'error',
        message: error
      })
    }
  }

  return {
    socket,
    emit,
    http,
    request,
    process,
    log
  }
}

// helpers

function log(...args) {
  console.log('[API]', ...args)
}

async function initSocket() {
  // INIT API SOCKET

  // create the socket in `/` namespace
  let url = `ws://${host}:${api_port}`
  if (mode === 'production') {
    // production api server is routed to api_port via nginx reverse proxy
    url = `ws://${host}`
  }
  const socket = io(url)
  log('initialized socket for', mode, ':', url, socket)
  const emit = (ev, ...args) => {
    log(`emitting event "${ev}"`, ...args)
    socket.emit(ev, ...args)
  }
  return [socket, emit]
}
