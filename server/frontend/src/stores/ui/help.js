import { ref, computed, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { useMouseInElement, watchDebounced } from '@vueuse/core'

import { genId } from '@/lib/utils'

export const useHelp = defineStore('app.ui.help', () => {
  const active = ref(false)
  const layer = ref(null)
  const cards = ref([])
  const roots = ref([])
  const current = ref()
  const event = ref()

  const toggle = () => {
    active.value = !active.value
  }
  watchEffect(() => {
    if (active.value) {
      document.documentElement.classList.add('disable-tooltips')
    } else {
      document.documentElement.classList.remove('disable-tooltips')
    }
  })

  const set = (current) => {
    layer.value = current
  }

  const register = (element, args) => {
    const { isOutside } = useMouseInElement(element)
    cards.value.push({ element, isOutside, ...args })
  }

  // hook into HTML elmenents:
  // v-help accepts either a string (the message) or an object
  //   { message, doc } where `doc` is an optional URL the popover links to
  //   ("Learn more"). Keep popover text short and put longer explanations in
  //   the docs site, linked via `doc` -- see docs/USER_DOCS_PLAN.md.
  const directive = (layer = 'default') => ({
    mounted: (element, { value, modifiers }) => {
      const [placement] = Object.keys(modifiers)
      const { message, doc } =
        value && typeof value === 'object' ? value : { message: value, doc: null }
      register(element, { placement, message, doc, layer })
    }
  })
  // hook into components:
  const pt = (args) => {
    const rootId = `help-${genId(8)}`
    roots.value.push([rootId, args])
    return {
      root: { id: rootId },
      hooks: {
        onMounted: () => {
          const element = document.getElementById(rootId)
          console.debug('🛟 [help] registering element', rootId, { args, element })
          register(element, args)
        }
      }
    }
  }

  const positions = ['right', 'left', 'top', 'bottom']
  const alignments = [null, 'start', 'end']

  const ptApi = {}
  positions.forEach((position) => {
    alignments.forEach((alignment) => {
      // create an API that combines position and alignment
      const placement = [position, alignment].filter((x) => x !== null).join('_')
      ptApi[placement] = (message, options = { layer: 'default' }) =>
        pt({ placement, message, ...options })
    })
  })

  const buffer = computed(() => {
    // Only consider cards whose element is still in the DOM
    const active = cards.value.filter(
      (card) =>
        card.layer == (layer.value ?? 'default') &&
        card.element &&
        document.body.contains(card.element)
    )
    // filter to select cards containing the mouse
    const hovered = active.filter(({ isOutside }) => !isOutside)
    // select the lowest element in the containment hierarchy
    return hovered.sort(containment)[0]
  })
  watchDebounced(
    buffer,
    (card) => {
      current.value = card
    },
    { debounce: 300 }
  )

  return {
    active,
    cards,
    current,
    event,
    toggle,
    set,
    layer,
    // hooks
    directive,
    pt,
    ...ptApi
  }
})

function containment(a, b) {
  if (a?.element && b?.element) {
    if (a.element.contains(b.element)) {
      return 1
    }
    if (b.element.contains(a.element)) {
      return -1
    }
  }
  return 0
}
