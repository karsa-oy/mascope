<script setup>
import { ref, computed, onMounted } from 'vue'

import { DialogProgrammatic as dialog } from '@ntohq/buefy-next'

import BaseParamField from './BaseParamField.vue'

import { useVisualizationStore } from '@/stores'

const visualizationStore = useVisualizationStore()

const initialParams = ref({})
const isSaving = ref(false)

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
  dialog.confirm({
    title: 'Saving filtering parameters',
    message: `Are you sure you want to save current ${visualizationStore.activeIon.target_ion_formula} filtering parameters for ${visualizationStore.activeIon.instrument} instrument?`,
    confirmText: 'Save',
    hasIcon: true,
    icon: 'content-save',
    onConfirm: async () => {
      isSaving.value = true
      await visualizationStore.saveFilterParams()
      isSaving.value = false
      visualizationStore.storeInitialParams()
      await visualizationStore.loadMatches()
    }
  })
}
function undoChanges() {
  // Revert filter parameters to their initial values
  Object.keys(initialParams.value).forEach((key) => {
    visualizationStore[key] = initialParams.value[key]
  })
}
function filterParamsDelete() {
  dialog.confirm({
    title: 'Deleting filtering parameters',
    message: `Are you sure you want to delete ${visualizationStore.activeIon.target_ion_formula} filtering parameters for ${visualizationStore.activeIon.instrument} instrument?`,
    confirmText: 'Delete',
    type: 'is-danger',
    hasIcon: true,
    icon: 'delete-alert',
    onConfirm: async () => {
      visualizationStore.setDefaultFilterParams()
      await visualizationStore.deleteInstrumentFilterParams()
      await visualizationStore.loadMatches()
      storeInitialParams()
    }
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
</script>

<template>
  <section style="padding: 1em">
    <!-- <h2 class="subtitle">Ion-specific filter parameters</h2> -->
    <base-param-field
      label="m/z tolerance [ppm]"
      v-model:param="visualizationStore.paramMzTolerance"
      @paramChange="reload"
      :range="{ min: 0, max: 100, step: 1 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum isotope abundance"
      v-model:param="visualizationStore.paramMinIsotopeAbundance"
      @paramChange="reload"
      :range="{ min: 0, max: 1, step: 0.01 }"
      disabled
    >
    </base-param-field>
    <base-param-field
      label="Isotope ratio tolerance"
      v-model:param="visualizationStore.paramIsotopeRatioTolerance"
      @paramChange="loadMatches"
      :range="{ min: 0, max: 1, step: 0.05 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum peak intensity"
      v-model:param="visualizationStore.paramPeakMinIntensity"
      @paramChange="reload"
      :range="{ min: 0, max: 10000, step: 500 }"
    >
    </base-param-field>
    <base-param-field
      label="Minimum isotope correlation"
      v-model:param="visualizationStore.paramMinIsotopeCorrelation"
      @paramChange="loadMatches"
      :range="{ min: 0, max: 1, step: 0.1 }"
    >
    </base-param-field>
    <base-param-field
      label="Probable match threshold [%]"
      v-model:param="visualizationStore.paramProbableMatchThreshold"
      @paramChange="onProbableMatchThresholdChange"
      :range="{ min: 0, max: 1, step: 0.1 }"
      type="is-danger"
    >
    </base-param-field>
    <base-param-field
      label="Possible match threshold [%]"
      v-model:param="visualizationStore.paramPossibleMatchThreshold"
      @paramChange="onPossibleMatchThresholdChange"
      :range="{ min: 0, max: 1, step: 0.1 }"
      type="is-warning"
    >
    </base-param-field>
    <div style="display: flex; align-items: center">
      <b-tooltip label="Revert changes" type="is-info" position="is-right" animated>
        <b-button
          icon-right="undo-variant"
          size="is-small"
          :disabled="!paramsChanged"
          @click="undoChanges"
          style="margin-right: 5px"
        >
        </b-button>
      </b-tooltip>

      <b-tooltip label="Set default parameters" type="is-info" position="is-right" animated>
        <b-button
          type="is-dark"
          icon-right="file-restore"
          size="is-small"
          :disabled="isDefaultSettings"
          @click="setDefaultFilterParams"
          style="margin-right: 5px"
        >
        </b-button>
      </b-tooltip>

      <b-tooltip label="Delete filtering parameters" type="is-danger" position="is-right" animated>
        <b-button
          type="is-danger"
          icon-right="delete"
          size="is-small"
          @click="filterParamsDelete"
          :disabled="
            visualizationStore.activeIon?.filter_params &&
            visualizationStore.activeIon.instrument in visualizationStore.activeIon.filter_params
              ? false
              : true
          "
        >
        </b-button>
      </b-tooltip>

      <div class="column is-one-half" style="text-align: right">
        <b-button
          type="is-primary"
          icon-left="content-save"
          :loading="isSaving"
          :disabled="!paramsChanged"
          @click="saveFilterSettings"
          >{{ isSaving ? 'Please wait...' : 'Save filter settings' }}
        </b-button>
      </div>
    </div>
  </section>
</template>
