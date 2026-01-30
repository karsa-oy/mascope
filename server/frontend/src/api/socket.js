import { io } from 'socket.io-client'

import { runtime } from '@/lib/runtime.js'

const host = location.hostname
const activeSubscriptions = new Set()

export async function initSocket() {
  // init socket in `/` namespace
  const url = runtime.mode === 'prod' ? `https://${host}` : `ws://${host}:${runtime.meta.api_port}`
  const socket = io(url, {
    withCredentials: true, // Enables cookie sending
    transports: ['websocket']
  })
  console.debug('📭 [api:sio] initialized socket for', runtime.mode, ':', url, socket)

  // Wait for connection
  if (!socket.connected) {
    console.debug('⏳ [api:sio] Waiting for connection...')
    await new Promise((resolve) => socket.once('connect', resolve))
    console.debug('✅ [api:sio] Socket connected')
  }
  // logging handlers
  socket.onAny((eventName, ...event) => {
    console.debug(`📬 [api:sio] ${eventName} received:`, event)
  })

  // reconnect handler
  socket.io.on('reconnect_attempt', (attempt) => {
    console.debug('🔄 [api:sio] Socket reconnect attempt')
  })
  socket.on('connect', () => {
    // Use 'connect' event to detect reconnections, since the socket.io server
    // instance may be different in which case 'reconnect' event won't fire
    console.debug('✅ [api:sio] Socket reconnected')
    // Re-subscribe to all active rooms
    activeSubscriptions.forEach((room) => {
      socket.emit('subscribe', room)
      console.debug(`📬 [api:sio] Re-subscribed to room: ${room}`)
    })
  })
  socket.on('disconnect', (reason) => {
    console.warn('⚠️ [api:sio] Socket disconnected:', reason)
  })

  // Attach subscription management methods to socket
  socket.addSubscription = function (room) {
    activeSubscriptions.add(room)
    this.emit('subscribe', room)
  }
  socket.removeSubscription = function (room) {
    activeSubscriptions.delete(room)
    this.emit('unsubscribe', room)
  }

  return socket
}
