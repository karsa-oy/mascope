import axios from 'axios'

import { runtime } from '@/lib/runtime.js'

import { useApp } from '@/stores'
import { api } from './client.js'
import handlers from './handlers.js'

const API_RESPONSE_TIMEOUT = 20_000 // 20 seconds

export const initHttp = () => {
  const client = axios.create({
    baseURL: `${runtime.api_path}/api`,
    withCredentials: true,
    timeout: API_RESPONSE_TIMEOUT
  })
  client.interceptors.request.use(handleRequestData, handleClientError)
  client.interceptors.response.use(handleResponseData, handleServerError)
  return client
}

// DATA HANDLING

function handleRequestData(config) {
  const { method, url } = config
  console.debug(`▶️ [api:http] request ${method} ${url}`, config)
  // session id
  const sid = api?.socket?.id
  if (sid) {
    config.headers['X-SID'] = sid
  }
  // handler
  let use, type
  ;({ use, type, ...config } = config)
  if (use) {
    config.headers['X-Handler'] = use
  }
  if (type) {
    config.headers['X-Type'] = type
  }
  return config
}

function handleResponseData(response) {
  const { method, url } = response?.config
  console.debug(`✅ [api:http] response ${method} ${url}`, response)
  // pick the handler
  const handlerName = response?.config?.headers['X-Handler']
  const handler = handlerName ? handlers[handlerName] : (resp) => resp
  // if a handler is defined
  return handler(response)
}

// ERROR HANDLING

function handleClientError(error) {
  const { method, url, headers } = error.config
  const type = headers['X-Type']
  // log to console for developers
  const { detail, error: message } = error?.response?.data
  console.error(`❌[api:http] ${method} ${url} client failure: ${detail?.error_message}`, error)
  // emit notification to users
  const app = useApp()
  app.ui.notification.push({
    type,
    status: 'error',
    message
  })
  // throw
  return Promise.reject(error)
}

/**
 * Handles server-side errors from API responses.
 * Part of axios interceptor chain, runs after handleResponseData and specific handlers.
 * One of purposes is catching unhandled 401s to trigger auth check.
 */
function handleServerError(error) {
  const { method, url, headers } = error?.config
  const type = headers['X-Type'] ?? 'unknown'

  // Any unhandled 401 triggers auth check, which will "redirect: to login if needed
  if (error?.response?.status === 401) {
    const app = useApp()
    app.auth.expire()
    return Promise.reject(error)
  }

  // log to console for developers
  const { detail, error: message } = error?.response?.data
  console.error(
    `🚫 [api:http] ${type} ${method} ${url} server failure: ${detail?.error_message}`,
    error
  )
  // emit notification to users
  const app = useApp()
  app.ui.notification.push({
    type,
    status: 'error',
    message
  })
  // throw
  return Promise.reject(error)
}
