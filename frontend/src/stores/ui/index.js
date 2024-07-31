import { useChart } from './chart'
import { useDarkmode } from './darkmode'
import { useMatchVisualized } from './matchVisualized'
import { useSplit } from './split'
import { useTab } from './tab'
import { useNotification } from './notification'

export const useUi = () => ({
  chart: useChart(),
  darkmode: useDarkmode(),
  matchVisualized: useMatchVisualized(),
  split: useSplit(),
  tab: useTab(),
  notification: useNotification()
})
