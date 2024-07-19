import { useInstrument } from './instrument'
import { useMechanism } from './mechanism'
import { useTemplate } from './template'
import { useWorkspace } from './workspace'
import { useSample } from './sample'
import { useBatch } from './batch'
import { useTargetCollection, useTargetCompound } from './target'
import { useMatchCollection, useMatchCompound, useMatchIon, useMatchIsotope } from './match'

export const useData = () => ({
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
  match: {
    collection: useMatchCollection(),
    compound: useMatchCompound(),
    ion: useMatchIon(),
    isotope: useMatchIsotope()
  }
})
