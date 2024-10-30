import { useChart } from './chart'
import { useDarkmode } from './darkmode'
import { useFilter } from './filter'
import { useSplit } from './split'
import { useTab } from './tab'
import { useNotification } from './notification'

export const useUi = () => ({
  chart: useChart(),
  darkmode: useDarkmode(),
  filter: useFilter(),
  split: useSplit(),
  tab: useTab(),
  notification: useNotification()
})
