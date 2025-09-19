<script setup>
import { ref, reactive, computed, watch } from 'vue'

import FloatLabel from 'primevue/floatlabel'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Panel from 'primevue/panel'
import InputText from 'primevue/inputtext'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import TextArea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'

import { api } from '@/api'

import { equals } from '@/lib/table'
import { DEFAULT_SAMPLE_BATCH_TYPE, ANALYSIS_POLARITY } from '@/lib/constants'
import { clone, instrumentType as getInstrumentType } from '@/lib/utils'
import { useMzFit } from '@/lib/mzFit'

import { useApp } from '@/stores'

import PaneSelectTargets from './PaneSelectTargets.vue'
import PaneSelectMechanisms from './PaneSelectMechanisms.vue'

const app = useApp()
const confirm = useConfirm()

const props = defineProps({
  batch: {
    type: Object
  }
})

const original = computed(() => props.batch ?? app.data.batch.focused)

// api
const action = defineModel('action') // create, update, update_targets
const ready = ref(false)

// dialog visibility reactivity
const visible = ref(false)
watch([action, ready], () => {
  visible.value = !!action.value && ready.value
})
watch(visible, (value) => {
  if (!value) {
    action.value = null
  }
})

// reactive
const tab = ref('info')
const initial = reactive({
  info: {
    name: '',
    desc: '',
    type: '',
    polarity: ''
  },
  mechanisms: {
    matching: [],
    calibration: []
  },
  calibrants: []
})
const selected = reactive({
  info: {
    name: '',
    desc: '',
    type: '',
    polarity: ''
  },
  mechanisms: {
    matching: [], // matching mechanisms
    calibration: [] // calibration mechanisms
  },
  calibrants: null, // single calibration collection
  targets: [] // multiple target collections
})

// computed
const title = computed(
  () =>
    ({
      create: `Create a new sample batch`,
      update: `Edit sample batch "${selected.info.name}"`,
      update_targets: `Edit collections of sample batch "${selected.info.name}"`
    })[action.value]
)
const updated = computed(() => {
  const common = {
    sample_batch_name: selected.info.name,
    sample_batch_description: selected.info.desc,
    sample_batch_polarity: selected.info.polarity,
    workspace_id: app.data.workspace.focusedId,
    build_params: {
      calibration_collection: selected.calibrants?.target_collection_id,
      ion_mechanisms: selected.mechanisms.matching.map((mech) => mech.ionization_mechanism_id),
      calibration_ion_mechanisms: selected.mechanisms.calibration.map(
        (mech) => mech.ionization_mechanism_id
      )
    },
    target_collection_ids: selected.targets.map((row) => row.target_collection_id)
  }
  switch (action.value) {
    case 'create': {
      return common
    }
    case 'update':
    case 'update_targets': {
      return {
        ...common,
        sample_batch_id: original.value.sample_batch_id,
        sample_batch_utc_created: original.value.sample_batch_utc_created
      }
    }
    default:
      return null
  }
})
const changed = computed(() =>
  ready.value
    ? selected.info.name !== initial.info.name ||
      selected.info.desc !== initial.info.desc ||
      !equals(selected.targets, initial.targets, 'target_collection_id') ||
      !equals(selected.calibrants, initial.calibrants, 'target_collection_id') ||
      !equals(
        selected.mechanisms.matching,
        initial.mechanisms.matching,
        'ionization_mechanism_id'
      ) ||
      !equals(
        selected.mechanisms.calibration,
        initial.mechanisms.calibration,
        'ionization_mechanism_id'
      )
    : false
)
const invalid = computed(() => {
  switch (action.value) {
    case 'create': {
      return !selected.info.name || !(selected.mechanisms.matching?.length > 0)
    }
    case 'update': {
      const infoValid = selected.info.name.length > 0
      return !changed.value || !infoValid
    }
    case 'update_targets': {
      return equals(initial.targets, selected.targets, 'target_collection_id')
    }
    default:
      return false
  }
})

const showCalibrantsTab = computed(() => {
  if (action.value === 'update_targets') return false

  // For ANALYSIS batches, always show calibrants tab
  if (selected.info.type === 'ANALYSIS') return true

  // For ACQUISITION batches, only show for TOF instruments
  if (selected.info.type === 'ACQUISITION') {
    const instrument = app.data.workspace.focused?.instrument
    return getInstrumentType(instrument) === 'tof'
  }

  return true // Default fallback
})

const calibrationChanged = computed(
  () =>
    ready.value &&
    (!equals(selected.calibrants, initial.calibrants, 'target_collection_id') ||
      !equals(
        selected.mechanisms.calibration,
        initial.mechanisms.calibration,
        'ionization_mechanism_id'
      ))
)

