import { useChart } from './chart'
import { useDarkmode } from './darkmode'
import { useSplit } from './split'
import { useTab } from './tab'
import { useHelp } from './help'
import { useNotification } from './notification'

export const useUi = () => ({
  chart: useChart(),
  darkmode: useDarkmode(),
  split: useSplit(),
  tab: useTab(),
  help: useHelp(),
  notification: useNotification()
})
