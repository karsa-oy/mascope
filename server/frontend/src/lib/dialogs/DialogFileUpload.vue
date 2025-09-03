<script setup>
import { reactive, computed, watch, nextTick } from 'vue'

import Button from 'primevue/button'
import Select from 'primevue/select'
import FloatLabel from 'primevue/floatlabel'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'

import { instrumentType } from '@/lib/utils'

import { useApp } from '@/stores'

const app = useApp()

const props = defineProps({
  files: {
    type: Array,
    default: []
  }
})
const active = defineModel('active')

const emit = defineEmits(['upload'])

const instrument = reactive({
  tof: null,
  orbi: null
})

// validate file sizes before upload
const processed = computed(() => {
  const invalid = {
    tof: [],
    orbi: []
  }
  const valid = []
  props.files.forEach((file) => {
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
  invalid: processed.value.invalid.tof.length + processed.value.invalid.orbi.length,
  valid: processed.value.valid.length,
  total: props.files.length
}))

const validInstrumentName = (name) => {
  const re = new RegExp('^[a-zA-Z]+[0-9]*$')
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
watch(
  () => props.files,
  (files) => {
    if (!files?.length) return
    nextTick(() => {
      if (count.value.total > 0) {
        // Some files need manual handling - show dialog
        active.value = true
      }
    })
  },
  { immediate: true }
)

// Manual upload for renamed files
const upload = () => {
  const renamedTofFiles = processed.value.invalid.tof.map((file) => {
    return {
      ...file,
      name: `${instrument.tof}_${file.name}`
    }
  })
  const renamedOrbiFiles = processed.value.invalid.orbi.map((file) => {
    return {
      ...file,
      name: `${instrument.orbi}_${file.name}`
    }
  })
  active.value = false
  app.uppy.clearInvalid()
  emit('upload', [...renamedTofFiles, ...renamedOrbiFiles])
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
          Valid TOF instrument names must include the word TOF or API (in lower or upper case),
          separated from the rest of the filename by an underscore.
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
      <p>The following raw files do not have a valid Orbitrap instrument name as a prefix:</p>
      <ul>
        <li v-for="file in processed.invalid.orbi" :key="file.name">
          {{ file.name }}
        </li>
      </ul>
      <p>
        <i>
          Valid Orbitrap instrument names must include the word ORBI (in lower or upper case),
          separated from the rest of the filename by an underscore.
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
