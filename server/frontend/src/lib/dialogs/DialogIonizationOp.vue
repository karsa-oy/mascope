<script setup>
/**
 *  Dialog for managing ionization modes and mechanisms
 *
 *  Allows adding and removing modes and mechanisms in separate tabs.
 */
import { watch, ref } from 'vue'

import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'

import PaneIonizationMechanism from '@/lib/panes/PaneIonizationMechanism.vue'
import PaneIonizationMode from '@/lib/panes/PaneIonizationMode.vue'

const visible = defineModel('visible')
const tab = ref('modes') // Default to modes tab
const modesPaneRef = ref(null)
const mechanismsPaneRef = ref(null)

// reset when modal closed/opened
watch(visible, () => {
  if (modesPaneRef.value) {
    modesPaneRef.value.resetFields()
  }
  if (mechanismsPaneRef.value) {
    mechanismsPaneRef.value.resetFields()
  }
  // Reset to default tab when dialog opens
  if (visible.value) {
    tab.value = 'modes'
  }
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    header="Edit Ionization Settings"
    modal
    style="max-width: 80vw; min-height: 85vh"
    contentStyle="flex-grow: 1; display: flex; flex-flow: column; gap: 0.5rem; justify-content: space-between"
  >
    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="modes">Ionization Modes</Tab>
        <Tab value="mechanisms">Ionization Mechanisms</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="modes">
          <PaneIonizationMode ref="modesPaneRef" />
        </TabPanel>

        <TabPanel value="mechanisms">
          <PaneIonizationMechanism ref="mechanismsPaneRef" />
        </TabPanel>
      </TabPanels>
    </Tabs>

    <menu>
      <Button label="Close" @click="visible = false" />
    </menu>
  </Dialog>
</template>
