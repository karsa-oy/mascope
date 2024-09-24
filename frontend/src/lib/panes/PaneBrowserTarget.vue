<script setup>
import { ref, reactive, computed, watch } from 'vue'

import Panel from 'primevue/panel'
import Button from 'primevue/button'
import TabMenu from 'primevue/tabmenu'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import ContextMenu from 'primevue/contextmenu'
import { useConfirm } from 'primevue/useconfirm'

import { BaseMatchTag } from '@/lib/base'
import {
  DialogTargetCollectionOp,
  PopoverTargetCompoundAdd,
  DialogTargetCompoundUpdate,
  DialogMechanismsOp
} from '@/lib/dialogs'

import { useApp } from '@/stores'

const confirm = useConfirm()

const app = useApp()

const emit = defineEmits(['focused'])

const expanded = computed(() => ({
  collection: app.data.match.collection.focused
    ? {
        [app.data.match.collection.focused.target_collection_id]: true
      }
    : {},
  compound: app.data.match.compound.focused
    ? {
        [app.data.match.compound.focused.target_compound_id]: true
      }
    : {},
  ion: app.data.match.ion.focused
    ? {
        [app.data.match.ion.focused.target_ion_id]: true
      }
    : {},
  isotope: app.data.match.isotope.focused
    ? {
        [app.data.match.isotope.focused.target_isotope_id]: true
      }
    : {}
}))

const context = reactive({
  collection: null,
  compound: null
})

const dialog = reactive({
  collection: null,
  compound: false,
  mechanisms: false
})

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const tree = computed(() =>
  // collections
  app.data.match.collection.list.map((coll) => ({
    ...coll,
    // compounds
    children: app.data.match.compound.list
      .filter((comp) => comp.target_collection_id == coll.target_collection_id)
      .map((comp) => ({
        ...comp,
        // ions
        children: app.data.match.ion.list
          .filter(
            (ion) =>
              ion.target_compound_id == comp.target_compound_id &&
              ion.target_collection_id == coll.target_collection_id
          )
          .map((ion) => ({
            ...ion,
            // isotopes
            children: app.data.match.isotope.list.filter(
              (iso) =>
                iso.target_ion_id == ion.target_ion_id &&
                iso.target_collection_id == coll.target_collection_id
            )
          }))
      }))
  }))
)

const collectionContextMenu = ref()
const collectionPreventDefault = (event) => {
  collectionContextMenu.value.show(event.originalEvent)
}
const compoundContextMenu = ref()
const compoundPreventDefault = (event) => {
  compoundContextMenu.value.show(event.originalEvent)
}

const menu = computed(() => ({
  collection: [
    {
      label: 'Edit collection',
      icon: 'pi pi-pen-to-square',
      command: () => {
        dialog.collection = 'update'
      }
    },
    {
      label: 'Edit batches',
      icon: 'pi pi-pen-to-square',
      command: () => {
        dialog.collection = 'update_batches'
      }
    },
    {
      label: 'Delete collection',
      icon: 'pi pi-trash',
      command: () => {
        dialog.collection = 'delete'
      }
    }
  ],
  compound: [
    {
      label: 'Edit compound',
      icon: 'pi pi-pen-to-square',
      command: () => {
        dialog.compound = true
      }
    },
    {
      label: 'Remove compound',
      icon: 'pi pi-minus',
      command: () => {
        const collection = tree.value.find(
          ({ target_collection_id }) =>
            target_collection_id == context.compound.target_collection_id
        )
        confirm.require({
          message: `Are you sure you want to remove the compound '${context.compound.target_compound_formula}' from the '${collection.target_collection_name}' collection?`,
          header: `Remove target compound '${context.compound.target_compound_formula}'`,
          icon: 'pi pi-exclamation-triangle',
          rejectProps: {
            label: 'Cancel',
            severity: 'secondary'
          },
          acceptProps: {
            icon: 'pi pi-minus',
            label: 'Remove'
          },
          accept: () => {
            app.data.target.collection.update({
              target_collection_id: collection.target_collection_id,
              target_collection_name: collection.target_collection_name,
              target_collection_type: collection.target_collection_type,
              target_compound_ids: collection.children
                .map(({ target_compound_id }) => target_compound_id)
                .filter((id) => id !== context.compound.target_compound_id)
            })
          }
        })
      }
    }
  ]
}))

