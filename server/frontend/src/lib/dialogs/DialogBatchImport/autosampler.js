import { useApp } from '@/stores'

export const autosampler = {
  parse: (rows) => {
    let result = []
    let step = {}
    for (let row of rows) {
      for (let cellKey in row) {
        const [key, value] = row[cellKey].split(':')
        if (key == 'Sequence step' || Object.keys(step).includes('Sequence step')) {
          // New sequence step or append existing step
          if (key && key.length) {
            step[key.trim()] = value.trim()
          }
        }
      }
      if (Object.keys(step).includes('Presence')) {
        // Sequence step complete
        result.push(...parseStep(step))
        step = {}
      }
    }
    return result

    function parseStep(step) {
      let result = []
      const cycles = step['Cycle(s)']
      delete step['Cycle(s)']
      for (let i = 0; i < cycles; ++i) {
        result.push(step)
      }
      return result
    }
  },
  preprocess: (acquisitions, parsed) => {
    const app = useApp()
    return parsed.map((parsed, i) => {
      const item = {
        filename: acquisitions[i]?.filename ?? null,
        sample_batch_id: app.data.batch.focused.sample_batch_id,
        filter_id: imported.filterId,
        sample_item_attributes: {}
      }
      Object.entries(parsed).forEach(([key, value]) => {
        const attr = key.toLowerCase().replaceAll(/[\s-]/g, '_')
        if (attr.startsWith('sample_')) {
          // some fields go into the base record
          const prop = `sample_item_${attr.slice(7)}`
          item[prop] = value
        } else {
          // others remain in `attributes`
          item.sample_item_attributes[attr] = value
        }
      })
      return item
    })
  }
}
