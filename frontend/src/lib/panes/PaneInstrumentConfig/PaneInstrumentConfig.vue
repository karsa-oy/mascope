<script setup>
import { reactive, watchEffect, watch, computed, ref, onMounted } from 'vue'

import Chart from 'primevue/chart'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import Button from 'primevue/button'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'

import { api } from '@/api'
import { useApp } from '@/stores'
import { BaseParamField } from '@/lib/base'
import { glasbey } from '@/lib/charts/colors.js'

const MAX_CONFIG_NAME_LENGTH = 32

const app = useApp()

const props = defineProps({
  fitTo: {
    type: [String, Array],
    required: true
  },
  autofit: {
    type: Boolean,
    default: false
  },
  invalidateUnchanged: {
    type: Boolean,
    default: false
  }
})

const status = defineModel('status')
const input = defineModel('input')
const payload = defineModel('payload')

const sampleFile = ref()
const threshold = ref()
const multifile = ref(false)
const error = ref(null)

const selectable = computed(() => input.value.options?.length > 0)
const instrument = computed(() =>
  app.data.instrument.list.find(({ instrument }) => instrument == sampleFile.value.instrument)
)
const instrumentType = computed(() => (sampleFile.value ? instrument.value?.type : null))

// init filename
if (typeof props.fitTo == 'string') {
  input.value.filename = props.fitTo
} else if (Array.isArray(props.fitTo)) {
  input.value.filename = props.fitTo[0]
  multifile.value = true
}

// load initial data
api.http
  .get(`/sample/files`, {
    params: {
      filename: input.value.filename
    },
    use: 'read',
    type: 'get_sample_file'
  })
  .then(([sample_file]) => {
    sampleFile.value = sample_file
    // load instrument configs
    api.http
      .get(`/instrument_configs`, {
        params: {
          filename: input.value.filename
        },
        use: 'read',
        type: 'load_instrument_configs'
      })
      .then((instrument_configs) => {
        if (instrument_configs?.length > 0) {
          // populate options
          input.value.options = instrument_configs
          // resolve current config (if valid)
          const sampleFileConfig = sample_file.method_file
          const sampleFileConfigValid = instrument_configs
            .map(({ method_file }) => method_file)
            .includes(sampleFileConfig)
          const currentConfig = sampleFileConfigValid ? sampleFileConfig : null
          // find the latest config
          const latestConfig = instrument_configs.sort((a, b) =>
            a.datetime_utc < b.datetime_utc ? -1 : a.datetime_utc > b.datetime_utc ? 1 : 0
          )[0]?.method_file
          // autoselect initial config
          const initialConfig = currentConfig ?? latestConfig
          input.value.selected = instrument_configs.find(
            ({ method_file }) => method_file == initialConfig
          )
        }
        // initialize other values
        input.value.new = {
          method_file: null
        }
        input.value.creating = !selectable.value
        // mark ready
        input.value.ready = true
      })
  })
api.http
  .get('/params', {
    type: 'read_params'
  })
  .then(({ data }) => {
    threshold.value = data?.data?.params.instrument_config.threshold
  })

// fit

const fitting = ref(null)
const updateFit = ref()
const previous = reactive({
  threshold: null,
  filename: null
})

const inputChanged = computed(
  () => threshold.value !== previous.threshold || input.value.filename !== previous.filename
)
const readyToFit = computed(
  () =>
    props.autofit && // autofit enabled from parent context
    threshold.value !== undefined // threshold value initialized
)
const missingFit = computed(() => !input.value?.new)
const invalidatedFit = computed(
  () =>
    !fitting.value && // no current fit is ongoing
    inputChanged.value // threshold or filename changed
)
const shouldRefit = computed(() => readyToFit.value && (missingFit.value || invalidatedFit.value))

const refit = async () => {
  if (shouldRefit.value) {
    fitting.value = true
    const prev = {
      threshold: input.value.creating ? threshold.value : null,
      filename: input.value.filename
    }
    await api.http.post(
      `/instrument_configs/fit`,
      {
        filename: input.value.filename,
        instrument_config_params: {
          threshold: threshold.value
        }
      },
      {
        use: 'process',
        type: 'fit_instrument_functions'
      }
    )
    previous.threshold = prev.threshold
    previous.filename = prev.filename
  }
}

// autorefit when conditions are met
watch(
  [
    inputChanged, // param changed
    () => input.value.creating, // toggle mode
    () => props.autofit // context change
  ],
  refit
)
// handle autorefit response
app.ui.notification
  .on('fit_instrument_config', (resp) => {
    if (resp?.data) {
      input.value.new = {
        ...input.value.new,
        ...resp.data.instrument_functions
      }
      input.value.statistics = resp.data.statistics
    }
    if (resp?.error) {
      error.value = {
        severity: 'error',
        contents: resp?.message,
        icon: 'pi pi-exclamation-triangle'
      }
    } else {
      error.value = null
    }
    fitting.value = false
  })
  .unmount()

