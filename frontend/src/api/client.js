import { initSocket } from './socket'
import { initHttp } from './http'

const initApi = () => ({
  http: initHttp(),
  socket: initSocket()
})

export const api = initApi()
