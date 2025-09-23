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

import { useApp } from '@/stores'

const app = useApp()
const confirm = useConfirm()

const add = reactive({
  mechanism: '',
  reagent: null
})

const resetFields = () => {
  add.mechanism = ''
  add.reagent = null
}

const polarityValid = computed(() => ['+', '-'].includes(add.mechanism.trim().slice(-1)))
const prefixValid = computed(() => ['+', '-'].includes(add.mechanism.trim()[0]))

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
        :invalid="add.mechanism.trim().length >= 3 || !prefixValid || !polarityValid"
        style="width: 100%"
      />
      <label for="add-mechanism">Mechanism*</label>
    </FloatLabel>
    <FloatLabel style="flex-grow: 1">
      <InputText v-model="add.reagent" id="add-reagent" style="width: 100%" />
      <label for="add-reagent">Reagent</label>
    </FloatLabel>
    <Button
      label="Add"
      icon="pi pi-plus"
      @click="
        () =>
          app.data.ionization.mechanism.create({
            ionization_mechanism: add.mechanism.trim(),
            reagent: add.reagent?.trim() || null
          })
      "
      :disabled="
        (!add.mechanism.trim() && !(add.reagent && add.reagent.trim())) ||
        !prefixValid ||
        !polarityValid
      "
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
      <Column field="reagent" header="Reagent" width="40%" sortable />
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
