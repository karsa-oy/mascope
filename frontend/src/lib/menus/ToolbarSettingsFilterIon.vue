<script setup>
import { ref, computed, onMounted } from 'vue'

import ContextMenu from 'primevue/contextmenu'
import Popover from 'primevue/popover'

import { useConfirm } from 'primevue/useconfirm'

import BaseParamField from '@/lib/base/BaseParamField.vue'

import { useVisualizationStore } from '@/stores'

const confirm = useConfirm()

const visualizationStore = useVisualizationStore()

const menu = ref()
const initialParams = ref({})
const isSaving = ref(false)

const isotopeSettings = ref()
const peakSettings = ref()

const paramsChanged = computed(() => {
  // Check if any parameter has changed
  return Object.keys(initialParams.value).some((key) => {
    return initialParams.value[key] !== visualizationStore[key]
  })
})
const isDefaultSettings = computed(() => {
  return Object.keys(visualizationStore.defaultFilterParams).every((key) => {
    return visualizationStore[key] === visualizationStore.defaultFilterParams[key]
  })
})

function onProbableMatchThresholdChange() {
  if (
    visualizationStore.paramProbableMatchThreshold < visualizationStore.paramPossibleMatchThreshold
  ) {
    visualizationStore.paramPossibleMatchThreshold = visualizationStore.paramProbableMatchThreshold
  }
  visualizationStore.loadMatches()
}
function onPossibleMatchThresholdChange() {
  if (
    visualizationStore.paramProbableMatchThreshold < visualizationStore.paramPossibleMatchThreshold
  ) {
    visualizationStore.paramProbableMatchThreshold = visualizationStore.paramPossibleMatchThreshold
  }
  visualizationStore.loadMatches()
}

async function saveFilterSettings() {
  confirm.require({
    header: 'Saving filtering parameters',
    message: `Are you sure you want to save current ${visualizationStore.activeIon.target_ion_formula} filtering parameters for ${visualizationStore.activeIon.instrument} instrument?`,
    acceptIcon: 'pi pi-save',
    acceptLabel: 'Save',
    accept: async () => {
      isSaving.value = true
      await visualizationStore.saveFilterParams()
      isSaving.value = false
      visualizationStore.storeInitialParams()
      await visualizationStore.loadMatches()
    },
    rejectLabel: 'Cancel',
    rejectIcon: 'pi pi-times'
  })
}
function undoChanges() {
  // Revert filter parameters to their initial values
  Object.keys(initialParams.value).forEach((key) => {
    visualizationStore[key] = initialParams.value[key]
  })
}
function filterParamsDelete() {
  confirm.require({
    header: 'Deleting filtering parameters',
    message: `Are you sure you want to delete ${visualizationStore.activeIon.target_ion_formula} filtering parameters for ${visualizationStore.activeIon.instrument} instrument?`,
    acceptIcon: 'pi pi-trash',
    acceptLabel: 'Delete',
    accept: async () => {
      visualizationStore.setDefaultFilterParams()
      await visualizationStore.deleteInstrumentFilterParams()
      await visualizationStore.loadMatches()
      storeInitialParams()
    },
    rejectLabel: 'Cancel',
    rejectIcon: 'pi pi-times'
  })
}
function storeInitialParams() {
  initialParams.value = {
    paramMzTolerance: visualizationStore.paramMzTolerance,
    paramMinIsotopeAbundance: visualizationStore.paramMinIsotopeAbundance,
    paramIsotopeRatioTolerance: visualizationStore.paramIsotopeRatioTolerance,
    paramPeakMinIntensity: visualizationStore.paramPeakMinIntensity,
    paramMinIsotopeCorrelation: visualizationStore.paramMinIsotopeCorrelation,
    paramProbableMatchThreshold: visualizationStore.paramProbableMatchThreshold,
    paramPossibleMatchThreshold: visualizationStore.paramPossibleMatchThreshold
  }
}

onMounted(() => {
  storeInitialParams()
})

const items = computed(() => [
  {
    label: 'Save params',
    icon: 'pi pi-save',
    command: saveFilterSettings,
    disabled: !paramsChanged.value
  },
  {
    label: 'Revert changes',
    icon: 'pi pi-undo',
    command: undoChanges,
    disabled: !paramsChanged.value
  },
  {
    label: 'Set defaults',
    icon: 'pi pi-file-import',
    command: visualizationStore.setDefaultFilterParams,
    disabled: isDefaultSettings.value
  },
  {
    label: 'Delete filtering params',
    icon: 'pi pi-trash',
    command: filterParamsDelete,
    disabled:
      visualizationStore.activeIon?.filter_params &&
      visualizationStore.activeIon.instrument in visualizationStore.activeIon.filter_params
        ? false
        : true
  }
])
</script>

