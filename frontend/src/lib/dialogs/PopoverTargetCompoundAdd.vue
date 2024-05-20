<script setup>
import Popover from 'primevue/popover'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

import { ref, reactive } from 'vue'

import { useTargetsStore } from '@/stores'

const targetsStore = useTargetsStore()

defineProps({
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
      <Button
        label="Add"
        style="width: 100%"
        @click="
          () => {
            const prexisting = targetsStore.targetCompoundsAll.find(
              (comp) => comp.target_compound_formula === input.target_compound_formula
            )
            const common = {
              target_collection_id: collection.target_collection_id,
              target_collection_name: collection.target_collection_name,
              target_collection_type: collection.target_collection_type
            }
            if (prexisting) {
              targetsStore.updateCollection({
                ...common,
                target_compound_ids: [
                  ...collection.children.map(({ target_compound_id }) => target_compound_id),
                  prexisting.target_compound_id
                ]
              })
            } else {
              targetsStore.updateCollection({
                ...common,
                target_compound_ids: collection.children.map(
                  ({ target_compound_id }) => target_compound_id
                ),
                target_compounds_create: [input]
              })
            }
            popover.hide()
          }
        "
      />
    </div>
  </Popover>
</template>
