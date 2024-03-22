export default {
  namespaced: true,
  state: {
    shift: false,
    control: false,
    alt: false,
    c: false,
    x: false,
    v: false,
  },
  mutations: {
    activate(state, key) {
      if (key in state) {
        state[key] = true
      }
    },
    deactivate(state, key) {
      if (key in state) {
        state[key] = false
      }
    },
  },
  actions: {
    down({ commit }, event) {
      let key = mapCodeToKey[event.code]
      if (key) {
        commit('activate', key)
      }
    },
    up({ commit }, event) {
      let key = mapCodeToKey[event.code]
      if (key) {
        commit('deactivate', key)
      }
    },
  },
}

let mapCodeToKey = {
  AltLeft: 'alt',
  AltRight: 'alt',
  ControlLeft: 'control',
  ControlRight: 'control',
  ShiftLeft: 'shift',
  ShiftRight: 'shift',
  KeyC: 'c',
  KeyV: 'v',
}
