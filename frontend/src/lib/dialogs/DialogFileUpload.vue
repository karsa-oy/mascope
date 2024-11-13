<script setup>
import { ref, reactive, computed, watch, watchEffect } from 'vue'

import Button from 'primevue/button'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import FileUpload from 'primevue/fileupload'
import FloatLabel from 'primevue/floatlabel'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'

import { runtime } from '@/lib/runtime'
import { instrumentType } from '@/lib/utils'

import { useApp } from '@/stores'

// TODO_configuration Default sample file upload params
const FILE_UPLOAD_SIZE_LIMIT = 200 * 1024 * 1024 // 200 MB

const app = useApp()

const props = defineProps({
  files: {
    type: Array,
    default: []
  }
})
const active = defineModel('active')

const instrument = reactive({
  tof: null,
  orbi: null
})

// validate file sizes before upload
const processed = computed(() => {
  const invalid = {
    tof: [],
    orbi: [],
    oversized: []
  }
  const valid = []
  props.files.forEach((file) => {
    // validate file size
    if (file.size > FILE_UPLOAD_SIZE_LIMIT) {
      invalid.oversized.push(file)
    }
    // parse filename
    const prefix = file.name.split('_')[0]
    const prefixType = instrumentType(prefix)
    const ext = file.name.split('.').slice(-1)[0].toLowerCase()
    // check filename validity
    if (ext == 'h5' && prefixType !== 'tof') {
      invalid.tof.push(file)
    } else if (ext == 'raw' && prefixType !== 'orbi') {
      invalid.orbi.push(file)
    } else {
      valid.push(file)
    }
  })
  return { invalid, valid }
})

const count = computed(() => ({
  invalid:
    processed.value.invalid.tof.length +
    processed.value.invalid.orbi.length +
    processed.value.invalid.oversized.length,
  valid: processed.value.valid.length,
  total: props.files.length
}))

const validInstrumentName = (name) => {
  const re = new RegExp('^[a-zA-Z]+\w*$')
  return re.test(name)
}

const invalid = computed(() => {
  const invalidOrbi =
    processed.value.invalid.orbi.length > 0 && instrumentType(instrument.orbi) !== 'orbi'
  const invalidTof =
    processed.value.invalid.tof.length > 0 && instrumentType(instrument.tof) !== 'tof'
  const invalidInstrumentName =
    !validInstrumentName(instrument.tof) || !validInstrumentName(instrument.orbi)
  const noFiles =
    processed.value.invalid.tof.length +
      processed.value.invalid.orbi.length +
      processed.value.valid.length ==
    0
  return invalidOrbi || invalidTof || invalidInstrumentName || noFiles
})

// handle file selection
watchEffect(() => {
  // validate file sizes
  if (count.value.valid > 0 && count.value.total == count.value.valid) {
    // autoupload if all files are valid
    app.data.sample.upload(props.files)
  } else {
    if (count.value.total > 0) {
      // launch the dialog otherwise
      active.value = true
    }
  }
})

const upload = () => {
  const renamedTofFiles = processed.value.invalid.tof.map(
    (file) => new File([file], `${instrument.tof}_${file.name}`, { type: file.type })
  )
  const renamedOrbiFiles = processed.value.invalid.orbi.map(
    (file) => new File([file], `${instrument.orbi}_${file.name}`, { type: file.type })
  )
  active.value = false
  app.data.sample.upload([...renamedTofFiles, ...renamedOrbiFiles, ...processed.value.valid])
}
</script>

