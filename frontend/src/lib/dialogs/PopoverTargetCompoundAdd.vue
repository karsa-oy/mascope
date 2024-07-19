<script setup>
import Popover from 'primevue/popover'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { useConfirm } from 'primevue/useconfirm'

import { ref, reactive } from 'vue'

import { api } from '@/api'
import { useApp } from '@/stores'

const confirm = useConfirm()
const app = useApp()

const props = defineProps({
  collection: {
    required: true,
    type: Object
  }
})

const popover = ref()

const input = reactive({
  target_compound_formula: '',
  target_compound_name: null,
  cas_number: null
})

const addCompound = () => {
  const prexisting = app.data.target.compound.list.find(
    (comp) => comp.target_compound_formula === input.target_compound_formula
  )
  const common = {
    target_collection_id: props.collection.target_collection_id,
    target_collection_name: props.collection.target_collection_name,
    target_collection_type: props.collection.target_collection_type
  }
  if (prexisting) {
    app.data.target.collection.update({
      ...common,
      target_compound_ids: [
        ...props.collection.children.map(({ target_compound_id }) => target_compound_id),
        prexisting.target_compound_id
      ]
    })
  } else {
    app.data.target.collection.update({
      ...common,
      target_compound_ids: props.collection.children.map(
        ({ target_compound_id }) => target_compound_id
      ),
      target_compounds_create: [input]
    })
  }
  popover.value.hide()
}

const confirmation = async () => {
  let count = (
    await api.request.read({
      method: 'getTargetCollection',
      body: props.collection.target_collection_id
    })
  )?.sample_batches.length
  if (count > 1) {
    confirm.require({
      message: `Are you sure you want to add this compound to a collection used in ${count} batches? Rematching may take a while...`,
      header: `Add compound to ${count} batches`,
      icon: 'pi pi-exclamation-triangle',
      rejectProps: {
        label: 'Cancel',
        severity: 'secondary'
      },
      acceptProps: {
        icon: 'pi pi-plus',
        label: 'Add'
      },
      accept: addCompound
    })
  } else {
    addCompound()
  }
}
</script>

<template>
  <Button
    icon="pi pi-plus"
    text
    size="small"
    v-tooltip="'Add compound'"
    @click="
      (event) => {
        popover.toggle(event)
      }
    "
  />
  <Popover ref="popover">
    <div class="col" style="gap: 0rem">
      <h4 style="margin: 1rem 0">Add compound to '{{ collection.target_collection_name }}'</h4>
      <FloatLabel style="margin: 1rem 0">
        <InputText id="add-compound-formula" required v-model="input.target_compound_formula" />
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
      <Button label="Add" style="width: 100%" @click="confirmation" />
    </div>
  </Popover>
</template>
