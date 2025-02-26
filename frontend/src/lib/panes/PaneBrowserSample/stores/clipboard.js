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
  const data = computed(() => parsed.value?.data)
  const op = computed(() => parsed.value?.op)
  const batch = computed(() => {
    if (isBatch(data.value)) {
      return data.value
    } else {
      return null
    }
  })
  const samples = computed(() => {
    if (Array.isArray(data.value) && data.value?.every(isSample)) {
      return data.value
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

  async function write({ op, data }) {
    if (!op || !['copy', 'cut'].includes(op)) {
      throw Error("clipboard writing must include an 'op' field with value 'copy' or 'cut'")
    }
    try {
      const text = JSON.stringify({ op, data })
      await navigator.clipboard.writeText(text)
    } catch (err) {
      console.warn(err)
    }
  }
  async function copy(data) {
    await write({ op: 'copy', data })
  }
  async function cut(data) {
    await write({ op: 'cut', data })
  }

  async function clear() {
    raw.value = null
  }

  return {
    op,
    batch,
    samples,
    copy,
    cut,
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
