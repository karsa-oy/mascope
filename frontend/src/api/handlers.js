import { useApp } from '@/stores'

export default {
  /**
   * Basic CRUD Operations
   */
  create: (response) => {
    const { type, status, message, data } = unpack(response)
    const app = useApp()
    if (status == 201) {
      // notify users
      app.ui.notification.push({
        type,
        message,
        status: 'success'
      })
      return data
    } else {
      unhandled(response)
      return
    }
  },
  read: (response) => {
    const { status, data } = unpack(response)
    if (status == 200 || status == 202) {
      return data.data
    } else {
      unhandled(response)
      return
    }
  },
  update: (response) => {
    const { type, status, message } = unpack(response)
    const app = useApp()
    if (status == 200) {
      // notify users
      app.ui.notification.push({
        type,
        message,
        status: 'success'
      })
      return null
    } else {
      unhandled(response)
      return
    }
  },
  delete: (response) => {
    const { type, status, message } = unpack(response)
    const app = useApp()
    if (status == 200) {
      // notify users
      app.ui.notification.push({
        type,
        message,
        status: 'success'
      })
      return null
    } else {
      unhandled(response)
      return
    }
  },
  /**
   * Start Background Process
   *   use with GET, POST
   */
  process: (response) => {
    const { status, data } = unpack(response)
    if (status === 202) {
      console.log('[api:http] progress notification', data)
      // data is returned in sio user_notifications
    } else {
      unhandled(response)
    }
  },
  /**
   * Authentication
   */
  auth: (response) => {
    const { type, status, message, data } = unpack(response)
    const app = useApp()
    if (status == 200 || status == 204) {
      // notify users
      if (!type.includes('identify')) {
        app.ui.notification.push({
          type,
          message: message ?? 'Signed in successfully',
          status: 'success'
        })
      }
      return data.data
    } else if (status == 401 && type !== 'identify_user') {
      // notify users
      app.ui.notification.push({
        type: 'user_signed_out',
        message: data?.error || 'Please sign in to the Mascope.',
        status: 'warning'
      })
      return null
    }
    unhandled(response)
    return data.data
  }
}

function unpack(response) {
  const { status, data, request, config } = response
  const { method, url } = request
  const message = data?.message
  const type = config?.headers['X-Type']
  return { type, status, message, data, request, method, url }
}

function unhandled(response) {
  const { status, method, url } = unpack(response)
  console.warn(`[api:http] ${method} ${url} response status ${status} unhandled:`, response)
}
