<script setup>
import { ref, watch, watchEffect } from 'vue'

import Popover from 'primevue/popover'

import { useMagicKeys, watchDebounced } from '@vueuse/core'
import { useFloating, arrow, offset } from '@floating-ui/vue'

import { useApp } from '@/stores'

const app = useApp()

const targetEl = ref()
const popoverEl = ref()
const arrowEl = ref()

const placement = ref()

const { floatingStyles, x, y, middlewareData } = useFloating(targetEl, popoverEl, {
  placement,
  strategy: 'fixed',
  middleware: [offset(10), arrow({ element: arrowEl })]
})

const visible = ref(false)

watchEffect(() => {
  const card = app.ui.help.current
  if (card && app.ui.help.active) {
    placement.value = card?.placement.replace('_', '-') ?? 'bottom'
    visible.value = true
    targetEl.value = card.element
  } else {
    visible.value = false
  }
})

const border = '1px solid var(--p-panel-border-color)'

// position box
watchEffect((data) => {
  if (popoverEl.value) {
    Object.assign(popoverEl.value.style, {
      top: `${y.value}px`,
      left: `${x.value}px`
    })
  }
})

// position arrow
watchEffect(() => {
  const { arrow } = middlewareData.value
  if (arrow && popoverEl.value) {
    const [position, alignment] = placement.value.split('-')
    let yOffset = 0
    if (alignment == 'start') {
      yOffset = -popoverEl.value.offsetHeight + 2 * arrowEl.value.offsetHeight
    } else if (alignment == 'end') {
      yOffset = popoverEl.value.offsetHeight - 2 * arrowEl.value.offsetHeight
    }

    Object.assign(
      arrowEl.value.style,
      {
        top: {
          left: `${arrow.x}px`,
          top: `${popoverEl.value.offsetHeight - arrowEl.value.offsetHeight / 2}px`,
          border,
          'border-top': 'none',
          'border-left': 'none'
        },
        right: {
          top: `${arrow.y + yOffset}px`,
          left: `${-arrowEl.value.offsetHeight / 2}px`,
          border,
          'border-top': 'none',
          'border-right': 'none'
        },
        bottom: {
          left: `${arrow.x}px`,
          top: `${-arrowEl.value.offsetHeight / 2}px`,
          border,
          'border-bottom': 'none',
          'border-right': 'none'
        },
        left: {
          top: `${arrow.y + yOffset}px`,
          left: `${popoverEl.value.offsetWidth - arrowEl.value.offsetWidth / 2 - 1}px`,
          border,
          'border-bottom': 'none',
          'border-left': 'none'
        }
      }[position]
    )
  }
})

// keybindings
const keys = useMagicKeys()
const combo = keys['alt+h']
watchDebounced(
  combo,
  () => {
    app.ui.help.toggle()
  },
  { debounce: 200 }
)
</script>

<template>
  <div ref="popoverEl" v-if="visible" :style="floatingStyles" class="help-popover">
    <div class="help-content" v-html="app.ui.help.current?.message" />
    <div ref="arrowEl" class="help-popover-arrow"></div>
  </div>
</template>

<style scoped>
.help-popover {
  position: fixed;
  padding: 1rem;
  z-index: 9999;
  border-radius: 0.5rem;
  border: 1px solid var(--p-panel-border-color);
}

.help-popover-arrow {
  position: absolute;
  width: 15px;
  height: 15px;
  transform: rotate(45deg);
}
</style>

<style>
html:not(.darkmode) {
  .help-popover {
    color: var(--p-surface-200);
    background: var(--p-surface-800);
  }

  .help-popover-arrow {
    background: var(--p-surface-800);
  }
}
html.darkmode {
  .help-popover {
    color: var(--p-surface-800);
    background: var(--p-surface-200);
  }
  .help-popover-arrow {
    background: var(--p-surface-200);
  }
}
.help-content {
  max-width: 300px;

  h1 {
    font-size: 1.1rem;
    margin-top: 0.5rem;
  }
  h2 {
    font-size: 1rem;
    margin-top: 0.3rem;
  }
  h3 {
    font-size: 1rem;
    margin-top: 0.1rem;
    font-weight: normal;
    font-style: italic;
  }
}
</style>
