<script setup>
/**
 * Component for managing ionization mechanisms
 *
 * Allows adding and removing mechanisms with validation.
 */
import { reactive, computed, watch } from 'vue'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import FloatLabel from 'primevue/floatlabel'
import { useConfirm } from 'primevue/useconfirm'

import { isValidChemicalFormula } from '@/lib/chem'
import { useApp } from '@/stores'

const app = useApp()
const confirm = useConfirm()

const add = reactive({
  mechanism: ''
})

const resetFields = () => {
  add.mechanism = ''
}

const polarityValid = computed(() => ['+', '-'].includes(add.mechanism.trim().slice(-1)))
const prefixValid = computed(() => ['+', '-'].includes(add.mechanism.trim()[0]))
const modificationValid = computed(() => {
  const mech = add.mechanism.trim()
  if (mech.length == 1) return true // Only polarity present
  const core = mech.slice(1, -1)
  return isValidChemicalFormula(core)
})

// reset when create successful
watch(
  computed(() => app.data.ionization.mechanism.list.length),
  (newVal, oldVal) => {
    if (newVal > oldVal) {
      resetFields()
    }
  }
)

// Expose resetFields for parent component
defineExpose({
  resetFields
})
</script>

<template>
  <menu class="row" style="margin-top: 1.5rem">
    <FloatLabel style="flex-grow: 1">
      <InputText
        v-model="add.mechanism"
        id="add-mechanism"
        :invalid="!modificationValid || !prefixValid || !polarityValid"
        style="width: 100%"
      />
      <label for="add-mechanism">Mechanism*</label>
    </FloatLabel>
    <Button
      label="Add"
      icon="pi pi-plus"
      @click="
        () =>
          app.data.ionization.mechanism.create({
            ionization_mechanism: add.mechanism.trim()
          })
      "
      :disabled="!add.mechanism.trim() || !modificationValid || !prefixValid || !polarityValid"
    />
  </menu>
  <section style="margin: 1rem 0">
    <DataTable
      :value="app.data.ionization.mechanism.list"
      tableStyle="width: 500px"
      scrollable
      scrollHeight="calc(85vh - 260px)"
    >
      <Column field="ionization_mechanism_polarity" header="Polarity" width="2rem" sortable />
      <Column field="ionization_mechanism" header="Mechanism" width="40%" sortable />
      <Column field="ionization_mechanism_id" width="2rem">
        <template #body="{ data }">
          <Button
            v-tooltip="'Delete mechanism'"
            label="Delete mechanism"
            class="hiddenlabel"
            icon="pi pi-trash"
            text
            size="small"
            @click="
              () => {
                confirm.require({
                  icon: 'pi pi-exclamation-triangle',
                  header: `Delete ionization mechanism '${data.ionization_mechanism}'`,
                  message: `Are you sure you want to delete the ionization mechanism '${data.ionization_mechanism}'?`,
                  accept: () => {
                    app.data.ionization.mechanism.delete(data.ionization_mechanism_id)
                  },
                  acceptProps: {
                    icon: 'pi pi-trash',
                    label: 'Delete',
                    severity: 'danger'
                  },
                  rejectProps: {
                    label: 'Cancel',
                    severity: 'secondary'
                  }
                })
              }
            "
          />
        </template>
      </Column>
    </DataTable>
  </section>
</template>

<style scoped>
section :deep(*) {
  overflow-x: hidden !important;
}
</style>