<template>
  <Dialog :visible="active" modal header="Resolve issues with uploaded files">
    <!-- TOF FILES -->
    <template v-if="processed.invalid.tof.length > 0">
      <h3>Invalid TOF Files</h3>
      <p>The following h5 files do not have a valid TOF instrument name as a prefix:</p>
      <ul>
        <li v-for="file in processed.invalid.tof" :key="file.name">
          {{ file.name }}
        </li>
      </ul>
      <p>
        <i>
          Valid TOF instrument names must include the word TOF or API (in lower or upper case) and
          consist only of letters, numbers and underscores _.
        </i>
      </p>
      <p>Please select or enter an instrument to assign these files to:</p>
      <div class="center" style="width: 100%">
        <FloatLabel>
          <Select
            inputId="file-instrument"
            v-model="instrument.tof"
            :options="
              app.data.instrument.list.filter(
                ({ instrument }) => instrumentType(instrument) == 'tof'
              )
            "
            dataKey="instrument"
            optionLabel="instrument"
            optionValue="instrument"
            editable
            style="min-width: 200px"
          />
          <label for="file-instrument"> Instrument </label>
        </FloatLabel>
        <Message
          severity="warn"
          icon="pi pi-exclamation-triangle"
          v-if="
            instrument.tof &&
            (instrumentType(instrument.tof) !== 'tof' || !validInstrumentName(instrument.tof))
          "
          style="margin-bottom: 2rem"
        >
          <i>
            You entered an invalid TOF instrument name; please enter a valid instrument name, as
            explained above.
          </i>
        </Message>
      </div>
    </template>
    <!-- ORBI FILES -->
    <template v-if="processed.invalid.orbi.length > 0">
      <h3>Invalid OrbiTrap Files</h3>
      <p>The following h5 files do not have a valid OrbiTrap instrument name as a prefix:</p>
      <ul>
        <li v-for="file in processed.invalid.orbi" :key="file.name">
          {{ file.name }}
        </li>
      </ul>
      <p>
        <i>
          Valid OrbiTrap instrument names must include the word ORBI (in lower or upper case) and
          consist only of letters, numbers and underscores _.
        </i>
      </p>
      <p>Please select or enter an instrument to assign these files to:</p>
      <div class="center" style="width: 100%">
        <FloatLabel>
          <Select
            inputId="file-instrument"
            v-model="instrument.orbi"
            :options="
              app.data.instrument.list.filter(
                ({ instrument }) => instrumentType(instrument) == 'orbi'
              )
            "
            dataKey="instrument"
            optionLabel="instrument"
            optionValue="instrument"
            editable
            style="min-width: 200px"
          />
          <label for="file-instrument"> Instrument </label>
        </FloatLabel>
        <Message
          severity="warn"
          icon="pi pi-exclamation-triangle"
          v-if="
            instrument.orbi &&
            (instrumentType(instrument.orbi) !== 'orbi' || !validInstrumentName(instrument.orbi))
          "
          style="margin-bottom: 2rem"
        >
          <i>
            You entered an invalid OrbiTrap instrument name; please enter a valid instrument name,
            as explained above.
          </i>
        </Message>
      </div>
    </template>
    <!-- OVERSIZED FILES -->
    <template v-if="processed.invalid.oversized.length > 0">
      <h3>Files exceeding the size limit</h3>
      <p>
        The following files exceeded the
        {{ FILE_UPLOAD_SIZE_LIMIT / (1024 * 1024) }} MB size limit:
      </p>
      <ul>
        <li v-for="file in processed.invalid.oversized" :key="file.name">
          {{ file.name }}
        </li>
      </ul>
      <p>Please try to reduce their file size or upload smaller files.</p>
    </template>
    <!-- CONFIRM -->
    <menu style="justify-content: flex-end">
      <Button label="Cancel" icon="pi pi-times" severity="secondary" @click="active = false" />
      <Button label="Save" icon="pi pi-save" :disabled="invalid" @click="upload" />
    </menu>
  </Dialog>
</template>

<style scoped>
menu {
  display: flex;
  flex-flow: row nowrap;
  gap: 0.5rem;
  justify-content: space-between;
  align-items: center;
  padding: 0;
  margin: 0;
}

menu > :deep(*) {
  margin-bottom: 0;
}

menu :deep(*) {
  font-size: 12px;
}

p,
:deep(.p-message-text) {
  max-width: 450px;
}
</style>