// initialization
watch(action, init)
async function init(value) {
  if (!value) return
  ready.value = true
  const modification = ['update', 'update_targets'].includes(action.value)
  if (modification) {
    // init information
    selected.info.name = original.value.sample_batch_name
    selected.info.desc = original.value.sample_batch_description
    selected.info.type = original.value.sample_batch_type
    selected.info.polarity = original.value.polarity
    // init ionization mechanisms
    selected.mechanisms.matching = app.data.mechanism.list.filter((mech) =>
      original.value.build_params?.ion_mechanisms?.includes(mech.ionization_mechanism_id)
    )
    selected.mechanisms.calibration = app.data.mechanism.list.filter((mech) =>
      original.value.build_params?.calibration_ion_mechanisms?.includes(
        mech.ionization_mechanism_id
      )
    )
    // init target collections with batch collections
    const batchCollections = (
      await api.http.get(`/sample/batches/${original.value.sample_batch_id}/targets`, {
        use: 'read',
        type: 'read_batch_collections'
      })
    )?.target_collections
    selected.targets = app.data.target.collection.list.filter((coll) =>
      batchCollections
        .map(({ target_collection_id }) => target_collection_id)
        .includes(coll.target_collection_id)
    )
    // init calibrants with batch param
    selected.calibrants = app.data.target.collection.list.find(
      ({ target_collection_id }) =>
        target_collection_id == original.value.build_params?.calibration_collection
    )
  } else {
    // init information
    selected.info.name = ''
    selected.info.desc = ''
    selected.info.type = DEFAULT_SAMPLE_BATCH_TYPE // Set default type
    selected.info.polarity = ANALYSIS_POLARITY // Default polarity for ANALYSIS batches
    // init ionization mechanisms
    selected.mechanisms.matching = []
    // init target collections with defaults
    selected.targets = []
    // init calibrants as null (optional)
    selected.calibrants = null
  }
  // save initial state
  initial.info = clone(selected.info)
  initial.mechanisms.matching = clone(selected.mechanisms.matching)
  initial.mechanisms.calibration = clone(selected.mechanisms.calibration)
  initial.targets = clone(selected.targets)
  initial.calibrants = clone(selected.calibrants)
  // set initial tab
  tab.value = value == 'update_targets' ? 'targets' : 'info'
}

// confirmation
async function execute() {
  action.value = null
  switch (action.value) {
    case 'create': {
      app.data.batch.create(updated.value)
      break
    }
    case 'update':
    case 'update_targets': {
      await app.data.batch.update(updated.value)
      if (calibrationChanged.value) {
        const mzFit = useMzFit({ unmount: true })
        await api.http.post(
          `/calibration/mz_calibrate/batch/${original.value.sample_batch_id}`,
          mzFit.mzCalibrationParams,
          {
            use: 'process',
            type: 'recalibrate_batch'
          }
        )
      }
      break
    }
  }
}
async function save() {
  if (calibrationChanged.value && ['update', 'update_targets'].includes(action.value)) {
    confirm.require({
      icon: 'pi pi-exclamation-triangle',
      header: 'Confirm calibration',
      message: `Updating calibration settings will remove matches for all associated samples in this and other batches. This action cannot be undone. Are you sure you want to proceed?`,
      accept: execute,
      acceptProps: {
        label: 'Continue'
      },
      rejectProps: {
        label: 'Cancel',
        severity: 'secondary'
      }
    })
  } else {
    await execute()
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="title"
    style="min-width: 800px; min-height: 600px"
    contentStyle="flex-grow: 1; display: flex; flex-flow: column; gap: 0.5rem; justify-content: space-between"
  >
    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="info">Info</Tab>
        <Tab value="targets" :disabled="action == 'update'">Targets</Tab>
        <Tab value="mechanisms" :disabled="action == 'update_targets'">Mechanisms</Tab>
        <Tab value="calibrants" :disabled="!showCalibrantsTab">Calibrants</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="info">
          <Panel style="text-align: center">
            <FloatLabel>
              <InputText
                id="batch-name"
                v-model="selected.info.name"
                :disabled="action == 'update_targets'"
                style="width: 65ch"
              />
              <label for="batch-name">Name</label>
            </FloatLabel>
            <FloatLabel>
              <TextArea
                id="batch-desc"
                v-model="selected.info.desc"
                :disabled="action == 'update_targets'"
                autoResize
                style="width: 65ch"
              />
              <label for="batch-desc">Description</label>
            </FloatLabel>
          </Panel>
        </TabPanel>

        <TabPanel value="targets">
          <PaneSelectTargets
            mode="targets"
            :batch="selected.info"
            v-model:selected="selected.targets"
          />
        </TabPanel>

        <TabPanel value="mechanisms">
          <PaneSelectMechanisms
            :batch="selected.info"
            v-model:matchingMechanisms="selected.mechanisms.matching"
            v-model:calibrationMechanisms="selected.mechanisms.calibration"
          />
        </TabPanel>

        <TabPanel value="calibrants">
          <PaneSelectTargets
            mode="calibrants"
            :batch="selected.info"
            v-model:selected="selected.calibrants"
          />
        </TabPanel>
      </TabPanels>
    </Tabs>

    <menu>
      <Button label="Cancel" @click="action = null" icon="pi pi-times" severity="secondary" />
      <Button label="Save" @click="save" icon="pi pi-save" :disabled="invalid" />
    </menu>
  </Dialog>
</template>
