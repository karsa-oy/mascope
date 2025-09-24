<script setup>
import { reactive, ref, computed, watch, nextTick } from 'vue'

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

const ionizationToken = ref(null)

const availableIonizationModes = computed(
  () =>
    app.data.ionization.mode.list
      .map((i) => ({ name: i.ionization_mode_name, token: i.ionization_mode_token }))
      .filter((mode) => mode.token) || []
)
// validate file sizes before upload
const processed = computed(() => {
  const invalid = {
    tof: [],
    orbi: [],
    ionization: []
  }
  const valid = []
  props.files.forEach((file) => {
    // parse filename
    const prefix = file.name.split('_')[0]
    const prefixType = instrumentType(prefix)
    const ext = file.name.split('.').slice(-1)[0].toLowerCase()
    // check filename validity
    let validInstrumentName = true
    if (ext == 'h5' && prefixType !== 'tof') {
      invalid.tof.push(file)
      validInstrumentName = false
    } else if (ext == 'raw' && prefixType !== 'orbi') {
      invalid.orbi.push(file)
      validInstrumentName = false
    }
    let validIonization = true
    if (!availableIonizationModes.value.some((mode) => file.name.includes(mode.token))) {
      invalid.ionization.push(file)
      validIonization = false
    }
    if (validInstrumentName && validIonization) {
      valid.push(file)
    }
  })
  return { invalid, valid }
})

const count = computed(() => ({
  invalid:
    processed.value.invalid.tof.length +
    processed.value.invalid.orbi.length +
    processed.value.invalid.ionization.length,
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
  const invalidIonization = processed.value.invalid.ionization.length > 0 && !ionizationToken.value
  const noFiles =
    processed.value.invalid.tof.length +
      processed.value.invalid.orbi.length +
      processed.value.invalid.ionization.length +
      processed.value.valid.length ==
    0
  return invalidOrbi || invalidTof || invalidInstrumentName || invalidIonization || noFiles
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
  const allProcessedFiles = new Map() // Use Map to avoid duplicates

  // Process TOF files with instrument name issues
  processed.value.invalid.tof.forEach((file) => {
    let newName = `${instrument.tof}_${file.name}`

    // Check if this file also needs ionization token
    const needsIonization = processed.value.invalid.ionization.some(
      (ionFile) => ionFile.name === file.name
    )
    if (needsIonization && ionizationToken.value) {
      // Insert ionization token after instrument name
      const parts = newName.split('.')
      const nameWithoutExt = parts.slice(0, -1).join('.')
      const ext = parts.slice(-1)[0]
      newName = `${nameWithoutExt}_${ionizationToken.value}.${ext}`
    }

    allProcessedFiles.set(file.name, {
      ...file,
      name: newName
    })
  })

  // Process Orbi files with instrument name issues
  processed.value.invalid.orbi.forEach((file) => {
    let newName = `${instrument.orbi}_${file.name}`

    // Check if this file also needs ionization token
    const needsIonization = processed.value.invalid.ionization.some(
      (ionFile) => ionFile.name === file.name
    )
    if (needsIonization && ionizationToken.value) {
      // Insert ionization token after instrument name
      const parts = newName.split('.')
      const nameWithoutExt = parts.slice(0, -1).join('.')
      const ext = parts.slice(-1)[0]
      newName = `${nameWithoutExt}_${ionizationToken.value}.${ext}`
    }

    allProcessedFiles.set(file.name, {
      ...file,
      name: newName
    })
  })

  // Process files that only have ionization issues (not already processed above)
  processed.value.invalid.ionization.forEach((file) => {
    // Skip if already processed as TOF or Orbi file
    if (!allProcessedFiles.has(file.name) && ionizationToken.value) {
      const parts = file.name.split('.')
      const nameWithoutExt = parts.slice(0, -1).join('.')
      const ext = parts.slice(-1)[0]
      const newName = `${nameWithoutExt}_${ionizationToken.value}.${ext}`

      allProcessedFiles.set(file.name, {
        ...file,
        name: newName
      })
    }
  })

  const renamedFiles = Array.from(allProcessedFiles.values())

  active.value = false
  app.uppy.clearInvalid()
  emit('upload', renamedFiles)
}

const cancel = () => {
  active.value = false
  app.uppy.clearInvalid()
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
    <!-- MISSING IONIZATION -->
    <template v-if="processed.invalid.ionization.length > 0">
      <h3>Files missing ionization mode</h3>
      <p>The following raw files do not have a valid ionization mode token:</p>
      <ul>
        <li v-for="file in processed.invalid.ionization" :key="file.name">
          {{ file.name }}
        </li>
      </ul>
      <p>
        <i>
          Each filename must include a valid ionization mode token in order to be processed
          correctly. Currently available tokens are:
          {{ availableIonizationModes.map((i) => i.token).join(', ') }}.
        </i>
      </p>
      <p>
        Please select one of the existing ionization modes below to apply to these files, if
        applicable. Otherwise, create a new ionization mode with an appropriate token and upload
        again.
      </p>
      <div class="center" style="width: 100%">
        <FloatLabel>
          <Select
            inputId="file-ionization"
            v-model="ionizationToken"
            :options="availableIonizationModes"
            optionLabel="name"
            optionValue="token"
            style="min-width: 200px"
          />
          <label for="file-ionization"> Ionization mode </label>
        </FloatLabel>
      </div>
    </template>
    <!-- CONFIRM -->
    <menu style="justify-content: flex-end">
      <Button label="Cancel" icon="pi pi-times" severity="secondary" @click="cancel" />
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
