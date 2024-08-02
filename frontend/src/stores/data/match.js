import { watch, computed } from 'vue'

import { api } from '@/api'

import { defineModule } from './lib'

import { useBatch } from './batch'
import { useSample } from './sample'

// Matches are implemented as a semiregular module,
// making it a bit different from the rest of the data
// modules. See the footnote for details.

const defineMatch = (level) => {
  return defineModule({
    name: `match.${level.toLowerCase()}`,
    key: `target_${level.toLowerCase()}_id`,
    reloadSelfOn: 'sample_batch_reload',
    useParent: () => ({
      // 'virtual' parent ensures matches react
      // to batch and sample selections
      name: 'batch & sample',
      multiselect: false,
      register: ({ reload }) => {
        const batch = useBatch()
        const sample = useSample()
        watch(
          computed(() => sample.focused?.sample_item_id ?? batch.focused?.sample_batch_id),
          () => reload()
        )
      }
    }),
    load: async () => {
      const batch = useBatch()
      const sample = useSample()
      if (sample.focused) {
        // If a sample is focused, load sample level matches
        return (
          await api.request.read({
            method: `getSampleMatch${level}s`,
            body: {
              sample_item_id: sample.focused.sample_item_id
            }
          })
        ).data
      } else if (batch.focused) {
        // If a batch is focused, load batch level matches
        return (
          await api.request.read({
            method: `getBatchMatch${level}s`,
            body: {
              sample_batch_id: batch.focused.sample_batch_id
            }
          })
        ).data
      } else {
        // Otherwise unload the data
        return []
      }
    }
  })
}

export const useMatchCollection = defineMatch('Collection')
export const useMatchCompound = defineMatch('Compound')
export const useMatchIon = defineMatch('Ion')
export const useMatchIsotope = defineMatch('Isotope')

// Footnote: reasoning for the irregular implementation

// The main usecase for this data is the target browser.
// Match scores depend on whether the aggregation is on
// the batch or sample level. For this reason, the module
// should load different scores depending on whether a sample,
// a batch or nothing is selected.

// This could have been implemented in a number of ways:
//  1. As an irregular store, not using the standard module
//  2. As multiple standard modules, glued together with custom code
//  3. By modifying the module library to support multiple parenting
//  4. As a quasiregular module, using a 'virtual' parent hook (current implementation)

// The first three options were eliminated for the following reasons:
//  - Matches still require selection logic since they are used in the target browser
//  - A fully custom store (approach #1) would therefore have to maintain feature parity
//    with the standard modules, resulting in a large maintenance burden and bug risks.
//  - Implementations #2 and #3 would introduce a lot of complexity, and are deemed
//    proverbial footguns likely to also caused bugs.

// Implementation #4 leverages the standard module by slightly abusing the API with
// a hack of sorts: afake useParent hook is constructed, which loads either batch or
// sample level aggregates based on what is currently focused.

// The disadvantage of this approach is a slight inefficiency of reloading batch
// aggregates every time we deselect a sample, even though it could be cached. The
// advantage of this implementation is that its extremely simple to understand and
// maintain: it just uses the same module code the other data modules stores use,
// by using this little API hack.

// Considering match logic and data models have a history of causing issues for the
// team due to the high cognitive overhead caused by the complexity of the data model,
// the tradeoff was chosen to favor developer experience in the expense of performance.

// In the future, the performance hit could be mitigated by correctly configuring our
// HTTP REST API caching.
