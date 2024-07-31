import { useData } from './data'
import { useUi } from './ui'

export const useApp = () => ({
  data: useData(),
  ui: useUi()
})
