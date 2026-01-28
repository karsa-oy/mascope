<script setup>
import FloatLabel from 'primevue/floatlabel'
import Slider from 'primevue/slider'
import InputNumber from 'primevue/inputnumber'

import { ref, watch } from 'vue'

import { debounce } from '@/lib/utils'

const props = defineProps({
  disabled: {
    type: Boolean,
    required: false,
    default: false
  },
  label: {
    type: String,
    required: true
  },
  range: {
    type: Object,
    required: false,
    default() {
      return { min: 0, max: 1, step: 0.01 }
    }
  },
  hideSlider: {
    type: Boolean,
    default: false
  },
  small: {
    type: Boolean,
    default: false
  }
})

const id = props.label.trim().replaceAll(/\s+/g, '-')

const param = defineModel('param')

const inner = ref(param.value)

watch(
  inner,
  debounce(() => {
    param.value = inner.value
  })
)

const emit = defineEmits(['change'])
watch(param, (value) => {
  if (value !== null) {
    inner.value = value
    emit('change')
  }
})
</script>

<template>
  <fieldset>
    <FloatLabel>
      <InputNumber
        v-model="inner"
        :id="id"
        showButtons
        :min="range.min"
        :max="range.max"
        :step="range.step"
        :disabled="disabled"
        :maxFractionDigits="3"
        :allowEmpty="false"
        :size="small ? 'small' : 'large'"
      />
      <label :for="id"> {{ label }}</label>
    </FloatLabel>
    <Slider
      v-if="!hideSlider"
      v-model="inner"
      :min="range.min"
      :max="range.max"
      :step="range.step"
      :disabled="disabled"
    />
  </fieldset>
</template>

<style scoped>
fieldset {
  display: flex;
  flex-flow: row nowrap;
  gap: 2rem;
  align-items: center;
  justify-content: space-between;
  border: 0;
  margin: 2rem 0;
}

fieldset > :deep(.p-slider) {
  flex-grow: 1;
}
</style>
