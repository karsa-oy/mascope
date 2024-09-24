import { io } from 'socket.io-client'

import { runtime } from '@/lib/runtime.js'

const host = location.hostname

export async function initSocket() {
  const log = (...args) => console.log('[api:sio]', ...args)
  // init socket in `/` namespace
  const url = runtime.mode === 'prod' ? `https://${host}` : `ws://${host}:${runtime.meta.api_port}`
  const socket = io(url)
  log('initialized socket for', runtime.mode, ':', url, socket)
  socket.io.on('error', (error) => {
    console.error(error)
  })
  socket.io.on('connection', (socket) => {
    socket.on('sample_batch_reload', (msg) => {
      console.log('XXX sample_batch_reload: ' + msg)
    })
  })
  return socket
}
