<script setup>
/**
 *  Dialog for managing ionization mechanisms
 *
 *  Allows adding and removing mechanisms.
 */
import { reactive, computed, watch } from 'vue'

import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import FloatLabel from 'primevue/floatlabel'
import { useConfirm } from 'primevue/useconfirm'

import { useApp } from '@/stores'

const app = useApp()
const confirm = useConfirm()

const visible = defineModel('visible')

const add = reactive({
  mechanism: '',
  reagent: ''
})
const resetFields = () => {
  add.mechanism = ''
  add.reagent = ''
}

const polarity = computed(() => add.mechanism.trim().slice(-1))
const polarityValid = computed(() => ['+', '-'].includes(polarity.value))
const prefix = computed(() => ['+', '-'].includes(add.mechanism.trim()[0]))
const prefixValid = computed(() => ['+', '-'].includes(prefix.value))

// reset when modal closed/opened
watch(visible, resetFields)
// reset when create successful
watch(
  computed(() => app.data.mechanism.list.length),
  (newVal, oldVal) => {
    if (newVal > oldVal) {
      resetFields()
    }
  }
)
</script>

<template>
  <Dialog
    v-model:visible="visible"
    header="Edit ionization mechanisms"
    modal
    style="max-width: 700px; min-height: 85vh"
  >
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
            app.data.mechanism.create({
              ionization_mechanism_polarity: polarity,
              ionization_mechanism: add.mechanism.trim(),
              reagent: add.reagent.trim()
            })
        "
        :disabled="(!add.mechanism.trim() && !add.reagent.trim()) || !polarityValid"
      />
    </menu>
    <section style="margin: 1rem 0">
      <DataTable
        :value="app.data.mechanism.list"
        tableStyle="width: 500px"
        scrollable
        scrollHeight="calc(85vh - 200px)"
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
                    header: `Delete ionization mechanism '${data.ionization_mechanism}'`,
                    message: `Are you sure you want to delete the ionization mechanism '${data.ionization_mechanism}'?`,
                    icon: 'pi pi-exclamation-triangle',
                    rejectProps: {
                      label: 'Cancel',
                      severity: 'secondary'
                    },
                    acceptProps: {
                      icon: 'pi pi-trash',
                      label: 'Delete',
                      severity: 'danger'
                    },
                    accept: () => {
                      app.data.mechanism.delete(data.ionization_mechanism_id)
                    }
                  })
                }
              "
            />
          </template>
        </Column>
      </DataTable>
    </section>
    <menu>
      <Button label="Close" @click="visible = false" />
    </menu>
  </Dialog>
</template>

<style scoped>
section :deep(*) {
  overflow-x: hidden !important;
}
</style>
