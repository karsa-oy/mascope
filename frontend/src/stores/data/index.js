// standard
import { useInstrument } from './instrument'
import { useMechanism } from './mechanism'
import { useTemplate } from './template'
import { useWorkspace } from './workspace'
import { useSample } from './sample'
import { useBatch } from './batch'
import { useTargetCollection, useTargetCompound } from './target'
import { usePeak } from './peak'

import {
  // semistandard
  useMatchCollection,
  useMatchCompound,
  useMatchIon,
  useMatchIsotope,
  // nonstandard
  useMatchParams,
  useMatchVisualized
} from './match'

// nonstandard
import { useAcquisition } from './acquisition'

export const useData = () => ({
  // standard
  workspace: useWorkspace(),
  instrument: useInstrument(),
  mechanism: useMechanism(),
  template: useTemplate(),
  batch: useBatch(),
  sample: useSample(),
  peak: usePeak(),
  target: {
    collection: useTargetCollection(),
    compound: useTargetCompound()
  },
  // semistandard
  match: {
    collection: useMatchCollection(),
    compound: useMatchCompound(),
    ion: useMatchIon(),
    isotope: useMatchIsotope(),
    params: useMatchParams(),
    visualized: useMatchVisualized()
  },
  // nonstandard
  acquisition: useAcquisition()
})
