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

import { useApp } from '@/stores'

const app = useApp()

const visible = defineModel('visible')
const tab = ref('modes') // Default to modes tab
const layer = 'dialog_ionization' // Help-mode layer for dialog
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
    app.ui.help.set(layer)
  } else {
    app.ui.help.set(null)
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
        <Tab
          value="modes"
          :pt="
            app.ui.help.bottom_start(
              `
                <h1>Ionization Modes</h1>

                <p>
                  Define ionization modes, to configure the data processing pipeline to match
                  with the experimental setup.
                </p>
                <p>
                  Ionization mode consists of the applicable ionization mechanisms, mass calibration
                  compounds and default targets used for monitoring instrument performance.
                </p>
                <p>
                  To enable automatic processing of files upon upload, the filename must contain a token
                  matching with an ionization mode configured here.
                </p>
          `,
              { layer }
            )
          "
        >
          Ionization Modes
        </Tab>
        <Tab
          value="mechanisms"
          :pt="
            app.ui.help.bottom_start(
              `
                <h1>Ionization Mechanisms</h1>
                <p>
                  Define ionization mechanisms used in ionization modes.
                  The mechanism defines how neutral compounds are ionized to
                  form ions detected by the mass spectrometer.
                </p>
                <p>
                  A mechanism describes a single charge-forming reaction as an
                  operation, a modification formula, and the charge of the
                  transferred species: a leading <code>+</code> (add) or
                  <code>-</code> (remove), the formula added or removed
                  (e.g. <code>H</code> or <code>Br</code>), and a trailing
                  <code>+</code> or <code>-</code> giving that species' charge.
                  The <em>ion</em> polarity is not written directly &mdash; it
                  follows from the two signs: adding a positively charged species
                  or removing a negatively charged one yields a positive ion, and
                  vice versa.
                </p>
                <ul>
                  <li><code>+H+</code> &mdash; protonation, <code>[M+H]+</code> (positive)</li>
                  <li>
                    <code>-H+</code> &mdash; deprotonation, i.e. removal of a
                    proton (<code>H+</code>), giving <code>[M-H]-</code> (negative)
                  </li>
                  <li><code>+Br-</code> &mdash; bromide adduct, <code>[M+Br]-</code> (negative)</li>
                  <li>a bare <code>+</code> or <code>-</code> &mdash; electron transfer</li>
                </ul>
          `,
              { layer }
            )
          "
          >Ionization Mechanisms</Tab
        >
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
