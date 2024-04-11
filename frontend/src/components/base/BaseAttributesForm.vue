<script setup>
import * as _ from 'underscore'

import { dialog, toast } from '@/main'

import { ref, reactive, computed, watch } from 'vue'

const props = defineProps({
  initialTemplates: {
    type: Array,
    required: true
  },
  attributesToLoad: {
    type: Object,
    default: () => {}
  },
  showEditFunctions: {
    type: Boolean,
    default: false
  },
  editable: {
    type: Boolean,
    default: false
  },
  fillable: {
    type: Boolean,
    default: true
  },
  formTitle: {
    type: String,
    required: true
  },
  templateType: {
    type: String,
    required: true
  }
})

const emit = defineEmits([
  'metaDataUpdated',
  'loadAttributes',
  'saveAttributes',
  'saveTemplate',
  'deleteTemplate'
])

// reactivity

let loadedTemplate = reactive(null)
loadedTemplate = structuredClone(availableTemplates.value[0])

let formFields = reactive([])

const availableTemplates = computed(() => props.initialTemplates)
const editFunctionsVisible = ref(props.showEditFunctions)

// watchers

watch(formFields, (newValue) => {
  emit('metaDataUpdated', newValue)
})
watch(loadedTemplate, (newValue) => {
  if (newValue) {
    formFields = structuredClone(newValue.template)
  }
})
watch(props.attributesToLoad, (data) => {
  if (_.isEmpty(data) || _.isEmpty(data.row)) {
    return
  }
  let newTemplate = {
    name: null,
    type: props.templateType,
    template: []
  }
  for (let { label, key, required, disabled } of data.template) {
    if (required) {
      newTemplate.template.push({
        label,
        key,
        required,
        disabled,
        value: data.row[label]
      })
    }
  }
  const attributesField = props.templateType + '_attributes'
  if (data.row[attributesField]) {
    Object.keys(data.row[attributesField]).forEach((attr) =>
      newTemplate.template.push({
        label: attr,
        value: data.row[attributesField][attr]
      })
    )
  }
  loadedTemplate = newTemplate
})
watch(props.showEditFunctions, (newValue) => {
  editFunctionsVisible.value = newValue
})

// methods

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
      loadedTemplate = {
        name: null,
        template: [...formFields, { label: fieldToAdd, value: '' }]
      }
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
  for (let i = 0; i < loadedTemplate.template.length; ++i) {
    if (_.isEqual(fieldToRemove, loadedTemplate.template[i].label)) {
      loadedTemplate = {
        name: null,
        template: [...loadedTemplate.template.slice(0, i), ...loadedTemplate.template.slice(i + 1)]
      }
      break
    }
  }
}
function deleteTemplate() {
  dialog.confirm({
    title: 'Deleting template',
    message: 'Are you sure you want to delete template <b>' + loadedTemplate.name + '</b>?',
    confirmText: 'Delete',
    onConfirm: () => {
      emit(
        'deleteTemplate',
        availableTemplates.value
          .filter(
            (template) => template.attribute_template_id == loadedTemplate.attribute_template_id
          )
          .map((template) => template.attribute_template_id)
      )
    }
  })
}
function saveTemplate() {
  dialog.prompt({
    title: 'Template name',
    confirmText: 'Save',
    inputAttrs: {
      placeholder: loadedTemplate.name === 'default' ? 'template name' : loadedTemplate.name,
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
      // copy loadedTempate fields with user input
      let newTemplate = {
        name: templateName,
        type: props.templateType,
        template: structuredClone(formFields)
      }
      let i = 0
      // set loaded template
      for (i = 0; i < availableTemplates.value.length; ++i) {
        if (_.isEqual(templateName, availableTemplates.value[i].name)) break
      }
      if (i < availableTemplates.value.length) {
        // existing template
        availableTemplates.value[i] = structuredClone(newTemplate)
      } else {
        // new template
        availableTemplates.value.push(structuredClone(newTemplate))
      }
      loadedTemplate = structuredClone(newTemplate)
      // push new template
      emit('saveTemplate', loadedTemplate)
    }
  })
}
function saveAttributes() {
  dialog.confirm({
    title: props.formTitle,
    message: `${props.formTitle} for <b>` + formFields[0].value + '</b>?',
    confirmText: 'Save',
    onConfirm: () => {
      emit('saveAttributes', formFields)
    }
  })
}
function loadAttributes(requestObject) {
  emit('loadAttributes', requestObject)
}
</script>

<template>
  <div>
    <div class="box" style="background-color: inherit">
      <div style="text-align: right" v-if="editable">
        <b-button
          icon-right="settings"
          type="is-primary"
          size="is-small"
          @click="editFunctionsVisible = !editFunctionsVisible"
        >
        </b-button>
      </div>
      <div style="padding-bottom: 1.5em">
        <h1 style="font-size: 16px; text-align: center">
          <p>
            <b>{{ formTitle }}</b>
          </p>
        </h1>
      </div>
      <div v-for="item in formFields" :key="item.label">
        <template>
          <b-field :label="item.label" custom-class="dark">
            <b-input
              v-model="item.value"
              :placeholder="editFunctionsVisible ? item.placeholder || 'default value' : ''"
              :required="fillable && item.required"
              :disabled="!fillable || item.disabled"
              lazy
              expanded
            >
            </b-input>
            <div v-if="item.key">
              <b-button
                :id="item.label"
                :disabled="!item.value || item.value.length == 0"
                @click="loadAttributes({ [item.label]: item.value })"
                type="is-warning"
                icon-right="database"
                hover
                title="Load attributes"
              >
              </b-button>
            </div>
            <div v-if="editFunctionsVisible">
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
      <div v-if="editFunctionsVisible" style="padding-top: 2em">
        <b-field custom-class="dark">
          <b-button @click="addField" expanded>
            <b>Add new field</b>
          </b-button>
        </b-field>
      </div>
      <div><br /></div>
      <b-field label="Reuse template" custom-class="dark">
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
              <div class="column is-narrow" style="text-align: left" v-if="editFunctionsVisible">
                <b-button
                  :disabled="
                    !loadedTemplate || !loadedTemplate.name || loadedTemplate.name == 'default'
                  "
                  @click="deleteTemplate"
                  type="is-danger"
                  icon-right="delete"
                  hover
                  title="Delete Template"
                >
                </b-button>
              </div>
              <div class="column is-narrow" style="text-align: left" v-if="editFunctionsVisible">
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
                    formFields.filter((f) => f.required).length !=
                    formFields.filter((f) => f.required).filter((f) => f.value).length
                  "
                  type="is-success"
                  icon-left="content-save"
                  @click="saveAttributes"
                >
                  {{ formTitle }}
                </b-button>
              </div>
            </div>
          </div>
          <div class="row">
            <br />
          </div>
        </div>
      </b-field>
    </div>
  </div>
</template>
