import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { useAppStore } from './app'

export const useNotificationStore = defineStore('notification', () => {
  const appStore = useAppStore()

  const active = ref(null)

  const warningActive = computed(() => active.value == 'warning')
  const generalActive = computed(() => active.value == 'general')
  const progressActive = computed(() => active.value == 'progress')
  const batchComputeProgressActive = computed(() => active.value == 'batchComputeProgress')
  const itemComputeProgressActive = computed(() => active.value == 'itemComputeProgress')
  const calibrationProgressActive = computed(() => active.value == 'calibrationProgress')

  // warning notifications

  const warningNotification = ref(null)
  const warningData = ref(null)

  const generalNotification = ref(null)
  const generalNotificationMessage = ref(null)

  const progressAction = ref(null)
  const progressActionType = ref(null)
  const progressMessage = ref('')
  const progressDataMessage = ref('')
  const progressPercentage = ref(0)
  const progressError = ref(false)

  const copyProgress = ref(false)
  const exportProgress = ref(false)
  const importProgress = ref(false)
  const deleteProgress = ref(false)
  const rematchBatchesProgress = ref(false)
  const rematchBatchProgress = ref(false)

  const progress = (action) => {
    switch (action) {
      case 'copy':
        return copyProgress
      case 'export':
        return exportProgress
      case 'import':
        return importProgress
      case 'delete':
        return deleteProgress
      case 'rematchBatches':
        return rematchBatchesProgress
      case 'rematchBatch':
        return rematchBatchProgress
    }
  }

  const itemMatchComputing = ref(false)
  const totalBatches = ref(null)

  const currentBatch = ref(null)
  const currentBatchMessage = ref('')

  const calibrationComputing = ref(false)
  const calibrationAction = ref(null)

  // Errors

  const computeError = ref(false)
  const calibrationError = ref(false)

  function resetWarningNotification() {
    warningNotification.value = null
    warningData.value = null
  }
  function resetGeneralNotification() {
    generalNotification.value = null
    generalNotificationMessage.value = null
  }
  function resetCalibrationNotification() {
    progressMessage.value = ''
    progressPercentage.value = 0
    calibrationError.value = false
    calibrationAction.value = null
  }
  function resetProgressNotification() {
    progressAction.value = null
    progressActionType.value = null
    progressMessage.value = ''
    progressDataMessage.value = ''
    progressPercentage.value = 0
    progressError.value = false
  }
  // warning notification
  function showWarningNotification({ notification, data }) {
    warningNotification.value = notification
    warningData.value = data ?? null
    active.value = 'warning'
  }
  // general notification
  function showGeneralNotification({ notification, message }) {
    generalNotification.value = notification
    generalNotificationMessage.value = message
    active.value = 'general'
  }
  function closeGeneralNotification() {
    active.value = null
  }
  // progress notification
  function showProgressNotification({ action, message, type, percentage }) {
    const state = progress(action)
    state.value = true
    progressAction.value = action
    progressActionType.value = type ?? null
    progressMessage.value = message
    progressPercentage.value = percentage ?? 0
  }
  async function onRematchBatchesStarted({ total_batches }) {
    rematchBatchesProgress.value = true
    totalBatches.value = total_batches
    progressMessage.value = `Changes in workspace detected.
    Starting computation for ${total_batches} batches`
  }
  async function onRematchBatchStarted({ total_batches }) {
    // if the rematch batches progress already opened - skip
    if (rematchBatchesProgress.value) return
    rematchBatchProgress.value = true
    totalBatches.value = total_batches
    progressMessage.value = `Changes in workspace detected.
    Starting computation for ${total_batches} batches`
  }
  async function onRematchBatchProgress({ current_batch, current_batch_message }) {
    if (current_batch) {
      currentBatch.value = current_batch
      progressMessage.value = `Changes in workspace detected.
      Computing matches for sample batch ${current_batch} / ${totalBatches.value}`
    }
    if (current_batch_message) {
      currentBatchMessage.value = current_batch_message
    } else {
      currentBatchMessage.value = ''
    }
  }
  async function onRematchBatchesProgressPercentage({ progress_percentage }) {
    if (progress_percentage) {
      progressPercentage.value = progress_percentage
    }
  }
  async function onRematchBatchProgressPercentage({ progress_percentage }) {
    // if the rematch batches progress already opened - skip
    if (rematchBatchesProgress.value) return
    if (progress_percentage) {
      progressPercentage.value = progress_percentage
    }
  }
  async function onRematchBatchesFinished({ samples_compute_failed }) {
    let message = `Finished computation for ${
      totalBatches.value
    } batch${totalBatches.value === 1 ? '' : 'es'}`

    if (samples_compute_failed && samples_compute_failed.length > 0) {
      computeError.value = true
      message += ` with ${samples_compute_failed.length} sample${
        samples_compute_failed.length === 1 ? '' : 's'
      } failed to compute matches`

      // Show warning notification after 3 seconds with info about failed to compute matches samples
      setTimeout(() => {
        showWarningNotification({
          notification: 'batchComputeFailedSamples',
          data: samples_compute_failed
        })
      }, 4000)
    }
    progressMessage.value = message
    currentBatchMessage.value = ''
    progressPercentage.value = 100
    setTimeout(() => {
      // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
      rematchBatchesProgress.value = false
      totalBatches.value = null
      currentBatch.value = null
      setTimeout(() => {
        progressMessage.value = ''
        computeError.value = false
        progressPercentage.value = 0
      }, 500)
    }, 4000)
  }
  async function onRematchBatchFinished({ samples_compute_failed }) {
    // if the rematch batches progress already opened - skip
    if (rematchBatchesProgress.value) return
    let message = `Finished computation for ${
      totalBatches.value
    } batch${totalBatches.value === 1 ? '' : 'es'}`

    if (samples_compute_failed && samples_compute_failed.length > 0) {
      computeError.value = true
      message += ` with ${samples_compute_failed.length} sample${
        samples_compute_failed.length === 1 ? '' : 's'
      } failed to compute matches`

      // Show warning notification after 3 seconds with info about failed to compute matches samples
      setTimeout(() => {
        showWarningNotification({
          notification: 'batchComputeFailedSamples',
          data: samples_compute_failed
        })
      }, 4000)
    }
    progressMessage.value = message
    currentBatchMessage.value = ''
    progressPercentage.value = 100
    setTimeout(() => {
      // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
      rematchBatchProgress.value = false
      totalBatches.value = null
      currentBatch.value = null
      setTimeout(() => {
        progressMessage.value = ''
        computeError.value = false
        progressPercentage.value = 0
      }, 500)
    }, 4000)
  }
  // Item compute progress notification
  async function onMatchItemUpdateComputeStarted({ sample_item_name }) {
    resetCalibrationNotification()
    itemMatchComputing.value = true
    progressMessage.value = `Computing matches for "${sample_item_name}"`
    progressPercentage.value = 0
  }
  async function onMatchItemUpdateComputeProgress({ progress_percentage }) {
    if (progress_percentage) {
      progressPercentage.value = progress_percentage
    }
  }
  async function onMatchItemUpdateComputeFinished({ sample_item_name }) {
    progressMessage.value = `Computing matches for "${sample_item_name}" is finished`
    progressPercentage.value = 100
    setTimeout(() => {
      // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
      itemMatchComputing.value = false
      setTimeout(() => {
        progressMessage.value = ''
        progressPercentage.value = 0
      }, 500)
    }, 3000)
  }
  async function onMatchItemUpdateComputeFailed({ sample_item_name, errorMessage }) {
    progressMessage.value = `Computing matches failed for "${sample_item_name}"`
    progressPercentage.value = 100
    computeError.value = true
    setTimeout(() => {
      // Show warning notification after 3 seconds with info about failed to compute matches samples
      showWarningNotification({
        notification: 'itemComputeFailed',
        data: errorMessage
      })

      // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
      itemMatchComputing.value = false
      setTimeout(() => {
        progressMessage.value = ''
        progressPercentage.value = 0
        computeError.value = false
      }, 500)
    }, 3000)
  }
  // calibration notifications
  // TODO_notifications	refactor to use unified progress component/onActionFinished
  async function onCalibrationStarted({ action, progress_percentage }) {
    calibrationComputing.value = true
    calibrationAction.value = action
    progressMessage.value = `Calibration process started: ${action}...`
    progressPercentage.value = progress_percentage
  }
  async function onCalibrationProgress({ progress_percentage }) {
    if (progress_percentage) {
      progressPercentage.value = progress_percentage
    }
  }
  async function onCalibrationFinished({ action }) {
    progressMessage.value = `Calibration process finished: ${action}...`
    setTimeout(() => {
      if (calibrationAction.value !== action) {
        return // Do not close if this is not the currently active action.
      }
      calibrationComputing.value = false
      setTimeout(() => {
        if (calibrationAction.value !== action) {
          return // Do not close if this is not the currently active action.
        }
        if (!calibrationProgressActive.value) {
          return // Do not reset if calibrationAction is not the currently active action.
        }
        resetCalibrationNotification()
      }, 500)
    }, 3000)
  }
  async function onCalibrationFailed({ action, error }) {
    progressMessage.value = `Calibration process ${action} failed: ${error}`
    calibrationError.value = true
    setTimeout(() => {
      // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
      calibrationComputing.value = false
      setTimeout(() => {
        resetCalibrationNotification()
      }, 500)
    }, 5000)
  }

  // delete notifications
  async function onDeleteFinished(data) {
    onActionFinished(data)
  }
  // copy notifications
  async function onCopyFinished(data) {
    onActionFinished(data)
  }
  // import batch notifications
  async function onImportSamplesToBatchFinished(data) {
    onActionFinished(data)
  }
  // batch peaks export
  async function onBatchExportPeakDataProgress({ progress_percentage, progress_data_message }) {
    progressPercentage.value = progress_percentage ?? 0
    progressDataMessage.value = progress_data_message ?? ''
  }
  async function onBatchExportPeakDataFinished(data) {
    onActionFinished(data)
    await appStore.pushNotify({
      message: 'Sample batch peak export finished',
      key: Math.random()
    })
  }

  // unified progress finished notification for actions
  async function onActionFinished({ status, action, type, message, progress_percentage }) {
    const progressState = progress(action)
    if (status === 'success') {
      // reopen the notification, if it was closed
      progressAction.value = action
      progressState.value = action
      progressActionType.value = type ?? null
      // set the message and 100 progress
      progressMessage.value = message
      progressPercentage.value = progress_percentage ?? 100
    } else if (status === 'error') {
      // reopen the notification, if it was closed
      progressAction.value = action
      progressState.value = true // TODO check if this is a bug
      progressActionType.value = type ?? null
      // set the error message and error flag
      progressMessage.value = message
      progressPercentage.value = progress_percentage ?? 100
      progressError.value = true
    }
    // Set a timeout to deactivate the modal and reset the progress notification state
    setTimeout(
      () => {
        // Deactivate the modal by setting the progress state of the action to false.
        // This will trigger the watcher in TheNotificationProgress.vue to close the modal.
        progressState.value = false
        // This clears out the progress message and other state for the next action.
        setTimeout(() => {
          resetProgressNotification()
        }, 500) // TODO_configuration 500ms delay to reset the progress notification for fade-out animation
      },
      status === 'error' ? 5000 : 4000 // 5s delay for error, 4s delay for success
    )
  }

  return {
    active,
    warningActive,
    generalActive,
    progressActive,
    batchComputeProgressActive,
    itemComputeProgressActive,
    calibrationProgressActive,
    warningNotification,
    warningData,
    generalNotification,
    generalNotificationMessage,
    progressAction,
    progressActionType,
    progressMessage,
    progressDataMessage,
    progressError,
    progressPercentage,
    copyProgress,
    exportProgress,
    importProgress,
    deleteProgress,
    itemMatchComputing,
    rematchBatchProgress,
    rematchBatchesProgress,
    totalBatches,
    currentBatch,
    currentBatchMessage,
    calibrationComputing,
    calibrationAction,
    computeError,
    calibrationError,
    showGeneralNotification,
    showProgressNotification,
    showWarningNotification,
    resetGeneralNotification,
    resetWarningNotification,
    resetCalibrationNotification,
    closeGeneralNotification,
    onRematchBatchStarted,
    onRematchBatchesStarted,
    onRematchBatchProgress,
    onRematchBatchProgressPercentage,
    onRematchBatchesProgressPercentage,
    onRematchBatchFinished,
    onRematchBatchesFinished,
    onMatchItemUpdateComputeStarted,
    onMatchItemUpdateComputeProgress,
    onMatchItemUpdateComputeFinished,
    onMatchItemUpdateComputeFailed,
    onCalibrationStarted,
    onCalibrationProgress,
    onCalibrationFailed,
    onCalibrationFinished,
    onDeleteFinished,
    onCopyFinished,
    onImportSamplesToBatchFinished,
    onBatchExportPeakDataFinished,
    onBatchExportPeakDataProgress
  }
})