<template>
  <menu class="k-settings-filter-ion row">
    <Button
      v-tooltip.bottom="'Save & restore settings'"
      icon="pi pi-ellipsis-h"
      :loading="isSaving"
      severity="secondary"
      @click="
        (event) => {
          menu.show(event)
        }
      "
    />
    <ContextMenu ref="menu" :model="items" />
    <Button
      v-tooltip.bottom="'Isotope settings'"
      severity="secondary"
      @click="
        (event) => {
          isotopeSettings.toggle(event)
        }
      "
    >
      <template #icon>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          fill="currentColor"
          viewBox="0 0 256 256"
        >
          <path
            d="M196.12,128c24.65-34.61,37.22-70.38,19.74-87.86S162.61,35.23,128,59.88C93.39,35.23,57.62,22.66,40.14,40.14S35.23,93.39,59.88,128c-24.65,34.61-37.22,70.38-19.74,87.86h0c5.63,5.63,13.15,8.14,21.91,8.14,18.48,0,42.48-11.17,66-27.88C151.47,212.83,175.47,224,194,224c8.76,0,16.29-2.52,21.91-8.14h0C233.34,198.38,220.77,162.61,196.12,128Zm8.43-76.55c7.64,7.64,2.48,32.4-18.52,63.28a300.33,300.33,0,0,0-21.19-23.57A300.33,300.33,0,0,0,141.27,70C172.15,49,196.91,43.8,204.55,51.45ZM176.29,128a289.14,289.14,0,0,1-22.76,25.53A289.14,289.14,0,0,1,128,176.29a289.14,289.14,0,0,1-25.53-22.76A289.14,289.14,0,0,1,79.71,128,298.62,298.62,0,0,1,128,79.71a289.14,289.14,0,0,1,25.53,22.76A289.14,289.14,0,0,1,176.29,128ZM51.45,51.45c2.2-2.21,5.83-3.35,10.62-3.35C73.89,48.1,92.76,55,114.72,70A304,304,0,0,0,91.16,91.16,300.33,300.33,0,0,0,70,114.73C49,83.85,43.81,59.09,51.45,51.45Zm0,153.1C43.81,196.91,49,172.15,70,141.27a300.33,300.33,0,0,0,21.19,23.57A304.18,304.18,0,0,0,114.73,186C83.85,207,59.09,212.2,51.45,204.55Zm153.1,0c-7.64,7.65-32.4,2.48-63.28-18.52a304.18,304.18,0,0,0,23.57-21.19A300.33,300.33,0,0,0,186,141.27C207,172.15,212.19,196.91,204.55,204.55ZM140,128a12,12,0,1,1-12-12A12,12,0,0,1,140,128Z"
          ></path>
        </svg>
      </template>
    </Button>
    <Popover ref="isotopeSettings">
      <div class="row" style="padding: 1rem; gap: 0.5rem">
        <BaseParamField
          label="m/z tolerance [ppm]"
          v-model:param="visualizationStore.paramMzTolerance"
          @change="visualizationStore.reload"
          :range="{ min: 0, max: 100, step: 1 }"
        />
        <BaseParamField
          label="Min. isotope abundance"
          v-model:param="visualizationStore.paramMinIsotopeAbundance"
          @change="visualizationStore.reload"
          :range="{ min: 0, max: 1, step: 0.01 }"
          disabled
          col
        />
        <BaseParamField
          label="Isotope ratio tolerance"
          v-model:param="visualizationStore.paramIsotopeRatioTolerance"
          @change="visualizationStore.loadMatches"
          :range="{ min: 0, max: 1, step: 0.05 }"
        />
        <BaseParamField
          label="Min. isotope correlation"
          v-model:param="visualizationStore.paramMinIsotopeCorrelation"
          @change="visualizationStore.loadMatches"
          :range="{ min: 0, max: 1, step: 0.1 }"
        />
      </div>
    </Popover>
    <Button
      v-tooltip.bottom="'Peak settings'"
      icon="pi pi-trash"
      severity="secondary"
      @click="
        (event) => {
          peakSettings.toggle(event)
        }
      "
    >
      <template #icon>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          fill="currentColor"
          viewBox="0 0 256 256"
        >
          <path
            d="M136,40V216a8,8,0,0,1-16,0V40a8,8,0,0,1,16,0ZM96,120H35.31l18.35-18.34A8,8,0,0,0,42.34,90.34l-32,32a8,8,0,0,0,0,11.32l32,32a8,8,0,0,0,11.32-11.32L35.31,136H96a8,8,0,0,0,0-16Zm149.66,2.34-32-32a8,8,0,0,0-11.32,11.32L220.69,120H160a8,8,0,0,0,0,16h60.69l-18.35,18.34a8,8,0,0,0,11.32,11.32l32-32A8,8,0,0,0,245.66,122.34Z"
          ></path>
        </svg>
      </template>
    </Button>
    <Popover ref="peakSettings">
      <div class="row" style="padding: 1rem; gap: 0.5rem">
        <BaseParamField
          label="Min. peak intensity"
          v-model:param="visualizationStore.paramPeakMinIntensity"
          @change="visualizationStore.reload"
          :range="{ min: 0, max: 10000, step: 500 }"
        />
        <BaseParamField
          label="Possible match [%]"
          v-model:param="visualizationStore.paramPossibleMatchThreshold"
          @change="onPossibleMatchThresholdChange"
          :range="{ min: 0, max: 1, step: 0.1 }"
        />
        <BaseParamField
          label="Probable match [%]"
          v-model:param="visualizationStore.paramProbableMatchThreshold"
          @change="onProbableMatchThresholdChange"
          :range="{ min: 0, max: 1, step: 0.1 }"
        />
      </div>
    </Popover>
  </menu>
</template>

<style scoped>
.k-settings-filter-ion {
  padding: 0;
  z-index: 100;
}
:deep(fieldset) {
  flex-flow: column nowrap;
  align-items: stretch;
  gap: 0.5rem;
}
</style>