// resolution function equations
const rTof = (a, b) => (mz) => mz / (a * mz + b)
const rOrbi = (a) => (mz) => a / Math.sqrt(mz)

const fitDetails = computed(() => {
  const params = input.value.creating
    ? input.value.new?.resolution_function
    : input.value.selected?.resolution_function
  let fit, equation, a, b
  if (params) {
    if (instrumentType.value == 'tof') {
      ;[a, b] = params
      fit = rTof(a, b)
      equation = 'mz / (a * mz + b)'
    } else if (instrumentType.value == 'orbi') {
      ;[a] = params
      fit = rOrbi(a)
      equation = 'a / sqrt(mz)'
    }
  }
  return {
    fit,
    equation,
    a,
    b
  }
})

// charts

const theme = computed(() => (app.ui.darkmode.active ? glasbey.dark : glasbey.light))
const newFitColor = computed(() => theme.value[3])

const resolutionChartData = computed(() => {
  const { fwhm, mz } = input.value?.statistics.resolution_function
  mz.sort((a, b) => a - b)

  return {
    labels: mz,
    datasets: [
      {
        type: 'scatter',
        label: 'Data',
        data: fwhm.map((fwhm, i) => {
          const x = mz[i]
          return {
            x,
            y: x / fwhm
          }
        }),
        backgroundColor: newFitColor.value
      },
      ...(fitDetails.value?.fit
        ? [
            {
              type: 'line',
              label: 'Fit',
              data: mz.map(fitDetails.value.fit),
              borderColor: newFitColor.value,
              pointStyle: false
            }
          ]
        : [])
    ]
  }
})

const peakshapeChartData = computed(() => {
  const config = input.value.creating ? input.value.new : input.value.selected
  const labels = config?.peakshape?.x.map((n) => n.toPrecision(3)) ?? []
  const datasets = []
  if (config?.peakshape) {
    const points = config.peakshape.x
      .map((x, i) => ({ x, i }))
      .map(({ x, i }) => ({ x: x.toPrecision(3), y: config.peakshape.y[i] }))
      .filter(({ x }) => labels.includes(x))
    datasets.push({
      label: 'Peakshape',
      data: points.map(({ y }) => y),
      fill: false,
      pointStyle: false,
      tension: 0.4,
      borderColor: newFitColor.value
    })
  }
  return {
    labels,
    datasets
  }
})

// validation

const configNameExists = computed(
  () =>
    input.value.options
      ?.map(({ method_file }) => method_file)
      .includes(input.value.new?.method_file) ?? false
)
const configNameMissing = computed(() => !(input.value.new?.method_file?.trim()?.length > 0))
const configNameTooLong = computed(
  () => input.value.new?.method_file?.trim()?.length > MAX_CONFIG_NAME_LENGTH
)
const configUnchanged = computed(
  () => sampleFile.value?.method_file == input.value.selected?.method_file
)

const invalidConfigCreate = computed(
  () =>
    input.value.creating &&
    (configNameExists.value || configNameMissing.value || configNameTooLong.value)
)
const invalidConfigUpdate = computed(
  () =>
    props.invalidateUnchanged && // changing is required
    !input.value.creating && // using an existing instrument config
    configUnchanged.value && // instrument config has not been changed
    !updateFit.value // fit has not been updated
)

const message = computed(() => {
  const missing = configNameMissing.value ? 'Instrument config name is required' : null
  const tooLong = configNameTooLong.value
    ? `Instrument config name is longer than ${MAX_CONFIG_NAME_LENGTH} characters`
    : null
  const existing = configNameExists.value ? 'Instrument config name already exists' : null
  const contents = missing ?? tooLong ?? existing
  const warning =
    input.value.statistics && input.value?.creating && contents
      ? {
          severity: 'warn',
          icon: 'pi pi-exclamation-triangle',
          contents
        }
      : null
  return error.value ?? warning
})

// sync status v-model
watchEffect(() => {
  status.value = {
    fitting: fitting.value,
    invalid: invalidConfigCreate.value || invalidConfigUpdate.value || (error.value ?? false),
    selectable: selectable.value,
    message: message.value
  }
})

// output

// sync payload v-model
watchEffect(() => {
  payload.value = input.value.creating
    ? {
        filename: input.value.filename,
        instrument_config: {
          new_record: input.value.new
        }
      }
    : {
        filename: input.value.filename,
        instrument_config: {
          instrument_function_id: input.value.selected?.instrument_function_id
        }
      }
})
</script>

