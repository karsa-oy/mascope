<script setup>
import { reactive, watchEffect, watch, computed, ref, onMounted } from 'vue'

import Chart from 'primevue/chart'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import Button from 'primevue/button'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'

import { api } from '@/api'
import { useApp } from '@/stores'
import { BaseParamField } from '@/lib/base'
import { glasbey } from '@/lib/charts/colors.js'

const ADD_METHOD_FILE = 'Create new'

const app = useApp()

const props = defineProps({
  filename: {
    type: String,
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

const data = defineModel('data')

// sample file

const sampleFile = ref()

api.http
  .get(`/sample/files`, {
    params: {
      filename: props.filename
    },
    use: 'read',
    type: 'get_sample_file'
  })
  .then(([sample_file]) => {
    sampleFile.value = sample_file
    loadMethodFiles(sample_file)
  })

const instrumentType = computed(() =>
  sampleFile.value
    ? app.data.instrument.list.find(({ instrument }) => instrument == sampleFile.value.instrument)
        .type
    : null
)

// threshold

const threshold = ref()

api.http
  .get('/params', {
    type: 'read_params'
  })
  .then(({ data }) => {
    threshold.value = data?.data?.params.instrument_functions.threshold
  })

// method files

const methodFile = reactive({
  options: [],
  selected: ADD_METHOD_FILE,
  new: null
})
const instrumentFunction = reactive({
  options: [ADD_METHOD_FILE],
  selected: null,
  new: null
})

const creating = computed(() => methodFile.selected == ADD_METHOD_FILE)

// internal sync

watchEffect(() => {
  instrumentFunction.selected = instrumentFunction.options.find(
    ({ method_file }) => method_file == methodFile.selected
  )
})

// inwards sync

watch(
  () => data?.methodFile?.selected,
  (externalSelected) => {
    if (methodFile.selected !== externalSelected) {
      methodFile.selected = externalSelected
    }
  }
)

// load

function loadMethodFiles(sample_file) {
  api.http
    .get(`/instrument_functions/method_files`, {
      params: {
        filename: props.filename
      },
      use: 'read',
      type: 'load_method_files'
    })
    .then((instrument_functions) => {
      // populate options
      instrumentFunction.options = instrument_functions
      methodFile.options = [
        ADD_METHOD_FILE,
        ...instrument_functions.map(({ method_file }) => method_file)
      ]
      // autoselect method file option
      const latestMethod = instrument_functions.sort((a, b) =>
        a.datetime_utc < b.datetime_utc ? -1 : a.datetime_utc > b.datetime_utc ? 1 : 0
      )[0].method_file
      const currentMethod = methodFile.options.includes(sample_file.method_file)
        ? sample_file.method_file
        : null
      methodFile.selected = currentMethod ?? latestMethod ?? ADD_METHOD_FILE
    })
}

// fit

const fitting = ref(null)
const updateFit = ref()

const previous = ref()

const shouldRefit = computed(
  () =>
    props.autofit && // autofit enabled from parent context
    !fitting.value && // no current fit is ongoing
    threshold.value !== undefined && // threshold value exists
    previous.value !== threshold.value // threshold value has changed
)

watch([threshold, () => props.autofit], async () => {
  if (shouldRefit.value) {
    const prev = threshold.value
    fitting.value = true
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
    previous.value = prev
  }
})

// Fit must be updated for new method files. For existing
// method files we default to using the current fit:
watchEffect(() => {
  updateFit.value = methodFile.selected == ADD_METHOD_FILE
})

app.ui.notification
  .on('instrument_functions_fit', ({ data }) => {
    instrumentFunction.new = data
    fitting.value = false
  })
  .unmount()

// resolution function fits

const rTof = (a, b) => (mz) => mz / (a * mz + b)

const rOrbi = (a) => (mz) => a / Math.sqrt(mz)

const createFitDetails = (params) => {
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
}

const currentFitDetails = computed(() => {
  const params = instrumentFunction.selected?.resolution_function
  return createFitDetails(params)
})

const newFitDetails = computed(() => {
  const params = instrumentFunction.new?.instrument_functions?.resolution_function
  return createFitDetails(params)
})

// colors

const theme = computed(() => (app.ui.darkmode.active ? glasbey.dark : glasbey.light))
const newFitColor = computed(() => theme.value[3])

// resolution function chart

const resolution = computed(() => {
  const { fwhm, mz } = instrumentFunction.new?.statistics.resolution_function
  mz.sort((a, b) => a - b)

  return {
    labels: mz,
    datasets: [
      {
        type: 'scatter',
        label: 'Data points',
        data: fwhm.map((fwhm, i) => {
          const x = mz[i]
          return {
            x,
            y: x / fwhm
          }
        }),
        backgroundColor: newFitColor.value
      },
      ...(newFitDetails.value?.fit
        ? [
            {
              type: 'line',
              label: 'New fit',
              data: mz.map(newFitDetails.value.fit),
              borderColor: newFitColor.value,
              pointStyle: false
            }
          ]
        : []),
      ...(currentFitDetails.value?.fit
        ? [
            {
              type: 'line',
              label: 'Current fit',
              data: mz.map(currentFitDetails.value.fit),
              borderColor: 'grey',
              pointStyle: false
            }
          ]
        : [])
    ]
  }
})

// peakshape chart

const peakshape = computed(() => {
  let currentPeakshape = null
  const labels = instrumentFunction.new?.instrument_functions.peakshape.x.map((n) =>
    n.toPrecision(3)
  )
  if (instrumentFunction.selected) {
    const points = instrumentFunction.selected.peakshape.x
      .map((x, i) => ({ x, i }))
      .map(({ x, i }) => ({ x: x.toPrecision(3), y: instrumentFunction.selected.peakshape.y[i] }))
      .filter(({ x }) => labels.includes(x))
    currentPeakshape = {
      label: 'Current peakshape',
      data: points.map(({ y }) => y),
      fill: false,
      pointStyle: false,
      tension: 0.4,
      borderColor: 'grey'
    }
  }
  const newPeakshape = {
    label: 'New peakshape',
    data: instrumentFunction.new?.instrument_functions.peakshape.y,
    fill: false,
    pointStyle: false,
    tension: 0.4,
    borderColor: newFitColor.value
  }
  return {
    labels,
    datasets: [newPeakshape, currentPeakshape].filter((d) => d)
  }
})

// input and validation

const methodFileNameExists = computed(() => methodFile.options.includes(methodFile.new))
const methodFileNameMissing = computed(() => !(methodFile.new?.trim()?.length > 0))
const methodFileUnchanged = computed(() => sampleFile.value?.method_file == methodFile.selected)

const invalidMethodFileCreate = computed(
  () => creating.value && (methodFileNameExists.value || methodFileNameMissing.value)
)
const invalidMethodFileUpdate = computed(
  () =>
    props.invalidateUnchanged && // changing is required
    !creating.value && // updating existing method file
    methodFileUnchanged.value && // method file has not been changed
    !updateFit.value // fit has not been updated
)

const message = computed(() => {
  const missing = methodFileNameMissing.value
    ? 'A name must be provided when creating a new method file'
    : null
  const existing = methodFileNameExists.value
    ? 'Method file name already exists; choose it from the dropdown or change the name.'
    : null
  const contents = missing ?? existing
  return instrumentFunction.new && creating.value && contents
    ? {
        severity: 'warn',
        icon: 'pi pi-exclamation-triangle',
        contents
      }
    : null
})

// sync model

watchEffect(() => {
  data.value = {
    fitting: fitting.value,
    invalid: invalidMethodFileCreate.value || invalidMethodFileUpdate.value,
    message: message.value,
    creating: creating.value,
    methodFile: {
      current: sampleFile.value?.method_file,
      new: creating.value ? methodFile.new : null,
      selected: methodFile.selected,
      options: methodFile.options
    },
    payload: creating.value
      ? {
          filename: props.filename,
          new_method_file: methodFile.new,
          new_instrument_function: instrumentFunction.new?.instrument_functions
        }
      : {
          filename: props.filename,
          existing_method_file: methodFile.selected,
          new_instrument_function: updateFit.value
            ? instrumentFunction.new?.instrument_functions
            : null
        }
  }
})
</script>

<template>
  <!-- inputs -->
  <menu class="topbar" v-if="threshold !== undefined && instrumentFunction.new">
    <div class="row">
      <FloatLabel>
        <Select
          v-model="methodFile.selected"
          :options="methodFile.options"
          id="method-file-option"
        />
        <label for="method-file-option">Method file</label>
      </FloatLabel>
      <FloatLabel v-if="methodFile.selected == ADD_METHOD_FILE">
        <InputText id="method-file-name" v-model="methodFile.new" required />
        <label for="method-file-name"> Method file name </label>
      </FloatLabel>
      <div class="row" v-else>
        <ToggleSwitch v-model="updateFit" :disabled="methodFile.selected == ADD_METHOD_FILE" />
        <span>Update instrument functions</span>
      </div>
    </div>
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
  </menu>
  <div style="position: relative" :class="fitting ? 'faded' : ''">
    <!-- charts -->
    <div style="" class="spinner-overlay" v-if="fitting">
      <ProgressSpinner />
    </div>
    <div
      class="col"
      style="align-items: center; justify-content: space-around; gap: 0.5rem"
      v-if="instrumentFunction.new"
    >
      <div class="row" style="gap: 0.5rem">
        <Chart
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
            }
          }"
        />
        <Chart
          type="line"
          class="chart"
          :data="peakshape"
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
            }
          }"
        />
      </div>
      <!-- stats bar -->
      <div class="row" style="justify-content: space-around; width: 100%">
        <div class="stat">
          <span>{{ newFitDetails.equation }} </span>
          <span>Formula</span>
        </div>
        <div class="stat" v-if="newFitDetails?.a">
          <span>{{ newFitDetails?.a?.toExponential(2) }} </span>
          <span>a</span>
        </div>
        <div class="stat" v-if="newFitDetails?.b">
          <span>{{ newFitDetails?.b?.toExponential(2) }} </span>
          <span>b</span>
        </div>
        <div class="stat">
          <span>
            {{ instrumentFunction.new?.instrument_functions.instrument }}
          </span>
          <span> Instrument </span>
        </div>
        <div class="stat">
          <span>
            {{ instrumentFunction.new?.instrument_functions.datetime_utc.replace('T', ' ') }}
          </span>
          <span> Datetime UTC </span>
        </div>
        <div class="stat">
          <span style="font-size: 2rem">
            {{ instrumentFunction.new?.statistics.peakshape.num_of_peaks }}
          </span>
          <span> Peaks </span>
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

.faded {
  opacity: 0.3;
}
</style>
