<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/icons/AppIcon.vue'

const route = useRoute()
const authStore = useAuthStore()

const requestEmail = ref('')
const requestLoading = ref(false)
const resetLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const resetForm = reactive({
  newPassword: '',
  confirmPassword: '',
})

const resetToken = computed(() => {
  const token = route.query.token
  return typeof token === 'string' ? token.trim() : ''
})

const hasResetToken = computed(() => resetToken.value.length > 0)

function isStrongPassword(password: string): boolean {
  if (password.length < 8) return false
  if (!/[A-Za-z]/.test(password)) return false
  if (!/\d/.test(password)) return false
  return true
}

const canSubmitReset = computed(() => {
  if (!hasResetToken.value || resetLoading.value) return false
  if (!resetForm.newPassword || !resetForm.confirmPassword) return false
  if (resetForm.newPassword !== resetForm.confirmPassword) return false
  return isStrongPassword(resetForm.newPassword)
})

async function onRequestResetLink() {
  errorMessage.value = ''
  successMessage.value = ''

  const email = requestEmail.value.trim()
  if (!email) {
    errorMessage.value = 'Enter your account email.'
    return
  }

  requestLoading.value = true
  const result = await authStore.requestPasswordReset({ email })
  requestLoading.value = false

  if (!result.ok) {
    errorMessage.value = result.message
    return
  }

  successMessage.value = result.message
}

async function onResetPassword() {
  errorMessage.value = ''
  successMessage.value = ''

  if (!hasResetToken.value) {
    errorMessage.value = 'Reset token missing. Open the link from your email.'
    return
  }

  if (resetForm.newPassword !== resetForm.confirmPassword) {
    errorMessage.value = 'Passwords do not match.'
    return
  }

  if (!isStrongPassword(resetForm.newPassword)) {
    errorMessage.value = 'Password must be at least 8 characters and include both letters and numbers.'
    return
  }

  resetLoading.value = true
  const result = await authStore.confirmPasswordReset({
    token: resetToken.value,
    newPassword: resetForm.newPassword,
  })
  resetLoading.value = false

  if (!result.ok) {
    errorMessage.value = result.message
    return
  }

  successMessage.value = result.message
  resetForm.newPassword = ''
  resetForm.confirmPassword = ''
}
</script>

<template>
  <section class="auth-shell">
    <div class="auth-card">
      <div class="auth-icon" aria-hidden="true"><AppIcon name="login" :size="22" :stroke-width="2" /></div>
      <p class="brand-mark">MEDIA HUB</p>

      <template v-if="hasResetToken">
        <h1>Set a new password</h1>
        <p class="muted">
          Create a new password for your account. It must be at least 8 characters and include
          letters and numbers.
        </p>

        <form class="auth-form" @submit.prevent="onResetPassword">
          <label>
            New password
            <input
              v-model="resetForm.newPassword"
              type="password"
              placeholder="At least 8 chars, letters + numbers"
              required
            />
          </label>

          <label>
            Confirm new password
            <input
              v-model="resetForm.confirmPassword"
              type="password"
              placeholder="Re-enter your new password"
              required
            />
          </label>

          <button type="submit" :disabled="!canSubmitReset">
            {{ resetLoading ? 'Resetting password...' : 'Reset Password' }}
          </button>
        </form>
      </template>

      <template v-else>
        <h1>Forgot your password?</h1>
        <p class="muted">
          Enter your account email and we will send a secure reset link if the account exists.
        </p>

        <form class="auth-form" @submit.prevent="onRequestResetLink">
          <label>
            Email
            <input
              v-model="requestEmail"
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
              required
            />
          </label>

          <button type="submit" :disabled="requestLoading">
            {{ requestLoading ? 'Sending reset link...' : 'Send Reset Link' }}
          </button>
        </form>
      </template>

      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <p v-if="successMessage" class="success">{{ successMessage }}</p>

      <div class="switch-link">
        Back to
        <RouterLink to="/login">Sign in</RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.auth-shell {
  min-height: calc(100vh - 68px);
  display: grid;
  place-items: center;
  padding: 24px;
}

.auth-card {
  width: min(500px, 100%);
  background: var(--surface-auth);
  border: 1px solid var(--border-default);
  border-radius: 18px;
  padding: 28px;
  box-shadow: var(--shadow-modal);
}

.auth-icon {
  width: 52px;
  height: 52px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: var(--text-inverse);
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  margin-bottom: 14px;
}

.brand-mark {
  color: var(--accent-border-focus);
  letter-spacing: 0.14em;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
}

h1 {
  font-size: 30px;
  color: var(--text-main);
  margin-bottom: 6px;
}

.muted {
  color: var(--text-muted);
  margin-bottom: 20px;
}

.auth-form {
  display: grid;
  gap: 14px;
}

label {
  display: grid;
  gap: 6px;
  color: var(--text-body);
  font-size: 14px;
}

input {
  width: 100%;
  border: 1px solid var(--border-strong);
  background: var(--surface-auth-input);
  color: var(--text-main);
  border-radius: 10px;
  padding: 11px 12px;
}

input:focus {
  outline: none;
  border-color: var(--accent-border-focus);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

button {
  border: none;
  border-radius: 10px;
  padding: 12px;
  color: var(--text-inverse);
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  font-weight: 600;
  cursor: pointer;
}

button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error {
  margin-top: 12px;
  color: var(--accent-text-mid);
  font-size: 14px;
}

.success {
  margin-top: 12px;
  color: #22c55e;
  font-size: 14px;
}

.switch-link {
  margin-top: 18px;
  color: var(--link-muted);
  font-size: 14px;
}

.switch-link a {
  margin-left: 6px;
  color: var(--accent-text-strong);
}
</style>
