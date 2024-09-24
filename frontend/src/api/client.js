import { createHttpClient } from './http.js'

import { runtime } from '@/lib/runtime.js'
import { strToSnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'

import { initSocket } from './socket.js'

export const api = await initApi()

async function initApi() {
  const socket = await initSocket()
  const http = createHttpClient(location.hostname, runtime.meta.api_port)

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

  const log = (...args) => console.log('[api]', ...args)

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
        return data
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
        log('Progress notification', data)
      }
    }
  }

  return {
    client: http.client,
    socket,
    request,
    log
  }
}
