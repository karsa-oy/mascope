<script setup>
import { ref, reactive, computed, watchEffect } from 'vue'

import BaseMatchTag from '@/lib/base/BaseMatchTag.vue'

import DialogTargetCollectionOp from '@/lib/dialogs/DialogTargetCollectionOp.vue'

import { useSampleStore, useBatchStore, useVisualizationStore } from '@/stores'

const sampleStore = useSampleStore()
const batchStore = useBatchStore()
const visualizationStore = useVisualizationStore()

const emit = defineEmits(['focused'])

const expanded = reactive({
  collections: {},
  compounds: {},
  ions: {}
})
const selected = reactive({
  collection: null,
  compound: null,
  ion: null,
  isotope: null
})
const context = reactive({
  collection: null
})

const dialog = reactive({
  collection: null
})

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const collections = computed(() =>
  sampleStore.active && sampleStore.matchCollections && sampleStore.matchCollections.length > 0
    ? sampleStore.matchCollections
    : batchStore.targetCollections
)
const compounds = computed(() => {
  if (!sampleStore.active || !sampleStore.matchCompounds) {
    return batchStore.targetCompounds
  }
  return batchStore.targetCompounds.map((target) => {
    const match = sampleStore.matchCompounds.find(
      (mc) => mc.target_compound_id === target.target_compound_id
    )
    return match ? { ...target, ...match } : target
  })
})
const ions = computed(() => {
  if (!sampleStore.active || !sampleStore.matchIons) {
    return batchStore.targetIons
  }
  return batchStore.targetIons.map((target) => {
    const match = sampleStore.matchIons.find((mi) => mi.target_ion_id === target.target_ion_id)
    return match ? { ...target, ...match } : target
  })
})
const isotopes = computed(() => {
  if (!sampleStore.active || !sampleStore.matchIsotopes) {
    return batchStore.targetIsotopes
  }
  const matchIsotopeIds = new Set(sampleStore.matchIsotopes.map((mi) => mi.target_isotope_id))
  const isotopes = batchStore.targetIsotopes
    .filter(({ target_isotope_id }) => matchIsotopeIds.has(target_isotope_id))
    .map((targetIsotope) => {
      const matchIsotope = sampleStore.matchIsotopes.find(
        (mis) => mis.target_isotope_id === targetIsotope.target_isotope_id
      )

      return matchIsotope ? { ...targetIsotope, ...matchIsotope } : targetIsotope
    })
  return isotopes
})
const tree = computed(() =>
  // collections
  collections.value.map((coll) => ({
    ...coll,
    // compounds
    children: compounds.value
      .filter((comp) => comp.target_collection_id == coll.target_collection_id)
      .map((comp) => ({
        ...comp,
        // ions
        children: ions.value
          .filter(
            (ion) =>
              ion.target_compound_id == comp.target_compound_id &&
              ion.target_collection_id == coll.target_collection_id
          )
          .map((ion) => ({
            ...ion,
            // isotopes
            children: isotopes.value.filter(
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

const menu = computed(() => ({
  collection: [
    {
      label: 'Edit collection',
      icon: 'pi pi-pen-to-square',
      command: () => (dialog.collection = 'update')
    },
    {
      label: 'Edit batches',
      icon: 'pi pi-pen-to-square',
      command: () => (dialog.collection = 'update_batches')
    },
    {
      label: 'Delete collection',
      icon: 'pi pi-trash',
      command: () => (dialog.collection = 'delete')
    }
  ]
}))

async function showMatch(row) {
  const ionId =
    row?.target_ion_id ??
    sampleStore.matchIons?.find((ion) => ion.target_compound_id === row.target_compound_id)
      ?.target_ion_id
  if (ionId && sampleStore.active && visualizationStore.activeIon?.target_ion_id !== ionId) {
    await visualizationStore.load({
      sampleId: sampleStore.active.sample_item_id,
      ionId,
      collectionId: row?.target_collection_id,
      // pass the ion specific filter params if available to the loadSampleIon function
      filterParams: sampleStore.matchIons.find((ion) => ion.target_ion_id === ionId)?.filter_params[
        sampleStore.active.instrument
      ]
    })
    emit('focused')
  }
}
async function hideMatch() {
  if (!selected.compound) {
    visualizationStore.unload()
  } else {
    showMatch(selected.compound)
  }
}

watchEffect(() => {
  const collection_id = selected.collection?.target_collection_id
  if (collection_id && !(collection_id in expanded.collections)) {
    expanded.collections = { [collection_id]: true }
  }
})

watchEffect(() => {
  if (selected.collection) {
    const collectionId = selected.collection.target_collection_id
    expanded.collections = { [collectionId]: true }
    selected.compound = null
    selected.ion = null
    selected.isotope = null
  } else {
    expanded.collections = {}
    selected.compound = null
    selected.ion = null
    selected.isotope = null
  }
})
watchEffect(() => {
  if (selected.compound) {
    if (selected.ion?.target_compound_id !== selected.compound.target_compound_id) {
      selected.ion = null
      selected.isotope = null
    }
  }
})
watchEffect(() => {
  if (selected.ion) {
    selected.compound = compounds.value.find(
      ({ target_compound_id }) => selected.ion.target_compound_id == target_compound_id
    )
    if (selected.isotope?.target_ion_id !== selected.ion.target_ion_id) {
      selected.isotope = null
    }
  }
})
watchEffect(() => {
  if (selected.isotope) {
    selected.ion = ions.value.find(
      ({ target_ion_id }) => selected.isotope.target_ion_id == target_ion_id
    )
  }
})
</script>

<template v-if="collections">
  <Panel style="border: none" class="k-browser">
    <template #header>
      <TabMenu :model="[{ label: 'Targets', icon: 'pi pi-bullseye' }]" />
    </template>
    <template #icons>
      <Button
        icon="pi pi-plus"
        text
        size="small"
        v-tooltip="'Create collection'"
        @click="() => (dialog.collection = 'create')"
      />
    </template>
    <ScrollPanel class="k-browser-target-scroller">
      <!-- collections -->
      <DataTable
        :value="tree"
        v-model:expandedRows="expanded.collections"
        dataKey="target_collection_id"
        v-model:selection="selected.collection"
        selectionMode="single"
        :metaKeySelection="false"
        contextMenu
        v-model:contextMenuSelection="context.collection"
        @rowContextmenu="collectionPreventDefault"
        size="small"
        sortField="match_score"
        :sortOrder="-1"
      >
        <Column field="match_score" sortable class="k-match-column">
          <template #header>
            <span class="pi pi-verified" />
          </template>
          <template #body="{ data }">
            <BaseMatchTag
              v-if="sampleStore.active"
              :row="data"
              :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area_sum)}`"
            />
          </template>
        </Column>
        <Column header="Collection" field="target_collection_name" sortable>
          <template #body="{ data }">
            <span
              :class="`pi pi-chevron-${data.sample_batch_id in expanded.collections ? 'down' : 'right'}`"
              style="font-size: smaller; margin-right: 0.5rem"
            />
            {{ data.target_collection_name }}
          </template>
        </Column>
        <template #expansion="{ data }">
          <!-- compounds   -->
          <DataTable
            v-if="data.children.length > 0"
            :value="data.children"
            v-model:expandedRows="expanded.compounds"
            dataKey="target_compound_id"
            v-model:selection="selected.compound"
            selectionMode="single"
            :metaKeySelection="false"
            @rowSelect="(e) => showMatch(e.data)"
            @rowUnselect="hideMatch"
            size="small"
            sortField="match_score"
            :sortOrder="-1"
          >
            <Column field="match_score" sortable class="k-match-column">
              <template #header>
                <span class="pi pi-verified" />
              </template>
              <template #body="{ data }">
                <BaseMatchTag
                  v-if="sampleStore.active"
                  :row="data"
                  :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area_sum)}`"
                />
              </template>
            </Column>
            <Column expander style="width: 1ch" />
            <Column header="Compound" field="target_compound_formula" sortable />
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
                v-model:expandedRows="expanded.ions"
                dataKey="target_ion_id"
                v-model:selection="selected.ion"
                selectionMode="single"
                :metaKeySelection="false"
                @rowSelect="(e) => showMatch(e.data)"
                @rowUnselect="hideMatch"
                size="small"
                sortField="match_score"
                :sortOrder="-1"
              >
                <Column field="match_score" sortable class="k-match-column">
                  <template #header>
                    <span class="pi pi-verified" />
                  </template>
                  <template #body="{ data }">
                    <BaseMatchTag
                      v-if="sampleStore.active"
                      :row="data"
                      :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area_sum)}`"
                    />
                  </template>
                </Column>
                <Column expander style="width: 1ch" />
                <Column header="Ion" field="target_ion_formula" sortable />
                <Column header="Mechanism" field="ionization_mechanism" sortable />

                <template #expansion="{ data }">
                  <!-- isotopes   -->
                  <DataTable
                    v-if="data.children.length > 0"
                    :value="data.children"
                    dataKey="target_isotope_id"
                    v-model:selection="selected.isotope"
                    selectionMode="single"
                    :metaKeySelection="false"
                    @rowSelect="(e) => showMatch(e.data)"
                    size="small"
                    sortField="match_score"
                    :sortOrder="-1"
                  >
                    <Column field="match_score" sortable class="k-match-column">
                      <template #header>
                        <span class="pi pi-verified" />
                      </template>
                      <template #body="{ data }">
                        <BaseMatchTag
                          v-if="sampleStore.active"
                          :row="data"
                          :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area_sum)}`"
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
                  <div class="k-spinner" v-else>
                    <ProgressSpinner strokeWidth="5px" />loading...
                  </div>
                </template>
              </DataTable>
              <div class="k-spinner" v-else><ProgressSpinner strokeWidth="5px" />loading...</div>
            </template>
          </DataTable>
          <div class="k-spinner" v-else><ProgressSpinner strokeWidth="5px" />loading...</div>
        </template>
      </DataTable>
      <ContextMenu ref="collectionContextMenu" :model="menu.collection" />
    </ScrollPanel>
  </Panel>
  <DialogTargetCollectionOp v-model:action="dialog.collection" :collection="context.collection" />
</template>
