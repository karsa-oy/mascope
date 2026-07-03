<script setup>
import { reactive, computed } from 'vue'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useAuth } from '@/stores/auth'
import { passwordPolicyError } from '@/lib/password'

const auth = useAuth()

const input = reactive({
  email: null,
  username: null,
  password: null,
  confirmPassword: null,
  serverSecret: null
})

// Mirror the backend password policy for instant feedback.
const passwordError = computed(() =>
  input.password
    ? passwordPolicyError(input.password, { email: input.email, username: input.username })
    : null
)

const invalid = computed(() => ({
  email: !input.email || input.email?.length < 5 || !input.email?.includes('@'),
  username: !input.username || input.username?.length < 5,
  password: !input.password || input.password !== input.confirmPassword || !!passwordError.value,
  serverSecret: !input.serverSecret || input.serverSecret.length < 1
}))

const disabled = computed(() => Object.values(invalid.value).some((v) => v))

const signup = async () => {
  if (!disabled.value) {
    await auth.signupFirstOwner({
      email: input.email,
      username: input.username,
      password: input.password,
      serverSecret: input.serverSecret
    })
  }
}
</script>

<template>
  <h3 style="opacity: 0.7; text-align: center">Create owner account</h3>
  <div class="fields">
    <div class="field">
      <FloatLabel>
        <InputText
          id="signup-email"
          v-model="input.email"
          :invalid="input.email && invalid.email"
          required
        />
        <label for="signup-email">Email</label>
      </FloatLabel>
    </div>
    <div class="field">
      <FloatLabel>
        <InputText
          id="signup-username"
          v-model="input.username"
          :invalid="input.username && invalid.username"
          required
        />
        <label for="signup-username">Full name</label>
      </FloatLabel>
    </div>
    <div class="field">
      <FloatLabel>
        <Password
          id="signup-password"
          v-model="input.password"
          :invalid="input.password && invalid.password"
          required
        />
        <label for="signup-password">Password</label>
      </FloatLabel>
    </div>
    <div class="field">
      <FloatLabel>
        <Password
          id="signup-confirm-password"
          v-model="input.confirmPassword"
          :invalid="input.confirmPassword && invalid.password"
          required
          @keyup.enter="signup"
        />
        <label for="signup-confirm-password">Confirm password</label>
      </FloatLabel>
    </div>
    <Message
      v-if="input.password && passwordError"
      icon="pi pi-exclamation-triangle"
      severity="secondary"
    >
      {{ passwordError }}
    </Message>
    <div class="field">
      <FloatLabel>
        <InputText
          id="owner-signup-server-secret"
          v-model="input.serverSecret"
          :invalid="input.serverSecret && invalid.serverSecret"
          type="password"
          required
        />
        <label for="owner-signup-server-secret">Server password</label>
      </FloatLabel>
    </div>
  </div>
  <Button
    @click="signup"
    label="Create owner"
    icon="pi pi-check"
    :disabled="disabled"
    fluid
    style="margin-top: 2rem"
  />
</template>
