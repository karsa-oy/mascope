import { initSocket } from './socket'
import { initHttp } from './http'

const initApi = async () => {
  const { socket, socketConnected } = await initSocket()
  const http = initHttp()

  return { socket, http, connected: socketConnected }
}

export const api = await initApi()
