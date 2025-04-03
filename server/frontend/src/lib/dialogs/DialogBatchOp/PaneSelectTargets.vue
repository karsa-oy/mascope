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

import { ref, computed } from 'vue'

import { useApp } from '@/stores'

const app = useApp()

const selected = defineModel('selected')

const props = defineProps({
  mode: {
    default: 'targets',
    type: String
  },
  batch: {
    type: String
  }
})

const search = ref()

const categories = ['Targets', 'Calibrants', 'Diagnostics', 'All']
const category = ref(categories.find((c) => c.toLowerCase() == props.mode.toLowerCase()))

const targetCollections = computed(() =>
  app.data.target.collection.list
    .filter((coll) => {
      const type = category.value.toUpperCase()
      return type == 'ALL' ? true : coll.target_collection_type == type
    })
    .filter(
      (coll) =>
        coll.target_collection_name.toLowerCase().includes(search.value?.toLowerCase() ?? '') ||
        coll.target_collection_description.toLowerCase().includes(search.value?.toLowerCase() ?? '')
    )
)
</script>

<template>
  <Panel>
    <div class="row">
      <SelectButton v-model="category" :options="categories" :allowEmpty="false" />
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
