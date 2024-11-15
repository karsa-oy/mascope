<script setup>
import { reactive, watchEffect, computed, ref } from 'vue'

import Chart from 'primevue/chart'

import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import SelectButton from 'primevue/selectbutton'
import ProgressSpinner from 'primevue/progressspinner'
import Button from 'primevue/button'

import { api } from '@/api'
import { useApp } from '@/stores'
import { BaseParamField } from '@/lib/base'

const app = useApp()

const props = defineProps({
  filename: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['saved'])

const methodfile = ref()
const save = async () => {
  const body = fit.value.instrument_functions
  body.method_file = methodfile.value
  await api.http.post(`/instrument_functions`, body, {
    use: 'create',
    type: 'create_instrument_function'
  })
  emit('saved', methodfile.value)
}

// fit

const threshold = ref() // input
const fit = ref() // output
const loading = ref(true) // state

api.http
  .get('/params', {
    type: 'read_params'
  })
  .then(({ data }) => {
    threshold.value = data?.data?.params.instrument_functions.threshold
  })

watchEffect(async () => {
  if (threshold.value !== undefined) {
    loading.value = true
    await api.http.post(
      `/instrument_functions/fit`,
      {
        filename: props.filename,
        instrument_function_params: {
          threshold: threshold.value
        }
      },
      {
        use: 'process',
        type: 'fit_instrument_function'
      }
    )
  }
})

app.ui.notification.on('instrument_functions_fit', ({ data }) => {
  fit.value = data
  loading.value = false
})

// charts

const chart = ref('Resolution Function')

const peakshape = computed(() => ({
  x: fit.value?.instrument_functions.peakshape.x.map((n) => n.toPrecision(2)),
  y: fit.value?.instrument_functions.peakshape.y
}))

const resolution = computed(() => ({
  datasets: [
    {
      label: 'Resolution function',
      data: fit.value?.statistics.resolution_function.fwhm.map((fwhm, i) => {
        const mz = fit.value?.statistics.resolution_function.mz[i]
        return {
          x: mz,
          y: mz / fwhm
        }
      })
    }
  ]
}))

// validation

const invalid = computed(() => !fit.value || !(methodfile.value?.length > 0))
</script>

<template>
  <menu class="topbar" v-if="threshold !== undefined">
    <BaseParamField
      label="Threshold"
      :range="{
        min: 0,
        max: 0.999,
        step: 0.001
      }"
      hideSlider
      v-model:param="threshold"
      :disabled="loading"
    />
    <FloatLabel>
      <InputText id="methodfile" v-model="methodfile" required />
      <label for="methodfile"> Method file name </label>
    </FloatLabel>
  </menu>
  <div style="position: relative" :class="loading ? 'faded' : ''">
    <div
      style="
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        min-height: 100%;
        z-index: 100;
        display: grid;
        place-items: center;
      "
      v-if="loading"
    >
      <ProgressSpinner />
    </div>
    <div class="row" style="align-items: flex-start; justify-content: space-around" v-if="fit">
      <div class="col" style="gap: 0.5rem">
        <SelectButton
          v-model="chart"
          :options="['Resolution Function', 'Peakshape']"
          :allowEmpty="false"
        />
        <Chart
          v-if="chart == 'Resolution Function'"
          type="scatter"
          class="chart"
          :data="resolution"
          :options="{
            maintainAspectRatio: false,
            scales: {
              x: {
                title: {
                  display: true,
                  text: 'mz'
                }
              },
              y: {
                title: {
                  display: true,
                  text: 'Resolution'
                }
              }
            },
            plugins: {
              legend: {
                display: false
              }
            }
          }"
        />
        <Chart
          v-if="chart == 'Peakshape'"
          type="line"
          class="chart"
          :data="{
            labels: peakshape.x,
            datasets: [
              {
                label: 'Peakshape',
                data: peakshape.y,
                fill: false,
                tension: 0.4
              }
            ]
          }"
          :options="{
            maintainAspectRatio: false,
            scales: {
              x: {
                title: {
                  display: true,
                  text: 'Normalized mz'
                }
              },
              y: {
                title: {
                  display: true,
                  text: 'Normalized Intensity'
                }
              }
            },
            plugins: {
              legend: {
                display: false
              }
            }
          }"
        />
      </div>
      <div class="col" style="padding-top: 3rem">
        <div class="stat">
          <span style="font-size: 2rem">
            {{ fit.statistics.peakshape.num_of_peaks }}
          </span>
          <span> Peaks </span>
        </div>
        <div class="stat">
          <span>
            {{ fit.instrument_functions.datetime_utc.replace('T', ' ') }}
          </span>
          <span> Datetime UTC </span>
        </div>
        <div class="stat">
          <span>
            {{ fit.instrument_functions.instrument }}
          </span>
          <span> Instrument </span>
        </div>
        <menu class="config">
          <Button icon="pi pi-save" label="Save" :disabled="invalid" @click="save" />
        </menu>
      </div>
    </div>
    <div v-else style="height: 250px" />
  </div>
</template>

<style scoped>
.stat {
  display: flex;
  flex-flow: column;
}
.stat > :first-child {
  font-size: 1.2rem;
}

.topbar {
  display: flex;
  flex-flow: row;
  justify-content: flex-start;
}

.topbar :deep(fieldset) {
  flex-grow: 1;
}

.confirm {
  display: flex;
  flex-flow: row;
  justify-content: space-between;
}

.col {
  text-align: center;
  gap: 1.5rem;
}

.chart {
  height: 250px;
  width: 450px;
}

.faded {
  opacity: 0.3;
}
</style>
