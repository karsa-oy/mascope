// standard
import { useInstrument } from './instrument'
import { useMechanism } from './mechanism'
import { useTemplate } from './template'
import { useWorkspace } from './workspace'
import { useSample } from './sample'
import { useBatch } from './batch'
import { useTargetCollection, useTargetCompound } from './target'

// semistandard
import { useMatchCollection, useMatchCompound, useMatchIon, useMatchIsotope } from './match'

// nonstandard
import { useAcquisition } from './acquisition'
import { useFilterParams } from './filterParams'

export const useData = () => ({
  // standard
  workspace: useWorkspace(),
  instrument: useInstrument(),
  mechanism: useMechanism(),
  template: useTemplate(),
  batch: useBatch(),
  sample: useSample(),
  target: {
    collection: useTargetCollection(),
    compound: useTargetCompound()
  },
  // semistandard
  match: {
    collection: useMatchCollection(),
    compound: useMatchCompound(),
    ion: useMatchIon(),
    isotope: useMatchIsotope()
  },
  // nonstandard
  acquisition: useAcquisition(),
  filterParams: useFilterParams()
})