async function showMatch(row) {
  const ionId =
    row?.target_ion_id ??
    app.data.match.ion.list?.find((ion) => ion.target_compound_id === row.target_compound_id)
      ?.target_ion_id
  if (ionId && app.data.sample.focused && app.ui.matchVisualized.ion?.target_ion_id !== ionId) {
    await app.ui.matchVisualized.set({
      sampleId: app.data.sample.focused.sample_item_id,
      ionId,
      collectionId: row?.target_collection_id,
      // pass the ion specific filter params if available to the loadSampleIon function
      params: app.data.match.ion.list.find((ion) => ion.target_ion_id === ionId)?.filter_params[
        app.data.sample.focused.instrument
      ]
    })
    emit('focused')
  }
}

// match refocus logic

/**
 * Watcher that monitors changes of the focused target collection.
 *
 * It unfocuses all child elements (compounds, ions, isotopes) and unsets the visualized Match when:
 *   1. A different collection is selected.
 *   2. The current collection is deselected.
 *
 * @param {Object|null} collection - The currently focused collection.
 * @param {Object|null} oldCollection - The previously focused collection.
 */
watch(
  computed(() => app.data.match.collection.focused),
  (collection, oldCollection) => {
    // Unfocus all child elements when switching collections or deselecting the current collection
    if (
      !collection ||
      (oldCollection && collection.target_collection_id !== oldCollection.target_collection_id)
    ) {
      app.data.match.compound.unfocus()

      // Unset the visualized match if the Match tab is active
      if (app.ui.matchVisualized.ion) app.ui.matchVisualized.unset({ target: true })
    }
  }
)
watch(
  computed(() => app.data.match.compound.focused),
  (compound) => {
    if (compound) {
      // focus parent if focused
      app.data.match.collection.focus(compound)
      // unfocus unrelated ions
      if (app.data.match.ion.focused?.target_compound_id !== compound.target_compound_id) {
        app.data.match.ion.unfocus()
      }
    } else {
      // unfocus child if unfocused
      app.data.match.ion.unfocus()
      // and unset visualized match
      app.ui.matchVisualized.unset()
    }
  }
)
watch(
  computed(() => app.data.match.ion.focused),
  (ion) => {
    if (ion) {
      // focus parent if focused
      app.data.match.compound.focus(ion)
      // unfocus unrelated isotopes
      if (app.data.match.isotope.focused?.target_ion_id !== ion.target_ion_id) {
        app.data.match.isotope.unfocus()
      }
    } else {
      // unfocus child if unfocused
      app.data.match.isotope.unfocus()
    }
  }
)
watch(
  computed(() => app.data.match.isotope.focused),
  (isotope) => {
    if (isotope) {
      // focus parent in focused
      app.data.match.ion.focus(isotope)
    }
  }
)
</script>

