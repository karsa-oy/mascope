import { reactive } from 'vue'
import { defineStore } from 'pinia'

const keymap = {
  AltLeft: 'alt',
  AltRight: 'alt',
  ControlLeft: 'control',
  ControlRight: 'control',
  ShiftLeft: 'shift',
  ShiftRight: 'shift',
  KeyC: 'c',
  KeyV: 'v',
  KeyX: 'x'
}

export const useKeyStore = defineStore('key', () => {
  // state

  const state = reactive({
    shift: false,
    control: false,
    alt: false,
    c: false,
    x: false,
    v: false
  })

  // actions

  function down(event) {
    const key = keymap[event.code]
    if (key && key in state) {
      state[key] = true
    }
  }

  function up(event) {
    const key = keymap[event.code]
    if (key && key in state) {
      state[key] = false
    }
  }

  return { state, up, down }
})
