import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useClipboard = defineStore('browser.sample.clipboard', () => {
  const raw = ref()
  const parsed = computed(() => {
    if (raw.value) {
      try {
        return JSON.parse(raw.value)
      } catch (err) {
        return null
      }
    }
  })
  const batch = computed(() => {
    if (isBatch(parsed.value)) {
      return parsed.value
    } else {
      return null
    }
  })
  const samples = computed(() => {
    if (parsed.value?.every(isSample)) {
      return parsed.value
    } else {
      return null
    }
  })

  async function read() {
    try {
      raw.value = await navigator.clipboard.readText()
    } catch (err) {
      return
    }
  }

  async function write(data) {
    try {
      const text = JSON.stringify(data)
      await navigator.clipboard.writeText(text)
    } catch (err) {
      console.warn(err)
    }
  }

  async function clear() {
    raw.value = null
  }

  return {
    parsed,
    batch,
    samples,
    write,
    read,
    clear
  }
})

function isBatch(record) {
  return record?.sample_batch_id && !record?.sample_item_id
}

function isSample(record) {
  return record.sample_item_id && record.sample_batch_id && record.sample_item_name
}
