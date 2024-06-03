<script setup>
import { reactive } from 'vue'

import Button from 'primevue/button'
import ConfirmPopup from 'primevue/confirmpopup'
import { useConfirm } from 'primevue/useconfirm'

import { api } from '@/api'
import { DialogMatchRating } from '@/lib/dialogs'

import { useFocusedMatch, useFilterParams, useSampleStore } from '@/stores'

const sampleStore = useSampleStore()
const focusedMatch = useFocusedMatch()
const filterParams = useFilterParams()

const confirm = useConfirm()
const dialog = reactive({
  visible: false,
  rating: -1
})

async function submit(rating) {
  const possibleMatch =
    focusedMatch.ion.match_score >= filterParams.current.possible_match_threshold
  if ((rating == 0 && possibleMatch) || rating == 1 || (rating == 1 && !possibleMatch)) {
    dialog.rating = rating
    dialog.visible = true
  } else {
    await api.request.create({
      method: 'submitMatchRating',
      body: {
        sample_item_id: sampleStore.active.sample_item_id,
        target_ion_id: focusedMatch.ion.target_ion_id,
        rating,
        environment: {
          mz_calibration: sampleStore.active.mz_calibration
        }
      }
    })
  }
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
                submit(0)
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
                submit(1)
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
                submit(2)
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
