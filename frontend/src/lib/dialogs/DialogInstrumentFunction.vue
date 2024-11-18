<script setup>
import { ref, computed } from 'vue'

import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Message from 'primevue/message'

import { PaneInstrumentFunctions } from '@/lib/panes'
import { useApp } from '@/stores'
import { api } from '@/api'

const app = useApp()

const props = defineProps({
  sample: {
    type: Object
  }
})

const visible = defineModel('visible')

const instrumentFunctions = ref()

const execute = async () => {
  const { payload } = instrumentFunctions.value
  visible.value = false
  if (payload) {
    await api.http.post(`/instrument_functions/process`, payload, {
      use: 'process',
      type: 'adjust_instrument_functions'
    })
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="`Refit instrument functions for ${sample?.filename}`"
    modal
    style="width: 900px"
  >
    <section>
      <PaneInstrumentFunctions
        v-if="visible && sample"
        :filename="sample?.filename"
        :autofit="true"
        v-model:data="instrumentFunctions"
        invalidateUnchanged
      />
    </section>
    <menu style="margin-top: 2rem; justify-content: space-between">
      <Message
        v-if="instrumentFunctions?.message"
        :severity="instrumentFunctions?.message?.severity"
        :icon="instrumentFunctions?.message?.icon"
      >
        {{ instrumentFunctions?.message?.contents }}
      </Message>
      <div class="row" style="justify-content: flex-end; flex-grow: 1">
        <Button label="Cancel" @click="visible = false" severity="secondary" />
        <Button
          label="Save"
          @click="execute"
          :disabled="instrumentFunctions?.fitting || instrumentFunctions?.invalid"
        />
      </div>
    </menu>
  </Dialog>
</template>
