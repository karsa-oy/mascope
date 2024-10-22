import { useData } from './data'
import { useUi } from './ui'
import { useAuth } from './auth'

export const useApp = () => ({
  data: useData(),
  ui: useUi(),
  auth: useAuth()
})
