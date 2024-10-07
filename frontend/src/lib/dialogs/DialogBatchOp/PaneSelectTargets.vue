<script setup>
import ScrollPanel from 'primevue/scrollpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Panel from 'primevue/panel'
import SelectButton from 'primevue/selectbutton'

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

const categories = ['Targets', 'Calibrants', 'Diagnostics', 'All']
const category = ref(categories.find((c) => c.toLowerCase() == props.mode.toLowerCase()))

const targetCollections = computed(() =>
  app.data.target.collection.list.filter((coll) => {
    const type = category.value.toUpperCase()
    return type == 'ALL' ? true : coll.target_collection_type == type
  })
)

// init
if (props.mode == 'calibrants' && !selected.value) {
  // if autosetting fails inform user
  // notificationStore.showWarningNotification({
  //   notification: 'noCalibrationCollection',
  //   data: {
  //     batch: props.batch,
  //     collection: selected.value?.target_collection_name ?? 'none'
  //   }
  // })
}
</script>

<template>
  <Panel>
    <SelectButton v-model="category" :options="categories" :allowEmpty="false" />
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
.p-selectbutton {
  margin-bottom: 1rem;
}
</style>
