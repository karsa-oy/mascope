<script setup>
import Dialog from 'primevue/dialog'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

import { reactive, watchEffect } from 'vue'

import { api } from '@/api'

const props = defineProps({
  compound: {
    type: Object
  }
})

const visible = defineModel('visible')

const input = reactive({
  target_compound_id: props.compound?.target_compound_id,
  target_compound_formula: props.compound?.target_compound_formula,
  target_compound_name: props.compound?.target_compound_name,
  cas_number: props.compound?.cas_number
})

watchEffect(() => {
  input.target_compound_id = props.compound?.target_compound_id
  input.target_compound_formula = props.compound?.target_compound_formula
  input.target_compound_name = props.compound?.target_compound_name
  input.cas_number = props.compound?.cas_number
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="`Edit target compound '${compound?.target_compound_formula}'`"
  >
    <div class="col" style="gap: 0rem">
      <FloatLabel style="margin: 1rem 0; margin-top: 1.5rem">
        <InputText
          id="add-compound-formula"
          required
          v-model="input.target_compound_formula"
          disabled
        />
        <label for="add-compound-formula"> Formula </label>
      </FloatLabel>
      <FloatLabel style="margin: 1rem 0">
        <InputText id="add-compound-name" required v-model="input.target_compound_name" />
        <label for="add-compound-name"> Name </label>
      </FloatLabel>
      <FloatLabel style="margin: 1rem 0">
        <InputText id="add-compound-cas" required v-model="input.cas_number" />
        <label for="add-compound-cas"> CAS </label>
      </FloatLabel>
      <menu style="justify-content: flex-end; width: 100%">
        <Button
          label="Cancel"
          severity="secondary"
          icon="pi pi-times"
          @click="
            () => {
              visible = false
            }
          "
        />
        <Button
          label="Save"
          icon="pi pi-save"
          @click="
            () => {
              api.request.update({
                method: 'updateTargetCompounds',
                body: [input]
              })
              visible = false
            }
          "
        />
      </menu>
    </div>
  </Dialog>
</template>
