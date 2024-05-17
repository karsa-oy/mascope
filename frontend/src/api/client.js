import { io } from 'socket.io-client'

import { createHttpClient } from './http.js'

import { strToSnakeCase } from '@/lib/utils'
import { useNotification } from '@/stores'

// LOAD ENV VARS
const mode = import.meta.env.MASCOPE_PUBLIC_MODE
const host = location.hostname
const api_port = import.meta.env.MASCOPE_PUBLIC_API_PORT

export const api = await initApi()

async function initApi() {
  const [socket, emit] = await initSocket()
  const http = createHttpClient(host, api_port)

  // Catch errors, show error norification and return response from api
  async function apiResponse({ method, body = {} }) {
    const notification = useNotification()
    try {
      return await http[method](body)
    } catch (error) {
      console.error(`Failed to ${method}:`, error)
      notification.push({
        type: strToSnakeCase(method),
        status: 'error',
        message: error.message
      })
    }
  }

  const request = {
    // method to write the data to api (http_methods: POST, success_status: 201)
    create: async ({ method, body = {} }) => {
      const notification = useNotification()
      const { data, status } = await apiResponse({ method, body })
      if (status === 201) {
        notification.push({
          type: strToSnakeCase(method),
          status: 'success',
          message: data.message,
          data: {
            request: {
              body,
              method
            },
            response: {
              data,
              status
            }
          }
        })
      }
    },
    // method to get the data from api (http_methods: GET,POST, success_status: 200)
    read: async ({ method, body = {} }) => {
      const { data, status } = await apiResponse({ method, body })
      if (status === 200) {
        return data
      }
    },
    // method to update the data in api (http_methods: PATCH, success_status: 200)
    update: async ({ method, body = {} }) => {
      const notification = useNotification()
      const { data, status } = await apiResponse({ method, body })
      if (status === 200) {
        notification.push({
          type: strToSnakeCase(method),
          status: 'success',
          message: data.message,
          data: {
            request: {
              body,
              method
            },
            response: {
              data,
              status
            }
          }
        })
      }
    },
    // method to delete the data from api (http_methods: DELETE, success_status: 200)
    delete: async ({ method, body = {} }) => {
      const notification = useNotification()
      const { data, status } = await apiResponse({ method, body })
      if (status === 200) {
        notification.push({
          type: strToSnakeCase(method),
          status: 'success',
          message: data.message,
          data: {
            request: {
              body,
              method
            },
            response: {
              data,
              status
            }
          }
        })
      }
    },
    // method to start the long running process in api (http_methods: GET, POST, success_status: 202, data is returned in sio user_notifications)
    process: async ({ method, body = {} }) => {
      const { data, status } = await apiResponse({ method, body })
      if (status === 202) {
        console.log('Progress notification', data)
      }
    }
  }

  return {
    socket,
    emit,
    request,
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
