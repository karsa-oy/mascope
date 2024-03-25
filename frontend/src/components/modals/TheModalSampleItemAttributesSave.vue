<script setup>
import { ref, computed, watch, toRaw } from 'vue'

import { DialogProgrammatic as dialog, ToastProgrammatic as toast } from '@ntohq/buefy-next'

import BaseTable from '@/components/base/BaseTable.vue'
import ThePaneBrowserTarget from '@/components/panes/ThePaneBrowserTarget.vue'
import ThePaneSettingsCalibration from '@/components/panes/ThePaneSettingsCalibration.vue'

import { beautifySnakeCase, strToSnakeCase, genId } from '@/lib/util'

import {
  useAppStore,
  useBatchStore,
  useModalStore,
  useCalibrationStore,
  useSampleStore
} from '@/stores'

const appStore = useAppStore()
const batchStore = useBatchStore()
const sampleStore = useSampleStore()
const modalStore = useModalStore()
const calibrationStore = useCalibrationStore()

const action = ref(null)
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
const sampleFilename = ref(null)
const sampleItemFilterId = ref(null)
const sampleInstrument = ref(null)
const sampleItemType = ref(null)
const showEditFunctions = ref(false)
const templateType = ref('sample_item')

formFields.value = structuredClone(toRaw(defaultTemplate.value.template))

const availableTemplates = computed(() => [defaultTemplate.value, ...savedTemplates.value])
const batchFilterIds = computed(() =>
  batchStore.batchActive
    ? [null, ...new Set(batchStore.sampleItems.map((item) => item.filter_id))]
    : []
)
const editable = computed(() => ['create', 'update'].includes(action.value))
const fillable = computed(() => ['create', 'update'].includes(action.value))
const instrumentIsTof = computed(() =>
  sampleInstrument.value ? sampleInstrument.value.indexOf('ORBI') == -1 : false
)
const mzCalibrationTableRows = computed(() => calibrationStore.mzFitStats ?? [])
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
const sampleItemName = computed(
  () => formFields.value.filter((field) => field.label == 'sample_item_name')[0].value
)
const savedTemplates = computed(() =>
  appStore.attributeTemplates.value.filter((template) => template.type == templateType.value)
)
const sampleMzCalibrated = computed(() => sampleStore.active.mz_calibration.verified)

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
        template: [...formFields, { label: fieldToAdd, value: '' }]
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
function removeField(event) {
  // Field to remove label is in button element id, find it from the event data
  let targetElement = event.target
  // Check if the clicked element is not the button itself, then find the closest parent button
  if (targetElement.nodeName !== 'BUTTON') {
    targetElement = targetElement.closest('button')
  }
  let fieldToRemove = targetElement?.id ?? null
  if (!fieldToRemove) {
    // Failed to find the button id
    console.log('fieldToRemove not found at event.target.id: ', event)
    return
  }
  for (let i = 0; i < loadedTemplate.value.template.length; ++i) {
    if (fieldToRemove == loadedTemplate.value.template[i].label) {
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
async function sampleMatch() {
  await sampleStore.matchSampleRematch(sampleStore.active)
}
async function saveSampleItem() {
  await saveAttributes()
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
      let templateFormFields = structuredClone(formFields.value)
      // Empty values
      templateFormFields.forEach((field) => (field.value = ''))
      let newTemplate = {
        name: templateName,
        type: templateType.value,
        template: templateFormFields
      }
      loadedTemplate.value = structuredClone(newTemplate)
      // push new template
      sampleStore.createAttributeTemplate(loadedTemplate.value)
    }
  })
}
async function saveAttributes() {
  if (action.value == 'create') {
    let newSampleItem = {
      filename: sampleFilename.value,
      sample_item_name: sampleItemName.value,
      sample_item_type: sampleItemType.value,
      sample_batch_id: batchStore.batchActive.sample_batch_id,
      sample_item_attributes: sampleItemAttributes.value,
      filter_id: sampleItemFilterId.value
    }
    await sampleStore.create(newSampleItem)
  } else if (action.value == 'update') {
    let newSampleItem = {
      ...sampleStore.active, // To include sample_item_id
      sample_item_name: sampleItemName.value,
      sample_item_type: sampleItemType.value,
      sample_batch_id: batchStore.batchActive.sample_batch_id,
      sample_item_attributes: sampleItemAttributes.value,
      filter_id: sampleItemFilterId.value
    }
    await sampleStore.update(newSampleItem)

    modalStore.deactivate()
  }
}

