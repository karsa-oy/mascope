<script setup>
import { ref, reactive, computed, watch } from 'vue'

import FloatLabel from 'primevue/floatlabel'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

import { useApp } from '@/stores'

const app = useApp()

const action = defineModel('action')

const props = defineProps({
  workspace: {
    type: Object
  }
})

const original = computed(() =>
  action.value == 'create' ? null : app.data.workspace.focused ?? props.workspace
)

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
  const name = info.initial?.workspace_name ?? ''
  return {
    create: `Create a new workspace`,
    edit: `Edit workspace '${name}'`,
    delete: `Delete workspace '${name}'`
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
    case 'create': {
      await app.data.workspace.create({
        workspace_name: info.name,
        workspace_description: info.desc
      })
      break
    }
    case 'edit': {
      app.data.workspace.update({
        workspace_id: original.value.workspace_id,
        workspace_name: info.name,
        workspace_description: info.desc
      })
      break
    }
    case 'delete': {
      const nextWorkspace = app.data.workspace.list.find(
        ({ workspace_id }) => workspace_id !== original.value.workspace_id
      )
      if (nextWorkspace) {
        const prevWorkspace = original.value
        app.data.workspace.focus(nextWorkspace.workspace_id)
        app.data.workspace.delete(prevWorkspace)
      } else {
        info.message =
          'You cannot delete the last remaining workspace in the database. Create a new workspace before deleting this one.'
      }
      break
    }
  }
  if (!info.message) {
    action.value = null
  }
}

watch(action, init)
function init() {
  info.name = original.value?.workspace_name
  info.desc = original.value?.workspace_description
  ;(info.message = null), (info.initial = original.value)
}
</script>

<template>
  <Dialog v-model:visible="visible" :header="title" modal style="max-width: 600px">
    <section>
      <template v-if="action !== 'delete'">
        <FloatLabel>
          <InputText id="workspace-name" v-model="info.name" />
          <label for="workspace-name">Name</label>
        </FloatLabel>
        <FloatLabel>
          <InputText id="workspace-desc" v-model="info.desc" />
          <label for="workspace-desc">Description</label>
        </FloatLabel>
      </template>
      <template v-else>
        <p v-if="info.message">{{ info.message }}</p>
        <p v-else>
          Are you sure you want to delete the '{{ info.initial?.workspace_name }}' workspace?
        </p>
      </template>
    </section>
    <menu>
      <Button label="Cancel" @click="action = null" severity="secondary" />
      <Button :label="executeLabel" @click="execute" v-if="!info.message" />
    </menu>
  </Dialog>
</template>
