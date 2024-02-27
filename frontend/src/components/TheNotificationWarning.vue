<template>
  <div v-if="notificationIsActive">
    <!-- Development Warning -->
    <b-message
      v-if="warningNotification === 'inDevelopment'"
      type="is-notification"
      title="Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing, 'in-development': 'in-development' }"
    >
      NOTE: You are running the development version of Mascope. Any changes are
      not persisted.
    </b-message>

    <!-- Failed Calibration Samples Warning -->
    <b-message
      v-if="warningNotification === 'failedCalibrationSamples'"
      type="is-notification"
      title="Calibration Error Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing,
        'failed-calibration': 'failed-calibration',
      }"
    >
      <p>There was an error during calibration with the following samples:</p>
      <ul>
        <li v-for="sample in warningData" :key="sample.index">
          <strong>{{ sample.sample_item_name }}</strong
          >, <em>{{ sample.filename }}</em> encountered an error:
          {{ sample.error }}.
        </li>
      </ul>
      <p>Please check the samples.</p>
    </b-message>

    <!-- Failed to Compute Matches Samples during batch compute Warning -->
    <b-message
      v-if="warningNotification === 'itemComputeFailed'"
      type="is-notification"
      title="Match Computation Error Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing,
      }"
    >
      <p>There was an error during match computation.</p>
      <p>{{ warningData }}</p>
    </b-message>

    <!-- Warning with samples failed to compute matches during batch compute -->
    <b-message
      v-if="warningNotification === 'batchComputeFailedSamples'"
      type="is-notification"
      title="Match Computation Error Warning"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing,
        'failed-computation': 'failed-computation',
      }"
    >
      <p>
        There was an error during match computation for the
        {{ warningData.length }} following sample{{
          warningData.length === 1 ? "" : "s"
        }}:
      </p>
      <ul>
        <li
          v-for="sample in warningData"
          :key="sample.sample_item.sample_item_id"
        >
          <strong>{{ sample.sample_item.sample_item_name }}</strong> encountered
          an error: {{ sample.error_message }}.
        </li>
      </ul>
    </b-message>

    <!-- Empty Workspace Warning -->
    <b-message
      v-if="warningNotification === 'emptyWorkspace'"
      type="is-notification"
      title="Workspace Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing, 'empty-workspace': 'empty-workspace' }"
    >
      Selected workspace "{{ warningData }}" has no batches. Please first create
      a new batch in this workspace.
    </b-message>

    <!-- No calibration collection in active batch -->
    <b-message
      v-if="warningNotification === 'noCalibrationCollection'"
      type="is-notification"
      title="No Calibration Collection Warning"
      has-icon
      icon="alert"
      icon-size="is-medium"
      :closable="true"
      @close="close"
      :class="{ 'is-closing': isClosing, 'empty-workspace': 'empty-workspace' }"
    >
      Selected batch "{{ warningData.batchName }}" has no calibration
      collection. The default calibrant collection "{{
        warningData.collectionName
      }}" was applied, please save the changes.
    </b-message>

    <!-- Validation Errors Warning -->
    <!-- title="Pasted data formatted incorrectly, please review it:" -->
    <b-message
      v-if="warningNotification === 'validationErrors'"
      type="is-notification"
      title="There seems to be an issue with pasted data:"
      :closable="true"
      @close="close"
      :class="{
        'is-closing': isClosing,
        'failed-validation-import-samples': 'failed-validation-import-samples',
      }"
    >
      <ul v-if="warningData.messages.length" style="padding-bottom: 0.5em">
        <li
          v-for="(message, index) in warningData.messages"
          :key="'message-' + index"
        >
          {{ message }}
        </li>
      </ul>
      <p v-if="warningData.sampleFailures.length">
        <strong> Issues with pasted samples: </strong>
      </p>
      <ul v-if="warningData.sampleFailures.length">
        <li
          v-for="(item, index) in warningData.sampleFailures"
          :key="'item-' + index"
        >
          {{ index + 1 }}) {{ item.sampleName }}:
          <ul>
            <li
              v-for="(failure, i) in item.failures"
              :key="i"
              style="padding-left: 1em"
            >
              - {{ failure }}
            </li>
          </ul>
        </li>
      </ul>
      <ul v-if="warningData.columnsFailures.length">
        <li
          v-for="(col, index) in warningData.columnsFailures"
          :key="'col-' + index"
        >
          {{ index + 1 }}) {{ col }}
        </li>
      </ul>
      <p v-if="warningData.info.length" style="padding-top: 0.5em">
        <strong> The guidelines for correction: </strong>
      </p>
      <ul v-if="warningData.info.length">
        <li v-for="(info, index) in warningData.info" :key="'info-' + index">
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

<script>
import { mapMutations } from "vuex";
import { sync } from "vuex-pathify";

export default {
  name: "TheNotificationWarning",
  data() {
    return {
      isClosing: false,
    };
  },
  computed: {
    ...sync({
      notificationIsActive: "notification/warningActive",
      warningNotification: "notification/warningNotification",
      warningData: "notification/warningData",
    }),
  },
  watch: {
    notificationIsActive(newVal) {
      if (!newVal) {
        this.resetWarningNotification();
      }
    },
    warningNotification: {
      handler() {
        this.autoClose();
      },
      immediate: true,
    },
  },
  methods: {
    ...mapMutations({
      deactivateNotification: "notification/deactivate",
      resetWarningNotification: "notification/RESET_WARNING_NOTIFICATION",
    }),
    close() {
      // TODO_configuration  move animation delay to config file
      this.isClosing = true;
      setTimeout(() => {
        this.deactivateNotification();
        this.resetWarningNotification();
        this.isClosing = false;
      }, 500);
    },
    autoClose() {
      if (this.warningNotification === "emptyWorkspace") {
        setTimeout(this.close, 5000);
      }
    },
  },
};
</script>
