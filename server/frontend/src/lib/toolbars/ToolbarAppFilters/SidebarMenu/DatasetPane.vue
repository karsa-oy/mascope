<script setup>
import { ref, watch, watchEffect, computed } from 'vue'

import Button from 'primevue/button'
import Listbox from 'primevue/listbox'
import ContextMenu from 'primevue/contextmenu'

import { useApp } from '@/stores'
import { DialogDatasetOp } from '@/lib/dialogs'

import { useSidebarMenu } from './state.js'

const app = useApp()
const sidebarMenu = useSidebarMenu()
const open = computed(() => sidebarMenu.open && sidebarMenu.tab === 'datasets')

const dialog = ref()
const datasetContextMenu = ref()
const selectedDataset = ref(null)

watch(
  () => app.data.dataset.focused,
  () => {
    if (sidebarMenu.open) {
      sidebarMenu.open = false
    }
  }
)

const layer = 'sidebar_datasets_tab'
watchEffect(() => {
  if (open.value) {
    app.ui.help.set(layer)
  }
})

const vHelpLayer = app.ui.help.directive(layer)
</script>

<template>
  <div
    v-help-layer.right="
      `
      <b>Datasets</b>
      <p>
        Select and manage datasets. Datasets are like folders
        containing batches. Click on a dataset to open it and see its batches.
      </p>
      <p>Click on the Create button to create a new dataset</p>
      `
    "
  >
    <div class="row" style="align-items: center">
      <h2>Datasets</h2>
      <Button
        icon="pi pi-plus"
        @click="
          (event) => {
            dialog = 'create'
          }
        "
        label="Create"
        style="float: right"
      />
    </div>
    <section>
      <Listbox
        :modelValue="app.data.dataset.focused"
        @update:modelValue="
          (value) => {
            if (value) {
              // Selecting a different dataset
              app.data.dataset.focused = value
            } else if (!value && sidebarMenu.open) {
              // Tried to deselect (clicked same dataset) - close sidebar
              sidebarMenu.open = false
            }
          }
        "
        @contextmenu.prevent
        filter
        :filterPlaceholder="'Search datasets'"
        :options="app.data.dataset.list"
        optionLabel="dataset_name"
        listStyle="height: calc(100vh - 300px)"
        :pt="
          app.ui.help.bottom_start(`
          <h1>Dataset Selector</h1>

          <p>Datasets are the like folders that organize samples
          and targets relating to specific projects in one place.
          You can modify, create or delete datasets by clicking
          the ellipsis icon to the right of the dropdown.</p>
    `)
        "
      >
        <template #option="{ option }">
          <div
            class="row"
            style="gap: 1rem; width: 100%; justify-content: flex-start"
            @contextmenu="
              (event) => {
                event.preventDefault()
                selectedDataset = option
                datasetContextMenu.toggle(event)
              }
            "
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="32"
              height="32"
              fill="currentColor"
              viewBox="0 0 256 256"
              style="opacity: 0.3"
            >
              <path
                d="M216,72H130.67L102.93,51.2a16.12,16.12,0,0,0-9.6-3.2H40A16,16,0,0,0,24,64V200a16,16,0,0,0,16,16H216.89A15.13,15.13,0,0,0,232,200.89V88A16,16,0,0,0,216,72Zm0,128H40V64H93.33L123.2,86.4A8,8,0,0,0,128,88h88Z"
                v-if="option.dataset_type === 'ANALYSIS'"
              ></path>
              <path
                v-else
                d="M224,208H203.94A88.05,88.05,0,0,0,144,64.37V32a16,16,0,0,0-16-16H80A16,16,0,0,0,64,32V136a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V80.46A72,72,0,0,1,181.25,208H32a8,8,0,0,0,0,16H224a8,8,0,0,0,0-16Zm-96-72H80V32h48V136ZM72,184a8,8,0,0,1,0-16h64a8,8,0,0,1,0,16Z"
              ></path>
            </svg>
            <div class="col" style="gap: 1rem; align-items: flex-start">
              {{ option.dataset_name }}
              <span style="opacity: 0.5">{{ option.dataset_description }}</span>
            </div>
          </div>
        </template>
      </Listbox>
    </section>
  </div>
  <ContextMenu
    ref="datasetContextMenu"
    appendTo="self"
    :model="[
      {
        label: 'Edit dataset',
        icon: 'pi pi-pen-to-square',
        command: () => {
          dialog = 'edit'
        }
      },
      {
        label: 'Delete dataset',
        icon: 'pi pi-trash',
        command: () => {
          dialog = 'delete'
        }
      }
    ]"
  />
  <DialogDatasetOp v-model:action="dialog" :dataset="selectedDataset" />
</template>
