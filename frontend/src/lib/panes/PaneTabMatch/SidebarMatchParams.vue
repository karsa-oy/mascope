<script setup>
import { ref, computed, watch, watchEffect, onMounted } from 'vue'

import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Slider from 'primevue/slider'
import Menu from 'primevue/menu'
import { useConfirm } from 'primevue/useconfirm'

import { BaseParamField } from '@/lib/base'
import { api } from '@/api'
import { useApp } from '@/stores'

const confirm = useConfirm()
const app = useApp()

const drawer = ref(false)
const isSaving = ref(false)

const open = defineModel('open')
watchEffect(() => {
  open.value = drawer.value
})

const key = ref(0)
const refresh = () => {
  key.value = Math.random()
}

const items = computed(() => [
  {
    label: 'Save parameters',
    icon: 'pi pi-save',
    command: () => {
      confirm.require({
        icon: 'pi pi-info-circle',
        header: 'Saving match parameters',
        message: `Are you sure you want to save current ${app.data.match.visualized.ion.target_ion_formula} match parameters for ${app.data.match.visualized.ion.instrument} instrument?`,
        accept: async () => {
          isSaving.value = true
          await app.data.match.params.save()
          isSaving.value = false
        },
        acceptProps: {
          icon: 'pi pi-save',
          label: 'Save'
        },
        rejectProps: {
          icon: 'pi pi-times',
          label: 'Cancel',
          severity: 'secondary'
        }
      })
    },
    disabled: !app.data.match.params.changed
  },
  {
    label: 'Revert changes',
    icon: 'pi pi-undo',
    command: () => {
      app.data.match.params.revert()
      refresh()
    },
    disabled: !app.data.match.params.changed
  },
  {
    label: 'Set defaults',
    icon: 'pi pi-file-import',
    command: () => {
      app.data.match.params.reset()
      refresh()
    },
    disabled: app.data.match.params.default
  },
  {
    label: 'Delete filtering parameters',
    icon: 'pi pi-trash',
    command: () => {
      confirm.require({
        icon: 'pi pi-exclamation-triangle',
        header: 'Deleting match parameters',
        message: `Are you sure you want to delete ${app.data.match.visualized.ion?.target_ion_formula} match parameters for ${app.data.match.visualized.ion?.instrument} instrument?`,
        accept: () => {
          app.data.match.params.remove()
          refresh()
        },
        acceptProps: {
          icon: 'pi pi-trash',
          label: 'Delete',
          severity: 'danger'
        },
        rejectProps: {
          icon: 'pi pi-times',
          label: 'Cancel',
          severity: 'secondary'
        }
      })
    },
    disabled:
      app.data.match.visualized.ion?.filter_params &&
      app.data.match.visualized.ion?.instrument in app.data.match.visualized.ion.filter_params
        ? false
        : true
  }
])

const possibleMatchRange = computed({
  get() {
    return [
      app.data.match.params.ui.possible_match_threshold,
      app.data.match.params.ui.probable_match_threshold
    ]
  },
  set([a, b]) {
    let possible, probable
    if (a < b) {
      possible = a
      probable = b
    } else if (b <= a) {
      possible = b
      probable = a
    }
    app.data.match.params.ui.possible_match_threshold = possible
    app.data.match.params.ui.probable_match_threshold = probable
  }
})

const matchRangeMiddle = computed(
  () =>
    (100 *
      (app.data.match.params.ui.possible_match_threshold +
        app.data.match.params.ui.probable_match_threshold)) /
    2
)
</script>

<template>
  <Button
    v-tooltip.bottom="'Match parameters'"
    icon="pi pi-sliders-h"
    severity="secondary"
    text
    @click="
      (event) => {
        drawer = true
      }
    "
  />
  <Drawer
    v-model:visible="drawer"
    header="Match parameters"
    position="left"
    :style="`width: ${app.ui.split.left}vw;`"
    :modal="false"
  >
    <Menu :model="items" style="border: none" />
    <section>
      <h3>Isotope settings</h3>
      <BaseParamField
        label="m/z tolerance [ppm]"
        v-model:param="app.data.match.params.ui.mz_tolerance"
        @change="app.data.match.visualized.reload"
        :range="{ min: 0, max: 100, step: 1 }"
        small
        :key="key"
      />
      <BaseParamField
        label="Min. isotope abundance"
        v-model:param="app.data.match.params.ui.min_isotope_abundance"
        @change="app.data.match.visualized.reload"
        :range="{ min: 0, max: 1, step: 0.01 }"
        disabled
        col
        small
        :key="key"
      />
      <BaseParamField
        label="Isotope ratio tolerance"
        v-model:param="app.data.match.params.ui.isotope_ratio_tolerance"
        @change="app.data.match.visualized.reload"
        :range="{ min: 0, max: 1, step: 0.05 }"
        small
        :key="key"
      />
      <BaseParamField
        label="Min. isotope correlation"
        v-model:param="app.data.match.params.ui.min_isotope_correlation"
        @change="app.data.match.visualized.reload"
        :range="{ min: 0, max: 1, step: 0.1 }"
        small
        :key="key"
      />
    </section>
    <section>
      <h3>Peak settings</h3>
      <BaseParamField
        label="Min. peak intensity"
        v-model:param="app.data.match.params.ui.peak_min_intensity"
        @change="app.data.match.visualized.reload"
        :range="{ min: 0, max: 10000, step: 500 }"
        small
        :key="key"
      />
      <div class="col" style="gap: 0">
        <div class="row" :key="matchRangeMiddle">
          <BaseParamField
            label="Possible match [%]"
            v-model:param="app.data.match.params.ui.possible_match_threshold"
            @change="app.data.match.visualized.reload"
            :range="{
              min: 0,
              max: app.data.match.params.ui.probable_match_threshold,
              step: 0.05
            }"
            hideSlider
            small
            :key="key"
          />
          <BaseParamField
            label="Probable match [%]"
            v-model:param="app.data.match.params.ui.probable_match_threshold"
            @change="app.data.match.visualized.reload"
            :range="{
              min: app.data.match.params.ui.possible_match_threshold,
              max: 1,
              step: 0.05
            }"
            hideSlider
            small
            :key="key"
          />
        </div>
        <div style="width: 100%; margin-top: 1rem" class="match-slider">
          <Slider
            v-model="possibleMatchRange"
            range
            :min="0"
            :max="1"
            :step="0.05"
            :style="`background: linear-gradient(90deg, var(--p-button-success-background) ${matchRangeMiddle}%, var(--p-button-danger-background) ${matchRangeMiddle}%)`"
            :key="key"
          />
        </div>
      </div>
    </section>
  </Drawer>
</template>

<style scoped>
section:not(:first-child) {
  margin-top: 1rem;
  border-top: 1px solid var(--p-drawer-border-color);
}
:deep(fieldset) {
  flex-flow: row nowrap;
  align-items: center;
  gap: 1rem;
  padding: 0;
  margin: 1rem;
}

.match-slider {
  :deep(.p-slider-range) {
    background: var(--p-button-warn-background);
  }

  :deep(.p-slider) {
    background: red !important;
  }
}
</style>
