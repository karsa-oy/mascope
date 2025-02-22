import { io } from 'socket.io-client'

import { runtime } from '@/lib/runtime.js'

const host = location.hostname

export function initSocket() {
  // init socket in `/` namespace
  const url = runtime.mode === 'prod' ? `https://${host}` : `ws://${host}:${runtime.meta.api_port}`
  const socket = io(url, {
    withCredentials: true, // Enables cookie sending
    transports: ['websocket']
  })
  console.debug('[api:sio] initialized socket for', runtime.mode, ':', url, socket)
  // logging handlers
  socket.onAny((eventName, ...event) => {
    console.debug(`[api:sio] ${eventName} emitted:`, event)
  })
  return socket
}
