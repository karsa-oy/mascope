<script setup>
import ScrollPanel from 'primevue/scrollpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Panel from 'primevue/panel'
import SelectButton from 'primevue/selectbutton'
import FloatLabel from 'primevue/floatlabel'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'

import { ref, computed, watch } from 'vue'

import { useApp } from '@/stores'
import { collectionTypes, getAllowedCollectionTypes } from '@/lib/constants'
import { beautifyConstant, instrumentType } from '@/lib/utils'

const app = useApp()

const selected = defineModel('selected')

const props = defineProps({
  mode: {
    default: 'targets',
    type: String
  },
  batch: {
    type: Object
  }
})

const search = ref()

const allowedTypes = computed(() => {
  if (props.mode === 'calibrants') {
    return ['CALIBRANTS'] // Only CALIBRANTS collections for calibrants mode
  }

  if (!props.batch?.type) {
    return collectionTypes // Show all types if batch type not set
  }

  // For targets mode, use batch type constraints
  let allowed = getAllowedCollectionTypes(props.batch.type)

  // Special case: TOF instruments can use CALIBRANTS for ACQUISITION batches
  if (props.batch.type === 'ACQUISITION') {
    const currentInstrument = app.data.workspace.focused?.instrument
    if (instrumentType(currentInstrument) === 'tof') {
      allowed = [...new Set([...allowed, 'CALIBRANTS'])]
    }
  }

  return allowed
})

const categoryOptions = computed(() => [
  ...collectionTypes.map((type) => ({
    label: beautifyConstant(type),
    value: beautifyConstant(type),
    disabled: !allowedTypes.value.includes(type)
  })),
  {
    label: 'All',
    value: 'All',
    disabled: allowedTypes.value.length <= 1
  }
])

const category = ref()

// Initialize category based on mode and available options
watch(
  allowedTypes,
  () => {
    const modeOption = beautifyConstant(props.mode.toUpperCase())
    category.value = allowedTypes.value.includes(props.mode.toUpperCase())
      ? modeOption
      : allowedTypes.value.length > 1
        ? 'All'
        : beautifyConstant(allowedTypes.value[0])
  },
  { immediate: true }
)
const targetCollections = computed(() =>
  app.data.target.collection.list.filter((coll) => {
    // Filter by allowed types for this batch
    if (!allowedTypes.value.includes(coll.target_collection_type)) return false

    // Filter by selected category
    if (
      category.value !== 'All' &&
      beautifyConstant(coll.target_collection_type) !== category.value
    ) {
      return false
    }

    // Filter by search
    const query = search.value?.toLowerCase() ?? ''
    return (
      coll.target_collection_name.toLowerCase().includes(query) ||
      coll.target_collection_description?.toLowerCase().includes(query)
    )
  })
)
</script>

<template>
  <Panel>
    <div class="row">
      <SelectButton
        v-model="category"
        :options="categoryOptions"
        optionLabel="label"
        optionValue="value"
        optionDisabled="disabled"
        :allowEmpty="false"
      />
      <FloatLabel style="flex-grow: 1; max-width: 250px">
        <IconField class="full">
          <InputIcon>
            <i class="pi pi-search" />
          </InputIcon>
          <InputText v-model="search" placeholder="Search" />
        </IconField>
      </FloatLabel>
    </div>
    <ScrollPanel style="width: 100%; height: 300px">
      <DataTable v-model:selection="selected" :value="targetCollections">
        <Column v-if="mode == 'targets'" selectionMode="multiple" headerStyle="width: 3rem" />
        <Column v-else selectionMode="single" headerStyle="width: 3rem" />
        <Column header="Name" field="target_collection_name" />
        <Column header="Description" field="target_collection_description" />
      </DataTable>
    </ScrollPanel>
  </Panel>
</template>

<style scoped>
.row {
  margin-bottom: 1rem;
  height: fit-content;
}

:deep(.p-floatlabel) {
  margin: 0;
}
</style>
