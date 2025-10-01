import { useAcquisition } from './modules/acquisition'
import { useBatch } from './modules/batch'
import { useInstrument } from './modules/instrument'
import { useIonizationMechanism, useIonizationMode } from './modules/ionization'
import {
  useMatchCollection,
  useMatchIon,
  useMatchParams,
  useMatchVisualized,
  useMatchBatchOverview
} from './modules/match'
import { usePeak } from './modules/peak'
import { useSample } from './modules/sample'
import { useTargetCollection, useTargetCompound } from './modules/target'
import { useTemplate } from './modules/template'
import { useUser } from './modules/user'
import { useWorkspace } from './modules/workspace'

export const useData = () => ({
  workspace: useWorkspace(),
  ionization: {
    mechanism: useIonizationMechanism(),
    mode: useIonizationMode()
  },
  instrument: useInstrument(),
  template: useTemplate(),
  batch: useBatch(),
  sample: useSample(),
  peak: usePeak(),
  target: {
    collection: useTargetCollection(),
    compound: useTargetCompound()
  },
  user: useUser(),
  match: {
    params: useMatchParams(),
    collection: useMatchCollection(),
    ion: useMatchIon(),
    visualized: useMatchVisualized(),
    batch_overview: useMatchBatchOverview()
  },
  acquisition: useAcquisition()
})
