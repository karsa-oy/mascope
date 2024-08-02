import { io } from 'socket.io-client'

import { createHttpClient } from './http.js'

import { config } from '@/lib/config.js'
import { strToSnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'

// LOAD ENV VARS
const host = location.hostname
const mode = import.meta.env.MODE

export const api = await initApi()

async function initApi() {
  const [socket, emit] = await initSocket()
  const http = createHttpClient(host, config.server.port)

  // Catch errors, show error norification and return response from api
  async function apiResponse({ method, body = {} }) {
    const app = useApp()
    try {
      return await http[method](body)
    } catch (error) {
      console.error(`Failed to ${method}:`, error)
      app.ui.notification.push({
        type: strToSnakeCase(method),
        status: 'error',
        message: error.message
      })
    }
  }

  const request = {
    // method to write the data to api (http_methods: POST, success_status: 201)
    create: async ({ method, body = {} }) => {
      const app = useApp()
      const { data, status } = await apiResponse({ method, body })
      if (status === 201) {
        app.ui.notification.push({
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
      const app = useApp()
      const { data, status } = await apiResponse({ method, body })
      if (status === 200) {
        app.ui.notification.push({
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
      const app = useApp()
      const { data, status } = await apiResponse({ method, body })
      if (status === 200) {
        app.ui.notification.push({
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
    client: http.client,
    socket,
    emit,
    request,
    log
  }
}

// helpers

function log(...args) {
  console.log('[api]', ...args)
}

async function initSocket() {
  // init socket in `/` namespace
  const url = mode === 'production' ? `ws://${host}` : `ws://${host}:${config.server.port}`
  const socket = io(url)
  log('initialized socket for', mode, ':', url, socket)
  // create logged event emitter
  const emit = (event, ...args) => {
    log(`emitting event "${event}"`, ...args)
    socket.emit(event, ...args)
  }
  // create logged event handler
  const on = (event, callback, ...args) => {
    socket.on(event, callback)
    log(`handling event "${event}"`, ...args)
  }
  return [socket, emit, on]
}
