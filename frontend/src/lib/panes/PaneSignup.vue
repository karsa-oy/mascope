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
  username: null,
  password: null,
  confirmPassword: null
})

const invalid = computed(() => ({
  email: !input.email || input.email?.length < 5 || !input.email?.includes('@'),
  username: !input.username || input.username?.length < 5,
  password:
    !input.password || input.password !== input.confirmPassword || !(input.password?.length > 0)
}))

const disabled = computed(
  () => invalid.value.email || invalid.value.username || invalid.value.password
)

const emit = defineEmits(['signup'])

const signup = async () => {
  if (!disabled.value) {
    const { status } = await auth.signup(input)
    if (status == 'success') {
      emit('signup')
    }
  }
}
</script>

<template>
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
      <small>
        <span v-if="invalid.email"> Enter a valid email address </span>
      </small>
    </div>
    <div class="field">
      <FloatLabel>
        <InputText
          id="signup-username"
          v-model="input.username"
          :invalid="input.username && invalid.username"
          required
        />
        <label for="signup-username">Full Name</label>
      </FloatLabel>
      <small>
        <span v-if="invalid.username"> Enter your full name </span>
      </small>
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
      <small>
        <span v-if="invalid.password"> Enter a password (min 8 characters) </span>
      </small>
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
        <label for="signup-confirm-password">Confirm Password</label>
      </FloatLabel>
      <small>
        <span v-if="invalid.password"> Repeat your password </span>
      </small>
    </div>
  </div>
  <Button
    @click="signup"
    label="Sign up"
    icon="pi pi-check"
    :disabled="disabled"
    fluid
    style="margin-top: 2rem"
  />
</template>
