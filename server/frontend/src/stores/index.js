import { useData } from './data'
import { useUi } from './ui'
import { useAuth } from './auth'
import { useUppy } from './uppy'

export const useApp = () => ({
  data: useData(),
  ui: useUi(),
  auth: useAuth(),
  uppy: useUppy()
})
