<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'

import FloatLabel from 'primevue/floatlabel'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

import { useApp } from '@/stores'

const app = useApp()

const action = defineModel('action')

const props = defineProps({
  dataset: {
    type: Object
  }
})

const original = computed(() => {
  if (action.value == 'create') {
    return null
  }
  // Use the passed dataset prop if available, otherwise use the focused dataset
  return props.dataset ?? app.data.dataset.focused
})

const info = reactive({
  name: null,
  desc: null,
  message: null,
  initial: null
})

// dialog visibility reactivity
const visible = ref(false)
watch(action, (value) => {
  visible.value = !!value
})
watch(visible, (value) => {
  if (!value) {
    action.value = null
  }
})

const title = computed(() => {
  const name = info.initial?.dataset_name ?? ''
  return {
    create: `Create a new dataset`,
    edit: `Edit dataset '${name}'`,
    delete: `Delete dataset '${name}'`
  }[action.value]
})

const executeLabel = computed(() => {
  return {
    create: `Create`,
    edit: `Save`,
    delete: `Delete`
  }[action.value]
})

async function execute() {
  switch (action.value) {
    /**
     * Handles the creation of a new dataset.
     * - After successfully creating the dataset, it sets up a one-time watcher.
     * - The watcher focuses on the newly created dataset once it is added to the dataset list.
     */
    case 'create': {
      const response = await app.data.dataset.create({
        dataset_name: info.name,
        dataset_description: info.desc
      })
      app.data.dataset.lazyFocus({
        dataset_id: response.data.dataset_id
      })
      break
    }
    case 'edit': {
      app.data.dataset.update({
        dataset_id: original.value.dataset_id,
        dataset_name: info.name,
        dataset_description: info.desc
      })
      break
    }
    /**
     * Handles the deletion of a dataset.
     * - Determines the next dataset to focus on (previous in the list or next one).
     * - Sets up a one-time watcher to focus on the new dataset after the current one is deleted.
     */
    case 'delete': {
      if (app.data.dataset.list.length > 1) {
        app.data.dataset.delete(original.value)
      } else {
        info.message =
          'You cannot delete the last remaining dataset in the database. Create a new dataset before deleting this one.'
      }
      break
    }
  }
  if (!info.message) {
    action.value = null
  }
}

// Initialize the dialog fields based on the selected action
watch(action, init)
function init() {
  info.name = original.value?.dataset_name
  info.desc = original.value?.dataset_description
  ;((info.message = null), (info.initial = original.value))
}

const invalid = computed(() =>
  action.value == 'create' ? (info.name?.trim().length ?? 0) == 0 : false
)
</script>

<template>
  <Dialog v-model:visible="visible" :header="title" modal style="max-width: 600px">
    <section>
      <template v-if="action !== 'delete'">
        <FloatLabel>
          <InputText id="dataset-name" v-model="info.name" />
          <label for="dataset-name">Name</label>
        </FloatLabel>
        <FloatLabel>
          <InputText id="dataset-desc" v-model="info.desc" />
          <label for="dataset-desc">Description</label>
        </FloatLabel>
      </template>
      <template v-else>
        <p v-if="info.message">{{ info.message }}</p>
        <p v-else>
          Are you sure you want to delete the '{{ info.initial?.dataset_name }}' dataset?
        </p>
      </template>
    </section>
    <menu>
      <Button label="Cancel" @click="action = null" severity="secondary" />
      <Button :label="executeLabel" @click="execute" v-if="!info.message" :disabled="invalid" />
    </menu>
  </Dialog>
</template>
