import { initSocket } from './socket'
import { initHttp } from './http'

const initApi = async () => {
  const socket = await initSocket()
  const http = initHttp()

  return { socket, http }
}

export const api = await initApi()
