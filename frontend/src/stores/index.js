import { useData } from './data'
import { useUi } from './ui'
import { useAcquisition } from './acquisition'
import { useFilterParams } from './filterParams'
import { useNotification } from './notification'

export const useApp = () => ({
  data: useData(),
  ui: useUi(),
  acquisition: useAcquisition(),
  filterParams: useFilterParams(),
  notification: useNotification()
})
