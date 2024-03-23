<script setup>
import { ref, watch, computed } from 'vue'

import { useNotificationStore } from '@/stores'

const notificationStore = useNotificationStore()

const isClosing = ref(false)

function close() {
  // TODO_configuration  move animation delay to config file
  isClosing.value = true
  setTimeout(() => {
    notificationStore.deactivate()
    notificationStore.resetWarningNotification()
    isClosing.value = false
  }, 500)
}

function autoClose() {
  if (notificationStore.warningNotification === 'emptyWorkspace') {
    setTimeout(close, 5000)
  }
}

watch(
  computed(() => notificationStore.warningActive),
  (newVal) => {
    if (!newVal) {
      notificationStore.resetWarningNotification()
    }
  }
)
watch(
  computed(() => notificationStore.warningNotification),
  () => autoClose(),
  { immediate: true }
)
</script>

<template>
  <div v-if="notificationStore.warningActive">
    <!-- Development Warning -->
    <b-message
      v-if="notificationStore.warningNotification === 'inDevelopment'"
      type="is-notification"
      title="Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing, 'in-development': 'in-development' }"
    >
      NOTE: You are running the development version of Mascope. Any changes are not persisted.
    </b-message>

    <!-- Failed Calibration Samples Warning -->
    <b-message
      v-if="notificationStore.warningNotification === 'failedCalibrationSamples'"
      type="is-notification"
      title="Calibration Error Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing,
        'failed-calibration': 'failed-calibration'
      }"
    >
      <p>There was an error during calibration with the following samples:</p>
      <ul>
        <li v-for="sample in notificationStore.warningData" :key="sample.index">
          <strong>{{ sample.sample_item_name }}</strong
          >, <em>{{ sample.filename }}</em> encountered an error: {{ sample.error }}.
        </li>
      </ul>
      <p>Please check the samples.</p>
    </b-message>

    <!-- Failed to Compute Matches Samples during batch compute Warning -->
    <b-message
      v-if="notificationStore.warningNotification === 'itemComputeFailed'"
      type="is-notification"
      title="Match Computation Error Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing
      }"
    >
      <p>There was an error during match computation.</p>
      <p>{{ notificationStore.warningData }}</p>
    </b-message>

    <!-- Warning with samples failed to compute matches during batch compute -->
    <b-message
      v-if="notificationStore.warningNotification === 'batchComputeFailedSamples'"
      type="is-notification"
      title="Match Computation Error Warning"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing,
        'failed-computation': 'failed-computation'
      }"
    >
      <p>
        There was an error during match computation for the
        {{ notificationStore.warningData.length }} following sample{{
          notificationStore.warningData.length === 1 ? '' : 's'
        }}:
      </p>
      <ul>
        <li
          v-for="sample in notificationStore.warningData"
          :key="sample.sample_item.sample_item_id"
        >
          <strong>{{ sample.sample_item.sample_item_name }}</strong> encountered an error:
          {{ sample.error_message }}.
        </li>
      </ul>
    </b-message>

    <!-- Empty Workspace Warning -->
    <b-message
      v-if="notificationStore.warningNotification === 'emptyWorkspace'"
      type="is-notification"
      title="Workspace Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing, 'empty-workspace': 'empty-workspace' }"
    >
      Selected workspace "{{ notificationStore.warningData }}" has no batches. Please first create a
      new batch in this workspace.
    </b-message>

    <!-- No calibration collection in active batch -->
    <b-message
      v-if="notificationStore.warningNotification === 'noCalibrationCollection'"
      type="is-notification"
      title="No Calibration Collection Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing, 'empty-workspace': 'empty-workspace' }"
    >
      Selected batch "{{ notificationStore.warningData.batchName }}" has no calibration collection.
      The default calibrant collection "{{ notificationStore.warningData.collectionName }}" was
      applied, please save the changes.
    </b-message>

    <!-- Validation Errors Warning -->
    <!-- title="Pasted data formatted incorrectly, please review it:" -->
    <b-message
      v-if="notificationStore.warningNotification === 'validationErrors'"
      type="is-notification"
      title="There seems to be an issue with pasted data:"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing,
        'failed-validation-import-samples': 'failed-validation-import-samples'
      }"
    >
      <ul v-if="notificationStore.warningData.messages.length" style="padding-bottom: 0.5em">
        <li
          v-for="(message, index) in notificationStore.warningData.messages"
          :key="'message-' + index"
        >
          {{ message }}
        </li>
      </ul>
      <p v-if="notificationStore.warningData.sampleFailures.length">
        <strong> Issues with pasted samples: </strong>
      </p>
      <ul v-if="notificationStore.warningData.sampleFailures.length">
        <li
          v-for="(item, index) in notificationStore.warningData.sampleFailures"
          :key="'item-' + index"
        >
          {{ index + 1 }}) {{ item.sampleName }}:
          <ul>
            <li v-for="(failure, i) in item.failures" :key="i" style="padding-left: 1em">
              - {{ failure }}
            </li>
          </ul>
        </li>
      </ul>
      <ul v-if="notificationStore.warningData.columnsFailures.length">
        <li
          v-for="(col, index) in notificationStore.warningData.columnsFailures"
          :key="'col-' + index"
        >
          {{ index + 1 }}) {{ col }}
        </li>
      </ul>
      <p v-if="notificationStore.warningData.info.length" style="padding-top: 0.5em">
        <strong> The guidelines for correction: </strong>
      </p>
      <ul v-if="notificationStore.warningData.info.length">
        <li v-for="(info, index) in notificationStore.warningData.info" :key="'info-' + index">
          {{ index + 1 }}) {{ info }}
        </li>
      </ul>
      <p style="padding-top: 0.5em">
        Please adjust your input data accordingly and paste it again.
      </p>
    </b-message>

    <!-- Other types of warning messages here -->
  </div>
</template>
