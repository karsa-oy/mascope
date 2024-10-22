<script setup>
import Panel from 'primevue/panel'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'

import { useAuth } from '@/stores/auth'

import { reactive, computed } from 'vue'

const auth = useAuth()

const input = reactive({
  email: null,
  password: null
})

const invalid = computed(() => ({
  email: input.email?.length < 5 || !input.email?.includes('@'),
  password: input.password?.length < 8
}))

const disabled = computed(() => invalid.value.email || invalid.value.password)
</script>


<template>
  <div class="fields" style="flex-flow: column">
    <FloatLabel>
      <InputText
        id="login-email"
        v-model="input.email"
        :invalid="invalid.email"
        style="width: 100%"
        required
      />
      <label for="login-email">Email</label>
    </FloatLabel>
    <FloatLabel>
      <Password
        id="login-password"
        v-model="input.password"
        :invalid="invalid.password"
        style="width: 100%"
        required
      />
      <label for="login-password">Password</label>
    </FloatLabel>
    <Button
      @click="auth.login(input)"
      label="Login"
      icon="pi pi-sign-in"
      :disabled="disabled"
    />
  </div>
</template>

<style scoped>
  :deep(.p-password-input) {
    width: 100%;
  }
</style>