watch(activeStep, () => {
  switch (activeStep.value) {
    case 0:
      break
    case 1:
      break
    case 2:
      break
  }
})
watch(sampleItemFilterId, (newValue) => {
  if (newValue != sampleStore.active.filter_id) {
    // Reset sample item type when filter ID was changed
    sampleItemType.value = null
  }
})
watch(
  loadedTemplate,
  (newValue) => {
    if (newValue) {
      // Make a copy to avoid mutating the loaded template directly
      let newFormFields = structuredClone(newValue.template)
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
  computed(() => modalStore.state.sampleItemAttributesSaveActive),
  (newValue) => {
    if (newValue) {
      activeStep.value = 0
    } else {
      // Reset template selection when closing modal
      loadedTemplate.value = null
    }
  }
)
watch(
  computed(() => modalStore.state.sampleItemAttributesSaveProps),
  (data) => {
    action.value = data.action
    let newTemplate = {
      name: null,
      type: templateType.value,
      template: []
    }
    for (let { label, key, required, disabled } of defaultTemplate.value.template) {
      if (required) {
        newTemplate.template.push({
          label,
          key,
          required,
          disabled,
          value: data.sampleItemRecordToLoad[label]
        })
      }
    }
    const attributesField = templateType.value + '_attributes'
    if (data.sampleItemRecordToLoad[attributesField]) {
      const attributes = data.sampleItemRecordToLoad[attributesField]
      if (attributes && typeof attributes === 'object' && Object.keys(attributes).length > 0) {
        Object.keys(attributes).forEach((attr) => {
          newTemplate.template.push({
            label: attr,
            value: attributes[attr]
          })
        })
      }
    }
    loadedTemplate.value = newTemplate
    formFields.value = newTemplate.template
    sampleFilename.value = data.sampleItemRecordToLoad.filename
    sampleInstrument.value = data.sampleItemRecordToLoad.instrument
    sampleItemFilterId.value = data.sampleItemRecordToLoad.filter_id
    sampleItemType.value = data.sampleItemRecordToLoad.sample_item_type
  }
)
</script>

<template>
  <section>
    <b-modal
      v-model="modalStore.state.sampleItemAttributesSaveActive"
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @close="modalStore.deactivate"
    >
      <div class="box" style="background-color: inherit">
        <b-steps v-model="activeStep" :has-navigation="false">
          <b-step-item
            label="Sample information"
            :clickable="true"
            :type="{ 'is-success': sampleStore.active ? true : false }"
          >
            <div style="text-align: right" v-if="editable">
              <b-button
                icon-right="cog"
                type="is-primary"
                size="is-small"
                @click="showEditFunctions = !showEditFunctions"
              >
              </b-button>
            </div>
            <div style="padding-bottom: 1.5em">
              <h1 class="title has-text-centered">Sample information</h1>
            </div>
            <div v-for="item in formFields" :key="item.label">
              <template>
                <b-field :label="convertLabelToTitle(item.label)">
                  <b-input
                    v-model="item.value"
                    :placeholder="showEditFunctions ? item.placeholder || 'default value' : ''"
                    :required="fillable && item.required"
                    :disabled="!fillable || item.disabled"
                    lazy
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
              </template>
            </div>
            <div>
              <b-field label="Filter ID">
                <b-input v-model="sampleItemFilterId" disabled expanded> </b-input>
                <b-dropdown aria-role="list" v-model="sampleItemFilterId" expanded>
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
                <b-button type="is-primary" icon-left="plus" @click="generateFilterId()">
                </b-button>
              </b-field>
              <b-field label="Sample type">
                <b-dropdown aria-role="list" v-model="sampleItemType" expanded>
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
                    >Instrument background</b-dropdown-item
                  >
                  <b-dropdown-item
                    aria-role="listitem"
                    value="FILTER_REGENERATION"
                    v-if="sampleItemFilterId"
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
                  <b-dropdown-item aria-role="listitem" value="SAMPLE" v-if="sampleItemFilterId"
                    >Sample</b-dropdown-item
                  >
                  <b-dropdown-item aria-role="listitem" value="BLANK" v-if="sampleItemFilterId"
                    >Blank</b-dropdown-item
                  >
                  <b-dropdown-item aria-role="listitem" value="UNKNOWN" v-if="sampleItemFilterId"
                    >Unknown</b-dropdown-item
                  >
                </b-dropdown>
              </b-field>
              <b-field label="Filename">
                <b-input v-model="sampleFilename" required :disabled="true" expanded> </b-input>
              </b-field>
            </div>
            <div v-if="showEditFunctions" style="padding-top: 2em">
              <b-field>
                <b-button @click="addField" expanded>
                  <b>Add new field</b>
                </b-button>
              </b-field>
            </div>
            <div><br /></div>
            <b-field label="Reuse template">
              <div class="container">
                <div class="row">
                  <div class="columns">
                    <div class="column is-half" style="text-align: center">
                      <b-select v-model="loadedTemplate" placeholder="Load template" expanded>
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
                    <div class="column is-one-half" style="text-align: right">
                      <b-button
                        :disabled="
                          !sampleItemType ||
                          formFields.filter((f) => f.required).length !=
                            formFields.filter((f) => f.required).filter((f) => f.value).length ||
                          (action == 'create' && sampleActive)
                        "
                        type="is-success"
                        icon-left="content-save"
                        @click="saveSampleItem"
                      >
                        Save sample info
                      </b-button>
                    </div>
                  </div>
                </div>
              </div>
            </b-field>
          </b-step-item>

          <b-step-item
            label="Calibration"
            :visible="instrumentIsTof"
            :clickable="sampleStore.active ? true : false"
            :type="{ 'is-success': sampleMzCalibrated }"
          >
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
            <b-message v-if="mzFitError" type="is-danger" has-icon>
              {{ mzFitError }}
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
                :disabled="sampleStore.active ? false : true"
                type="is-primary"
                icon-left=""
                @click="mzCalibrationFit"
              >
                Fit
              </b-button>
              <b-button
                :disabled="calibrationStore.mzFit ? false : true"
                type="is-success"
                icon-left="content-save"
                @click="mzCalibrationApply"
              >
                Apply calibration
              </b-button>
            </div>
          </b-step-item>

          <b-step-item
            label="Target search"
            :clickable="
              sampleStore.active ? (!instrumentIsTof || sampleMzCalibrated ? true : false) : false
            "
            :type="{ 'is-success': sampleMatched }"
          >
            <h1 class="title has-text-centered">Target search</h1>
            <div v-if="sampleMatched">
              <the-pane-browser-target></the-pane-browser-target>
            </div>
            <div style="text-align: center">
              <b-button
                :disabled="sampleStore.active ? false : true"
                type="is-success"
                icon-left=""
                @click="sampleMatch"
                v-if="!sampleMatched"
              >
                Process
              </b-button>
              <b-button
                type="is-primary"
                icon-left="close"
                @click="modalStore.deactivate"
                v-if="sampleMatched"
              >
                Close
              </b-button>
            </div>
          </b-step-item>
        </b-steps>
      </div>
    </b-modal>
  </section>
</template>
