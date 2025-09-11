// standard
import { useInstrument } from './instrument'
import { useIonizationMechanism, useIonizationMode } from './ionization'
import { useTemplate } from './template'
import { useWorkspace } from './workspace'
import { useSample } from './sample'
import { useBatch } from './batch'
import { useTargetCollection, useTargetCompound } from './target'
import { usePeak } from './peak'
import { useUser } from './user'

import {
  // semistandard
  useMatchCollection,
  useMatchCompound,
  useMatchIon,
  // nonstandard
  useMatchParams,
  useMatchVisualized
} from './match'

// nonstandard
import { useAcquisition } from './acquisition'

export const useData = () => ({
  // standard
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
  // semistandard
  match: {
    collection: useMatchCollection(),
    compound: useMatchCompound(),
    ion: useMatchIon(),
    params: useMatchParams(),
    visualized: useMatchVisualized()
  },
  // nonstandard
  acquisition: useAcquisition()
})
