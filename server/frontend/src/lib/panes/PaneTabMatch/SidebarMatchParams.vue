<script setup>
import { ref, computed, watchEffect } from 'vue'

import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Slider from 'primevue/slider'
import Menu from 'primevue/menu'
import { useConfirm } from 'primevue/useconfirm'

import { BaseParamField } from '@/lib/base'
import { useApp } from '@/stores'

const confirm = useConfirm()
const app = useApp()

const drawer = ref(false)
const isSaving = ref(false)
const layer = 'sidebar_match_params' // Help-mode layer for drawer

const open = defineModel('open')
watchEffect(() => {
  open.value = drawer.value
  // Set help mode layer when sidebar is opened
  if (drawer.value) {
    app.ui.help.set(layer)
  } else {
    app.ui.help.set(null)
  }
})
const vHelpLayer = app.ui.help.directive(layer)

const key = ref(0)

const summary = computed(
  () =>
    `${app.data.match.visualized.ion.target_ion_formula} match parameters for ${app.data.match.visualized.instrument} instrument`
)

const items = computed(() => [
  {
    label: 'Save parameters',
    icon: 'pi pi-save',
    command: () => {
      confirm.require({
        icon: 'pi pi-info-circle',
        header: 'Saving match parameters',
        message: `Are you sure you want to save ${summary.value}?`,
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
    },
    disabled: !app.data.match.params.changed
  },
  {
    label: 'Set defaults',
    icon: 'pi pi-file-import',
    command: () => {
      app.data.match.params.reset()
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
        message: `Are you sure you want to delete ${summary.value}?`,
        accept: () => {
          app.data.match.params.remove()
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
      app.data.match.visualized.instrument in app.data.match.visualized.ion.filter_params
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
    @click="drawer = true"
  />
  <Drawer
    v-model:visible="drawer"
    header="Match parameters"
    position="left"
    :style="`width: ${app.ui.split.left}vw;`"
    :modal="false"
  >
    <Menu
      :model="items"
      style="border: none"
      :pt="
        app.ui.help.right(
          `
          <h1>Match Parameters: Manage</h1>
          <p>
            Save the current match parameters for the selected ion and instrument.
            These parameters will be used for matching in future sessions.
          </p>
        `,
          { layer }
        )
      "
    />
    <section
      v-help-layer.right="
        `
          <h1>Match Parameters: Isotope settings</h1>
          <p>
            Configure the parameters used for isotope matching.
            <ul>
              <li><strong>m/z tolerance:</strong> The maximum allowed mass error (in ppm) when matching isotopes.</li>
              <li><strong>Min. isotope abundance:</strong> The minimum relative abundance of isotopes to consider when matching.</li>
              <li><strong>Isotope ratio tolerance:</strong> The maximum allowed deviation in expected isotope ratios.</li>
            </ul>
          </p>
        `
      "
    >
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
    </section>
    <section
      v-help-layer.right="
        `
          <h1>Match Parameters: Peak settings</h1>
          <p>
            Configure peak filtering parameters used when matching.
          </p>
        `
      "
    >
      <h3>Peak settings</h3>
      <BaseParamField
        label="Min. peak intensity"
        v-model:param="app.data.match.params.ui.peak_min_intensity"
        @change="app.data.match.visualized.reload"
        :range="{ min: 0, max: 10000, step: 500 }"
        small
        :key="key"
      />
    </section>
    <section
      v-help-layer.right="
        `
          <h1>Match Parameters: Match score thresholds</h1>
          <p>
            Configure the match score thresholds for match categorization.
          </p>
        `
      "
    >
      <h3>Match score thresholds</h3>
      <div class="col" style="gap: 0">
        <div class="row" :key="matchRangeMiddle">
          <!-- NO @change handler - these are UI-only params -->
          <BaseParamField
            label="Possible match [%]"
            v-model:param="app.data.match.params.ui.possible_match_threshold"
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