<template>
  <!-- inputs -->
  <menu
    class="topbar"
    v-if="threshold !== undefined && input?.ready"
    style="padding: 0.5rem 1rem; padding-bottom: 0"
  >
    <div class="row">
      <FloatLabel v-if="!input.creating">
        <Select
          v-model="input.selected"
          :options="input.options"
          optionLabel="method_file"
          id="instrument-config-option"
        />
        <label for="instrument-config-option">Config</label>
      </FloatLabel>
      <template v-else>
        <FloatLabel>
          <InputText id="instrument-config-name" v-model="input.new.method_file" required />
          <label for="instrument-config-name"> Config </label>
        </FloatLabel>
        <BaseParamField
          label="Threshold"
          :range="{
            min: 0,
            max: 0.999,
            step: 0.001
          }"
          hideSlider
          v-model:param="threshold"
          :disabled="fitting"
        />
      </template>
    </div>
    <FloatLabel v-if="multifile && input.creating" v-tooltip="input.filename">
      <Select v-model="input.filename" :options="fitTo" id="select-file" style="max-width: 300px" />
      <label for="select-file"> Fit target </label>
    </FloatLabel>
    <SelectButton
      v-model="input.creating"
      :options="[
        {
          tooltip: 'Use existing',
          label: 'Pick',
          value: false,
          disabled: !selectable,
          icon: 'pi pi-search'
        },
        {
          tooltip: 'Create new',
          label: 'Create',
          value: true,
          disabled: false,
          icon: 'pi pi-plus'
        }
      ]"
      optionLabel="tooltip"
      optionValue="value"
      optionDisabled="disabled"
      dataKey="label"
      :allowEmpty="false"
    >
      <template #option="{ option }">
        <div style="z-index: 100" :class="option.icon" />
        <span>{{ option.label }}</span>
      </template>
    </SelectButton>
  </menu>
  <div style="position: relative" :class="fitting ? 'faded' : ''">
    <!-- charts -->
    <div class="spinner-overlay" v-if="fitting">
      <ProgressSpinner />
    </div>
    <div class="error-overlay" v-if="error">
      <section>
        <h4>Fit failed</h4>
        <p>Adjust the parameters and try again</p>
      </section>
    </div>
    <div
      class="col"
      style="align-items: center; justify-content: space-around; gap: 0.5rem"
      v-if="input?.statistics"
    >
      <div class="row" style="gap: 0.5rem">
        <Chart
          class="chart"
          :data="resolutionChartData"
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
              title: { display: true, text: 'Resolution function fit' },
              legend: { display: false }
            },
            animation: { duration: 0 }
          }"
        />
        <Chart
          type="line"
          class="chart"
          :data="peakshapeChartData"
          :options="{
            maintainAspectRatio: false,
            scales: {
              x: {
                title: {
                  display: true,
                  text: 'Normalized mz'
                },
                ticks: {
                  autoSkip: true,
                  maxTicksLimit: 11
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
              title: {
                display: true,
                text: input.creating
                  ? `Peakshape (median of ${input?.statistics.peakshape.num_of_peaks})`
                  : 'Peakshape'
              },
              legend: { display: false }
            },
            animation: { duration: 0 }
          }"
        />
      </div>
      <!-- stats bar -->
      <div class="row" style="justify-content: space-around; width: 100%">
        <div class="stat">
          <span>{{ fitDetails.equation }} </span>
          <span>Formula</span>
        </div>
        <div class="stat" v-if="fitDetails?.a">
          <span>{{ fitDetails?.a?.toExponential(2) }} </span>
          <span>a</span>
        </div>
        <div class="stat" v-if="fitDetails?.b">
          <span>{{ fitDetails?.b?.toExponential(2) }} </span>
          <span>b</span>
        </div>
        <div class="stat">
          <span>
            {{ input.new?.instrument }}
          </span>
          <span> Instrument </span>
        </div>
        <div class="stat">
          <span>
            {{ input.new?.datetime_utc?.replace('T', ' ') }}
          </span>
          <span> Datetime UTC </span>
        </div>
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
  justify-content: space-between;
  aling-items: flex-end;
  padding-top: 0.5rem;
}

.topbar :deep(fieldset) {
  padding: 0;
}

.topbar :deep(*) {
  min-width: 0;
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
  width: 400px;
}

.spinner-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 300px;
  z-index: 100;
  display: grid;
  place-items: center;
}
.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 300px;
  z-index: 100;
  display: flex;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);

  section {
    margin-top: 100px;
    text-align: center;
  }
}

.faded {
  opacity: 0.3;
}

:deep(.p-inputtext) {
  width: 150px;
}
:deep(.p-inputnumber) {
  width: 100px;
}
:deep(.p-select) {
  width: 150px;
}
</style>
