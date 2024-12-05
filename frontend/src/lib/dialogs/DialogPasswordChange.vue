<script setup>
import { ref, reactive, computed, watch } from 'vue'

import FloatLabel from 'primevue/floatlabel'
import Dialog from 'primevue/dialog'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

import { useApp } from '@/stores'

const app = useApp()

const visible = defineModel('visible')

const password = reactive({
  current: null,
  new: null,
  verify: null
})

watch(visible, () => {
  password.current = null
  password.new = null
  password.verify = null
})

const invalidCurrentPassword = computed(() => password.current && password.current?.length == 0)
const invalidNewPassword = computed(() => password.new && password.new?.length == 0)
const invalidVerifyPassword = computed(() => password.verify && password.verify?.length == 0)
const mismatchingPasswords = computed(
  () => password.new && password.verify && password.new !== password.verify
)

const invalid = computed(
  () =>
    !password.current ||
    !password.new ||
    !password.verify ||
    invalidCurrentPassword.value ||
    invalidNewPassword.value ||
    invalidVerifyPassword.value ||
    mismatchingPasswords.value
)

const execute = () => {
  app.data.user.updateMeCreds({
    currentPassword: password.current,
    newPassword: password.new,
    verifyNewPassword: password.verify
  })
  visible.value = false
}
</script>

<template>
  <Dialog v-model:visible="visible" header="Change your password" modal style="width: 400px">
    <section>
      <FloatLabel>
        <Password
          id="current-password"
          v-model="password.current"
          :invalid="invalidCurrentPassword"
          fluid
        />
        <label for="current-password">Current password</label>
      </FloatLabel>
      <FloatLabel>
        <Password id="new-password" v-model="password.new" :invalid="invalidNewPassword" fluid />
        <label for="new-password">New password</label>
      </FloatLabel>
      <FloatLabel>
        <Password
          id="new-password-verify"
          v-model="password.verify"
          :invalid="invalidVerifyPassword"
          fluid
        />
        <label for="new-password-verify">Verify new password</label>
      </FloatLabel>
    </section>
    <menu style="margin-top: 2rem">
      <Message v-if="mismatchingPasswords" icon="pi pi-exclamation-triangle" severity="secondary">
        Your passwords do not match.
      </Message>
      <Button label="Cancel" @click="visible = false" severity="secondary" />
      <Button label="Save" @click="execute" :disabled="invalid" />
    </menu>
  </Dialog>
</template>