<template v-if="collections">
  <Panel style="border: none" class="browser">
    <template #header>
      <TabMenu :model="[{ label: 'Targets', icon: 'pi pi-bullseye' }]" />
    </template>
    <template #icons>
      <Button
        v-tooltip.left="'Edit mechanisms'"
        label="Edit mechanisms"
        class="hiddenlabel"
        icon="pi pi-sliders-h"
        text
        size="small"
        @click="
          () => {
            dialog.mechanisms = true
          }
        "
      />
      <Button
        v-tooltip="'Create collection'"
        label="Create collection"
        class="hiddenlabel"
        icon="pi pi-plus"
        text
        size="small"
        @click="
          () => {
            dialog.collection = 'create'
          }
        "
      />
    </template>
    <div class="scroller">
      <!-- collections -->
      <DataTable
        :value="tree"
        :expandedRows="expanded.collection"
        dataKey="target_collection_id"
        v-model:selection="app.data.match.collection.focused"
        selectionMode="single"
        :metaKeySelection="false"
        contextMenu
        v-model:contextMenuSelection="context.collection"
        @rowContextmenu="collectionPreventDefault"
        size="small"
        sortField="match_score"
        :sortOrder="-1"
      >
        <Column field="match_score" sortable class="match-column">
          <template #header>
            <span class="pi pi-verified" />
          </template>
          <template #body="{ data }">
            <BaseMatchTag
              :row="data"
              :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area_sum)}`"
            />
          </template>
        </Column>
        <Column header="Collection" field="target_collection_name" sortable>
          <template #body="{ data }">
            <span
              :class="`pi pi-chevron-${
                data.target_collection_id == app.data.match.collection.focused?.target_collection_id
                  ? 'down'
                  : 'right'
              }`"
              style="font-size: smaller; margin-right: 0.5rem"
            />
            {{ data.target_collection_name }}
          </template>
        </Column>
        <Column>
          <template #body="{ data }">
            <PopoverTargetCompoundAdd :collection="data" />
          </template>
        </Column>
        <template #expansion="{ data }">
          <!-- compounds   -->
          <DataTable
            v-if="data.children.length > 0"
            :value="data.children"
            :expandedRows="expanded.compound"
            dataKey="target_compound_id"
            v-model:selection="app.data.match.compound.focused"
            selectionMode="single"
            :metaKeySelection="false"
            v-model:contextMenuSelection="context.compound"
            @rowContextmenu="compoundPreventDefault"
            @rowSelect="(e) => showMatch(e.data)"
            size="small"
            sortField="match_score"
            :sortOrder="-1"
          >
            <Column field="match_score" sortable class="match-column">
              <template #header>
                <span class="pi pi-verified" />
              </template>
              <template #body="{ data }">
                <BaseMatchTag
                  :row="data"
                  :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area_sum)}`"
                />
              </template>
            </Column>
            <Column header="Compound" field="target_compound_formula" sortable>
              <template #body="{ data }">
                <span
                  :class="`pi pi-chevron-${
                    data.target_compound_id == app.data.match.compound.focused?.target_compound_id
                      ? 'down'
                      : 'right'
                  }`"
                  style="font-size: smaller; margin-right: 0.5rem"
                />
                {{ data.target_compound_formula }}
              </template>
            </Column>
            <Column header="Name" sortable>
              <template #body="{ data }">
                {{ data.target_compound_name }}
              </template>
            </Column>
            <template #expansion="{ data }">
              <!-- ions   -->
              <DataTable
                v-if="data.children.length > 0"
                :value="data.children"
                :expandedRows="expanded.ion"
                dataKey="target_ion_id"
                v-model:selection="app.data.match.ion.focused"
                selectionMode="single"
                :metaKeySelection="false"
                @rowSelect="(e) => showMatch(e.data)"
                size="small"
                sortField="match_score"
                :sortOrder="-1"
              >
                <Column field="match_score" sortable class="match-column">
                  <template #header>
                    <span class="pi pi-verified" />
                  </template>
                  <template #body="{ data }">
                    <BaseMatchTag
                      :row="data"
                      :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area_sum)}`"
                    />
                  </template>
                </Column>
                <Column header="Ion" field="target_ion_formula" sortable>
                  <template #body="{ data }">
                    <span
                      :class="`pi pi-chevron-${
                        data.target_ion_id == app.data.match.ion.focused?.target_ion_id
                          ? 'down'
                          : 'right'
                      }`"
                      style="font-size: smaller; margin-right: 0.5rem"
                    />
                    {{ data.target_ion_formula }}
                  </template>
                </Column>
                <Column header="Mechanism" field="ionization_mechanism" sortable />
                <template #expansion="{ data }">
                  <!-- isotopes   -->
                  <DataTable
                    v-if="data.children.length > 0"
                    :value="data.children"
                    dataKey="target_isotope_id"
                    v-model:selection="app.data.match.isotope.focused"
                    selectionMode="single"
                    :metaKeySelection="false"
                    @rowSelect="(e) => showMatch(e.data)"
                    size="small"
                    sortField="match_score"
                    :sortOrder="-1"
                  >
                    <Column field="match_score" sortable class="match-column">
                      <template #header>
                        <span class="pi pi-verified" />
                      </template>
                      <template #body="{ data }">
                        <BaseMatchTag
                          :row="data"
                          :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area)}`"
                        />
                      </template>
                    </Column>
                    <Column style="width: 4ch" />
                    <Column header="mz" field="mz" style="width: 15ch" sortable>
                      <template #body="{ data }">
                        {{ formatter.format(data.mz) }}
                      </template>
                    </Column>
                    <Column header="r.a." field="relative_abundance" sortable>
                      <template #body="{ data }">
                        {{ formatter.format(data.relative_abundance) }}
                      </template>
                    </Column>
                  </DataTable>
                  <div class="spinner" v-else><ProgressSpinner strokeWidth="5px" />loading...</div>
                </template>
              </DataTable>
              <div class="spinner" v-else><ProgressSpinner strokeWidth="5px" />loading...</div>
            </template>
          </DataTable>
          <div class="spinner" v-else><ProgressSpinner strokeWidth="5px" />loading...</div>
        </template>
      </DataTable>
      <ContextMenu ref="collectionContextMenu" :model="menu.collection" />
      <ContextMenu ref="compoundContextMenu" :model="menu.compound" />
    </div>
  </Panel>
  <DialogTargetCollectionOp v-model:action="dialog.collection" :collection="context.collection" />
  <DialogTargetCompoundUpdate v-model:visible="dialog.compound" :compound="context.compound" />
  <DialogMechanismsOp v-model:visible="dialog.mechanisms" />
</template>
