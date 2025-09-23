<script setup>
import { ref, watchEffect, computed } from 'vue'

import Panel from 'primevue/panel'
import ScrollPanel from 'primevue/scrollpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ToggleSwitch from 'primevue/toggleswitch'

import { DEFAULT_SAMPLE_BATCH_TYPE, ANALYSIS_POLARITY } from '@/lib/constants'
import { useApp } from '@/stores'

const app = useApp()

const props = defineProps({
  batch: {
    type: Object
  }
})

// external API
const matchingMechanisms = defineModel('matchingMechanisms')
const calibrationMechanisms = defineModel('calibrationMechanisms')

const filteredMechanisms = computed(() => {
  if (!props.batch?.polarity) {
    return app.data.ionization.mechanism.list
  }

  // If polarity is "+-", show all mechanisms
  if (props.batch.polarity === ANALYSIS_POLARITY) {
    return app.data.ionization.mechanism.list
  }

  // Otherwise filter by exact polarity match
  return app.data.ionization.mechanism.list.filter(
    (mech) => mech.ionization_mechanism_polarity === props.batch.polarity
  )
})

// internal selection
const calibrationSelection = ref(
  // modeled as { [ionization_mechanism_id]: boolean }
  Object.fromEntries(
    // initialized from the mechanism store
    filteredMechanisms.value.map(({ ionization_mechanism_id }) => [
      ionization_mechanism_id,
      // and the externally provided initial
      // calibration mechanism list
      calibrationMechanisms.value
        .map((init) => init.ionization_mechanism_id)
        .includes(ionization_mechanism_id)
    ])
  )
)
// update external calibration mode
watchEffect(() => {
  // the object needs to be transformed to a record array
  calibrationMechanisms.value = Object.entries(calibrationSelection.value)
    .filter(([, selected]) => selected)
    .map(([ionization_mechanism_id]) =>
      filteredMechanisms.value.find(
        (mech) => mech.ionization_mechanism_id == ionization_mechanism_id
      )
    )
})
// ensure selected calibration mechanisms
// are also added to the match mechanisms
watchEffect(() => {
  Object.entries(calibrationSelection.value)
    .filter(([, selected]) => selected)
    .forEach(([ionization_mechanism_id]) => {
      const matchMechanismIds = matchingMechanisms.value.map((m) => m.ionization_mechanism_id)
      if (!matchMechanismIds.includes(ionization_mechanism_id)) {
        matchingMechanisms.value.push(
          filteredMechanisms.value.find(
            (mech) => mech.ionization_mechanism_id == ionization_mechanism_id
          )
        )
      }
    })
})
</script>

<template>
  <Panel>
    <ScrollPanel style="width: 100%; height: 300px">
      <DataTable
        v-model:selection="matchingMechanisms"
        :value="filteredMechanisms"
        tableStyle="min-width: 70ch;"
        @rowUnselect="
          ({ data }) => {
            calibrationSelection[data['ionization_mechanism_id']] = false
          }
        "
      >
        <Column selectionMode="multiple" />
        <Column header="Mechanism" field="ionization_mechanism" sortable />
        <Column header="Polarity" field="ionization_mechanism_polarity" sortable />
        <Column header="Calibration">
          <template #body="{ data }">
            <ToggleSwitch v-model="calibrationSelection[data['ionization_mechanism_id']]" />
          </template>
        </Column>
      </DataTable>
    </ScrollPanel>
  </Panel>
</template>
