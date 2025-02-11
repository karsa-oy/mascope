<script setup>
import { reactive } from 'vue'

import Button from 'primevue/button'
import ConfirmPopup from 'primevue/confirmpopup'
import { useConfirm } from 'primevue/useconfirm'

import { api } from '@/api'
import { DialogMatchRating } from '@/lib/dialogs'

import { useApp } from '@/stores'

const app = useApp()

const confirm = useConfirm()
const dialog = reactive({
  visible: false,
  rating: -1
})

/**
 * Submits a match rating for the currently visualized ion match.
 * Checks for unsaved filter parameter changes and prompts the user to save or discard them.
 * Proceeds to submit the rating to the API if conditions are met.
 *
 * @param {number} rating - The rating to be submitted (0 = No Detection, 1 = Ambiguous, 2 = Detection)
 */
async function submitRating(rating) {
  if (app.data.match.params.changed) {
    handleUnsavedMatchParams()
  } else {
    processRatingSubmission(rating)
  }
}

/**
 * Processes the rating submission by either opening a dialog for ambiguous or mismatched ratings,
 * or directly submitting the rating to the API.
 *
 * @param {number} rating - The rating to be submitted
 */
async function processRatingSubmission(rating) {
  const matchScore = app.data.match.visualized.ion.match_score
  const possibleMatch = matchScore >= app.data.match.params.ui.possible_match_threshold

  if (rating === 1 || (rating === 0 && possibleMatch) || (rating === 2 && !possibleMatch)) {
    dialog.rating = rating
    dialog.visible = true
  } else {
    await api.http.post(
      `/match_ratings`,
      {
        sample_item_id: app.data.sample.focused.sample_item_id,
        target_ion_id: app.data.match.visualized.ion.target_ion_id,
        rating,
        environment: {
          mz_calibration: app.data.sample.focused.mz_calibration
        }
      },
      {
        use: 'create',
        type: 'match_rating'
      }
    )
  }
}

/**
 * Handles the scenario where there are unsaved filter parameter changes.
 * Prompts the user to either save the changes or discard them before proceeding with the rating submission.
 */
function handleUnsavedMatchParams() {
  confirm.require({
    icon: 'pi pi-exclamation-triangle',
    header: 'Unsaved match settings',
    message:
      'You have unsaved changes in your match isotope/peak parameters. Please save or discard them before submitting a rating.',
    accept: app.data.match.params.save,
    acceptProps: {
      icon: 'pi pi-save',
      label: 'Save changes'
    },
    reject: app.data.match.params.revert,
    rejectProps: {
      icon: 'pi pi-times',
      label: 'Discard changes',
      severity: 'secondary'
    }
  })
}
</script>

<template>
  <Button
    v-tooltip.bottom="'Rate Match'"
    severity="help"
    icon="pi pi-star"
    iconClass="small-icon"
    @click="
      (event) => {
        confirm.require({
          target: event.currentTarget,
          group: 'match-rating'
        })
      }
    "
  />
  <ConfirmPopup group="match-rating">
    <template #container="{ acceptCallback }">
      <div class="col" style="padding: 1rem; gap: 0.2rem">
        <div class="row">
          <Button
            v-tooltip.top="'No Detection'"
            severity="danger"
            icon="pi pi-times-circle"
            @click="
              () => {
                submitRating(0)
                acceptCallback()
              }
            "
          />
          <Button
            v-tooltip.top="'Ambiguous'"
            severity="info"
            icon="pi pi-question-circle"
            @click="
              () => {
                submitRating(1)
                acceptCallback()
              }
            "
          />
          <Button
            v-tooltip.top="'Detection'"
            severity="success"
            icon="pi pi-check-circle"
            @click="
              () => {
                submitRating(2)
                acceptCallback()
              }
            "
          />
        </div>
        <p style="font-weight: bold; margin: 0">Is this a match?</p>
      </div>
    </template>
  </ConfirmPopup>
  <DialogMatchRating v-model:visible="dialog.visible" :rating="dialog.rating" />
</template>

<style scoped>
.p-panel {
  padding: 0.75rem;
}

.row {
  margin-bottom: 0.3rem;
}

.small-icon {
  height: 12px;
  width: 12px;
}
</style>
