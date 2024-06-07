import { useInstrument } from './instrument'
import { useMechanism } from './mechanism'
import { useTemplate } from './template'

import { useWorkspace } from './workspace'
import { useSample } from './sample'
import { useBatch } from './batch'
import { useTargetCollection, useTargetCompound } from './target'

export const useData = () => ({
  workspace: useWorkspace(),
  batch: useBatch(),
  sample: useSample(),
  target: {
    collection: useTargetCollection(),
    compound: useTargetCompound()
  },
  instrument: useInstrument(),
  mechanism: useMechanism(),
  template: useTemplate()
})
