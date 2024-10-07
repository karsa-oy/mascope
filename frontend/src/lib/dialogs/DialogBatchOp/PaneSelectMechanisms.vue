<script setup>
import { ref, watchEffect } from 'vue'

import Panel from 'primevue/panel'
import ScrollPanel from 'primevue/scrollpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ToggleSwitch from 'primevue/toggleswitch'

import { useApp } from '@/stores'

const app = useApp()

// external API
const matchingMechanisms = defineModel('matchingMechanisms')
const calibrationMechanisms = defineModel('calibrationMechanisms')

// internal selection
const calibrationSelection = ref(
  // modeled as { [ionization_mechanism_id]: boolean }
  Object.fromEntries(
    // initialized from the mechanism store
    app.data.mechanism.list.map(({ ionization_mechanism_id }) => [
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
      app.data.mechanism.list.find(
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
          app.data.mechanism.list.find(
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
        :value="app.data.mechanism.list"
        tableStyle="min-width: 70ch;"
        @rowUnselect="
          ({ data }) => {
            calibrationSelection[data['ionization_mechanism_id']] = false
          }
        "
        :sortOrder="-1"
        :sortField="
          ({ ionization_mechanism_id }) =>
            matchingMechanisms
              .map(({ ionization_mechanism_id }) => ionization_mechanism_id)
              .includes(ionization_mechanism_id)
              ? +1
              : -1
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
