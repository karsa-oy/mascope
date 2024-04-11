<script setup>
import * as _ from 'underscore'
import { cloneDeep } from 'lodash'

import { dialog, toast } from '@/main'

import { ref, computed, watch, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

import BaseTable from '@/components/base/BaseTable.vue'
import ThePaneBrowserTarget from '@/components/panes/ThePaneBrowserTarget.vue'
import ThePaneSettingsCalibration from '@/components/panes/ThePaneSettingsCalibration.vue'

import TheLayoutSidebarView from '@/views/TheLayoutSidebarView.vue'

import { beautifySnakeCase, strToSnakeCase, genId } from '@/lib/util'

import {
  useAppStore,
  useBatchStore,
  useSampleStore,
  useInstrumentStore,
  useCalibrationStore,
  useWorkspaceStore
} from '@/stores'

const appStore = useAppStore()
const batchStore = useBatchStore()
const sampleStore = useSampleStore()
const instrumentStore = useInstrumentStore()
const calibrationStore = useCalibrationStore()
const workspaceStore = useWorkspaceStore()

const activeStep = ref(0)
const defaultTemplate = ref({
  name: 'default',
  template: [
    {
      label: 'sample_item_name',
      required: true,
      placeholder: 'Sample title'
    }
  ]
})
const formFields = ref([])
const loadedTemplate = ref(null)
const mzCalibrationTableCols = ref([
  { field: 'mz', label: 'Isotope m/z' },
  { field: 'sample_peak_mz', label: 'Pre peak m/z' },
  {
    field: 'match_mz_error',
    label: 'Pre m/z error [ppm]',
    subheading: null
  },
  { field: 'calibration_mz', label: 'Post peak m/z' },
  {
    field: 'calibration_mz_error',
    label: 'Post m/z error [ppm]',
    subheading: null
  },
  { field: 'mz_error_diff', label: 'm/z error diff', subheading: null },
  {
    field: 'calibrant_to_tic',
    label: 'fraction of TIC',
    subheading: null
  }
])
const mzCalibrationTableKey = ref(0)
const sampleItemFilterId = ref(null)
const sampleItemType = ref(null)
const showEditFunctions = ref(false)
const templateType = ref('sample_item')

onMounted(() => {
  sampleStore.unload()
  instrumentStore.scenthoundModeActive = true
  loadedTemplate.value = cloneDeep(defaultTemplate.value)
  formFields.value = [...defaultTemplate.value.template]
})

onBeforeRouteLeave((to, from, next) => {
  instrumentStore.scenthoundModeActive = false
  next()
})

const availableTemplates = computed(() => [defaultTemplate.value, ...savedTemplates.value])
const editable = computed(() => !instrumentStore.sampleItemPending)
const fillable = computed(
  () => instrumentStore.acquisitionActiveFilename && !instrumentStore.sampleItemPending
)
const batchFilterIds = computed(() =>
  batchStore.active ? [null, ...new Set(batchStore.sampleItems.map((item) => item.filter_id))] : []
)
const calibrationProgress = computed(() =>
  calibrationStore.calibrationStatus ? calibrationStore.calibrationStatus.progress : 0
)
const filterIsNew = computed(() => !batchFilterIds.value.includes(sampleItemFilterId.value))
const mzCalibrationTableRows = computed(() => calibrationStore.mzFitStats ?? [])
const sampleFilename = computed(() =>
  sampleStore.active ? sampleStore.active.filename : instrumentStore.acquisitionActiveFilename
)
const sampleItemAttributes = computed(() =>
  formFields.value
    .filter((field) => field.label != 'sample_item_name')
    .reduce(
      (acc, cur) => ({
        ...acc,
        [strToSnakeCase(cur.label)]: cur.value || ''
      }),
      {}
    )
)
const sampleIsSaved = computed(() =>
  sampleStore.active
    ? sampleItemName.value === sampleStore.active.sample_item_name &&
      sampleItemType.value === sampleStore.active.sample_item_type &&
      sampleItemFilterId.value === sampleStore.active.filter_id &&
      _.isEqual(sampleItemAttributes.value, sampleStore.active.sample_item_attributes)
    : false
)
const sampleItemName = computed(
  () => formFields.value?.filter((field) => field.label == 'sample_item_name')[0]?.value
)
const sampleMatchClass = computed(() => {
  if (sampleStore.active?.match_category === null) return 'is-success'
  if (sampleStore.active?.match_category === 2) {
    return 'is-danger'
  } else if (sampleStore.active?.match_category === 1) {
    return 'is-warning'
  } else {
    return 'is-success'
  }
})
const savedTemplates = computed(() => {
  return appStore.attributeTemplates.filter((template) => template.type == templateType.value)
})
const sampleMzCalibrated = computed(() => sampleStore.active?.mz_calibration.verified)

function close() {
  if (sampleStore.active && sampleIsSaved.value) {
    reset()
  } else {
    dialog.confirm({
      title: 'Close sample without saving?',
      message: `There is unsaved information in the form.
            Are you sure you want to close the sample without saving?`,
      confirmText: 'Close',
      onConfirm: () => {
        reset()
      }
    })
  }
}
function convertLabelToTitle(label) {
  return beautifySnakeCase(label)
}
function addField() {
  dialog.prompt({
    message: 'Add field to template',
    confirmText: 'Add',
    inputAttrs: {
      placeholder: 'field label',
      maxlength: 100
    },
    trapFocus: true,
    onConfirm: (fieldToAdd) => {
      loadedTemplate.value = {
        name: null,
        template: [...formFields.value, { label: fieldToAdd, value: '' }]
      }
    }
  })
}
function deleteTemplate() {
  dialog.confirm({
    title: 'Deleting template',
    message: 'Are you sure you want to delete template <b>' + loadedTemplate.value.name + '</b>?',
    confirmText: 'Delete',
    onConfirm: () => {
      const templateToDelete = availableTemplates.value.find(
        (template) => template.attribute_template_id == loadedTemplate.value.attribute_template_id
      )
      sampleStore.deleteAttributeTemplate(templateToDelete)
    }
  })
}
function removeField(event) {
  // Field to remove label is in button element id, find it from the event data
  let fieldToRemove = event.target.id
  if (!fieldToRemove.length) {
    // Failed to find the button id
    console.log('fieldToRemove not found at event.target.id: ', event)
    return
  }
  for (let i = 0; i < loadedTemplate.value.template.length; ++i) {
    if (_.isEqual(fieldToRemove, loadedTemplate.value.template[i].label)) {
      loadedTemplate.value = {
        name: null,
        template: [
          ...loadedTemplate.value.template.slice(0, i),
          ...loadedTemplate.value.template.slice(i + 1)
        ]
      }
      break
    }
  }
}
function saveTemplate() {
  dialog.prompt({
    title: 'Template name',
    confirmText: 'Save',
    inputAttrs: {
      placeholder: 'template name',
      maxlength: 100
    },
    trapFocus: true,
    onConfirm: (templateName) => {
      if (templateName.toLowerCase() === 'default') {
        toast.open({
          message: `Name "${templateName}" is not allowed`,
          duration: 5000,
          type: 'is-danger'
        })
        return
      }
      let templateFormFields = structuredClone(formFields)
      // Empty values
      templateFormFields.forEach((field) => (field.value = ''))
      let newTemplate = {
        name: templateName,
        type: templateType.value,
        template: templateFormFields.value
      }
      let i = 0
      // set loaded template
      for (i = 0; i < availableTemplates.value.length; ++i) {
        if (templateName == availableTemplates.value[i].name) break
      }
      if (i < availableTemplates.value.length) {
        // existing template
        availableTemplates.value[i] = structuredClone(newTemplate)
      } else {
        // new template
        availableTemplates.value.push(structuredClone(newTemplate))
      }
      loadedTemplate.value = structuredClone(newTemplate)
      // push new template
      sampleStore.createAttributeTemplate(loadedTemplate.value)
      showEditFunctions.value = false
    }
  })
}
function generateFilterId() {
  sampleItemFilterId.value = genId(6, false)
}
async function mzCalibrationFit() {
  calibrationStore.unload()
  const requestData = {
    sampleId: sampleStore.active.sample_item_id,
    sampleName: sampleStore.active.sample_item_name,
    body: calibrationStore.params
  }
  await calibrationStore.calibrationMzFit(requestData)
}
async function mzCalibrationApply() {
  const requestData = {
    fit: calibrationStore.mzFit,
    sample_filename: sampleFilename.value
  }
  await calibrationStore.calibrationMzApply(requestData)
}
function reset() {
  instrumentStore.resetAcquisitionStatus()
  resetSampleItem()
  activeStep.value = 0
}
function resetSampleItem() {
  sampleStore.unload()
  sampleItemFilterId.value = null
  sampleItemType.value = null
  // Reset sample item name
  formFields.value.filter((field) => field.label == 'sample_item_name')[0].value = null
}
async function sampleMatch() {
  await sampleStore.matchSampleCompute(sampleStore.active)
}
function saveSampleInfoButtonPressed() {
  let sample = {
    filename: sampleFilename.value,
    sample_item_name: sampleItemName.value,
    sample_item_type: sampleItemType.value,
    sample_batch_id: batchStore.active.sample_batch_id,
    sample_item_attributes: sampleItemAttributes.value,
    filter_id: sampleItemFilterId.value
  }
  if (instrumentStore.conversionProgress < 100) {
    instrumentStore.sampleItemPending = sample
    return
  } else {
    saveSampleInformation(sample)
  }
}
async function saveSampleInformation(sample) {
  if (!sampleStore.active) {
    // Create
    await sampleStore.create(sample)
  } else {
    // Update
    sample = {
      ...sample,
      sample_item_id: sampleStore.active.sample_item_id,
      sample_item_attributes: sampleStore.active.sample_item_attributes,
      sample_item_utc_created: sampleStore.active.sample_item_utc_created
    }
    await sampleStore.update(sample)
  }
}
function selectBatch(val) {
  batchStore.load(val.sample_batch_id)
}

watch(
  computed(() => instrumentStore.acquisitionProgress),
  (newValue) => {
    if (newValue == 0) {
      resetSampleItem()

      activeStep.value = 0
    }
  }
)
watch(calibrationProgress, (newValue, oldValue) => {
  if (oldValue != 100 && newValue == 100) {
    if (calibrationStore.calibrationStatus.failed) {
      activeStep.value = 1
    }
  }
})
watch(
  loadedTemplate,
  (newValue) => {
    if (newValue) {
      // Make a copy to avoid mutating the loaded template directly
      let newFormFields = cloneDeep(newValue.template)
      // Fill in new form with values from the old
      newFormFields.forEach(
        (field) =>
          (field.value = formFields.value.find(
            (old_field) => old_field.label === field.label
          )?.value)
      )
      formFields.value = newFormFields
    }
  },
  { deep: true }
)
watch(
  computed(() => sampleStore.active?.match_category),
  (newValue) => {
    if (newValue > 0) {
      // Switch to target search page if sample alarms
      activeStep.value = 2
    }
  }
)
watch(sampleItemFilterId, () => {
  // Reset sample item type when filter ID is changed
  // In order to not allow inconsistency between filter ID and sample type
  sampleItemType.value = null
})
</script>

<template>
  <section>
    <the-layout-sidebar-view>
      <div style="margin: 0 auto; width: 50vw">
        <!-- Progress bars -->
        <section>
          <b-field label="Acquisition">
            <b-progress
              :value="instrumentStore.acquisitionProgress"
              :type="instrumentStore.acquisitionProgress == 100 ? 'is-success' : 'is-primary'"
            >
            </b-progress>
          </b-field>
          <b-field label="Conversion">
            <b-progress
              :value="instrumentStore.conversionProgress"
              :type="instrumentStore.conversionProgress == 100 ? 'is-success' : 'is-primary'"
            >
            </b-progress>
          </b-field>
          <b-field label="Calibration">
            <b-progress
              :value="calibrationProgress"
              :type="
                calibrationProgress == 100
                  ? calibrationStore.calibrationStatus.failed
                    ? 'is-danger'
                    : 'is-success'
                  : 'is-primary'
              "
            >
            </b-progress>
          </b-field>
          <b-field label="Target search">
            <b-progress :value="instrumentStore.matchingProgress" :type="sampleMatchClass">
            </b-progress>
          </b-field>
        </section>
        <br />
        <!-- Steps -->
        <b-tabs v-model="activeStep" :has-navigation="false">
          <!-- Sample information step -->
          <b-tab-item label="Sample information" :clickable="true">
            <div style="padding-bottom: 0.75em">
              <div class="columns">
                <div class="column is-11">
                  <h1 class="title has-text-centered">Sample information</h1>
                </div>
                <div class="column is-1">
                  <div style="text-align: right" v-if="editable">
                    <b-button
                      icon-right="cog"
                      type="is-primary"
                      size="is-small"
                      @click="showEditFunctions = !showEditFunctions"
                    >
                    </b-button>
                  </div>
                </div>
              </div>
            </div>
            <div v-for="item in formFields" :key="item.label">
              <b-field :label="convertLabelToTitle(item.label)">
                <b-input
                  v-model="item.value"
                  :placeholder="showEditFunctions ? item.placeholder || 'default value' : ''"
                  :required="fillable && item.required"
                  :disabled="!fillable || item.disabled"
                  expanded
                >
                </b-input>
                <div v-if="showEditFunctions">
                  <b-button
                    :id="item.label"
                    :disabled="item.required"
                    @click="removeField"
                    type="is-danger"
                    icon-right="delete"
                    hover
                    title="Delete Field"
                  >
                  </b-button>
                </div>
              </b-field>
            </div>
            <b-field label="Filter ID">
              <b-input v-model="sampleItemFilterId" disabled expanded> </b-input>
              <b-dropdown
                aria-role="list"
                v-model="sampleItemFilterId"
                :disabled="!fillable"
                expanded
              >
                <template #trigger>
                  <b-button
                    :label="sampleItemFilterId"
                    icon-right="menu-down"
                    style="align: left"
                  />
                </template>
                <template v-for="filterId of batchFilterIds" :key="filterId">
                  <b-dropdown-item aria-role="listitem" :value="filterId">
                    {{ filterId }}
                  </b-dropdown-item>
                </template>
              </b-dropdown>
              <b-button
                type="is-primary"
                icon-left="plus"
                :disabled="!fillable"
                @click="generateFilterId()"
              >
              </b-button>
            </b-field>
            <b-field label="Sample type">
              <b-dropdown aria-role="list" v-model="sampleItemType" :disabled="!fillable" expanded>
                <template #trigger>
                  <b-button
                    :label="sampleItemType"
                    icon-right="menu-down"
                    expanded
                    style="align: left"
                  />
                </template>
                <b-dropdown-item
                  aria-role="listitem"
                  value="INSTRUMENT_BACKGROUND"
                  v-if="!sampleItemFilterId"
                >
                  Instrument background
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="FILTER_REGENERATION"
                  v-if="sampleItemFilterId && filterIsNew"
                >
                  Filter regeneration
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="FILTER_BACKGROUND"
                  v-if="sampleItemFilterId"
                >
                  Filter background
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="SAMPLE"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Sample
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="BLANK"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Blank
                </b-dropdown-item>
                <b-dropdown-item
                  aria-role="listitem"
                  value="UNKNOWN"
                  v-if="sampleItemFilterId && !filterIsNew"
                >
                  Unknown
                </b-dropdown-item>
              </b-dropdown>
            </b-field>
            <b-field label="Filename">
              <b-input
                v-model="instrumentStore.acquisitionActiveFilename"
                required
                :disabled="true"
                expanded
              >
              </b-input>
            </b-field>
            <b-field label="Sample batch">
              <b-tooltip :delay="200" position="is-top" type="is-dark" size="is-small" multilined>
                <b-dropdown aria-role="list" expanded @change="selectBatch" disabled>
                  <template #trigger>
                    <b-button
                      :label="batchStore.active ? batchStore.active.sample_batch_name : ''"
                      icon-right="menu-down"
                      expanded
                    />
                  </template>
                  <template v-for="batch of workspaceStore.batches" :key="batch.sample_batch_id">
                    <b-dropdown-item aria-role="listitem" :value="batch">
                      {{ batch.sample_batch_name }}
                    </b-dropdown-item>
                  </template>
                </b-dropdown>
                <!-- tooltip slot -->
                <template v-slot:content>
                  <table style="text-align: center; width: 100%">
                    <tr>
                      <th>#</th>
                      <th>Sample name</th>
                    </tr>
                    <template
                      v-for="item in batchStore.sampleItems"
                      v-bind:key="item.sample_item_id"
                    >
                      <tr>
                        <td>{{ item.index }}</td>
                        <td>{{ item.sample_item_name }}</td>
                      </tr>
                    </template>
                  </table>
                </template>
              </b-tooltip>
            </b-field>
            <div v-if="showEditFunctions" style="padding-top: 2em">
              <b-field>
                <b-button @click="addField" expanded>
                  <b>Add new field</b>
                </b-button>
              </b-field>
            </div>
            <b-field label="Reuse template">
              <div class="container">
                <div class="row">
                  <div class="columns">
                    <div class="column is-half" style="text-align: center">
                      <b-select
                        v-model="loadedTemplate"
                        placeholder="Load template"
                        expanded
                        :disabled="!editable"
                      >
                        <option v-for="t in availableTemplates" :value="t" :key="t.name">
                          {{ t.name }}
                        </option>
                      </b-select>
                    </div>
                    <div class="column is-narrow" style="text-align: left" v-if="showEditFunctions">
                      <b-button
                        :disabled="
                          !loadedTemplate ||
                          !loadedTemplate.name ||
                          loadedTemplate.name == 'default'
                        "
                        @click="deleteTemplate"
                        type="is-danger"
                        icon-right="delete"
                        hover
                        title="Delete Template"
                      >
                      </b-button>
                    </div>
                    <div class="column is-narrow" style="text-align: left" v-if="showEditFunctions">
                      <b-button
                        @click="saveTemplate"
                        :disabled="!formFields.length"
                        type="is-success"
                        icon-left="content-save"
                        hover
                        title="Save Template"
                      >
                      </b-button>
                    </div>
                  </div>
                </div>
              </div>
            </b-field>
            <div class="container" style="text-align: center; padding: 1em 0em 0em 0em">
              <div class="rows">
                <div class="row">
                  <b-button
                    :disabled="
                      sampleIsSaved ||
                      !sampleItemName ||
                      !sampleItemType ||
                      !instrumentStore.acquisitionActiveFilename
                    "
                    :type="sampleIsSaved ? 'is-success' : 'is-danger'"
                    :loading="instrumentStore.sampleItemPending === null ? false : true"
                    icon-left="content-save"
                    expanded
                    @click="saveSampleInfoButtonPressed"
                  >
                    Save sample info
                  </b-button>
                </div>
                <div class="row" style="padding: 1em">
                  <b-button
                    type="is-primary"
                    icon-left="close"
                    @click="close()"
                    :disabled="
                      sampleStore.active
                        ? calibrationProgress != 100 || instrumentStore.matchingProgress == null
                        : false
                    "
                    v-if="
                      instrumentStore.acquisitionActiveFilename &&
                      instrumentStore.conversionProgress == 100
                    "
                  >
                    Close
                  </b-button>
                </div>
              </div>
            </div>
          </b-tab-item>
          <!-- Calibration step -->
          <b-tab-item label="Calibration" :clickable="sampleStore.active ? true : false">
            <h1 class="title has-text-centered">Calibration</h1>
            <b-collapse :open="false" animation="slide">
              <template #trigger>
                <section style="padding: 0.5em">
                  <b-button
                    icon-left="wrench"
                    size="is-small"
                    @click="
                      (props) => {
                        props.open = !props.open
                      }
                    "
                  >
                  </b-button>
                </section>
              </template>
              <the-pane-settings-calibration></the-pane-settings-calibration>
            </b-collapse>
            <b-message v-if="calibrationStore.mzFitError" type="is-danger" has-icon>
              {{ calibrationStore.mzFitError }}
            </b-message>
            <base-table
              :key="mzCalibrationTableKey"
              :rows="mzCalibrationTableRows"
              :cols="mzCalibrationTableCols"
              :checkable="false"
              :defaultSort="['mz', 'asc']"
              :searchable="false"
              :minPrecision="4"
              :maxPrecision="4"
            >
            </base-table>
            <div style="text-align: right">
              <b-button
                :disabled="!sampleStore.active"
                type="is-primary"
                icon-left=""
                @click="mzCalibrationFit"
              >
                Fit
              </b-button>
              <b-button
                :disabled="!calibrationStore.mzFit"
                type="is-success"
                icon-left="content-save"
                @click="mzCalibrationApply"
              >
                Apply calibration
              </b-button>
            </div>
            <div style="text-align: center">
              <b-button
                type="is-primary"
                icon-left="close"
                @click="close"
                v-if="calibrationStore.mzFitError"
              >
                Close
              </b-button>
            </div>
          </b-tab-item>
          <!-- Target search step -->
          <b-tab-item
            label="Target search"
            :clickable="sampleStore.active ? (sampleMzCalibrated ? true : false) : false"
          >
            <h1 class="title has-text-centered">Target search</h1>
            <div v-if="sampleStore.matched">
              <the-pane-browser-target></the-pane-browser-target>
            </div>
            <div style="text-align: center">
              <b-button
                :disabled="sampleStore.active ? false : true"
                type="is-success"
                icon-left=""
                @click="sampleMatch"
                v-if="!sampleStore.matched"
              >
                Process
              </b-button>
              <b-button
                type="is-primary"
                icon-left="close"
                @click="close()"
                v-if="sampleStore.matched"
              >
                Close
              </b-button>
            </div>
          </b-tab-item>
        </b-tabs>
      </div>
    </the-layout-sidebar-view>
  </section>
</template>
