<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/icons/AppIcon.vue'

const authStore = useAuthStore()
const router = useRouter()

const loading = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const passwordChecks = computed(() => {
  const password = form.password
  return {
    minLength: password.length >= 8,
    hasLetter: /[A-Za-z]/.test(password),
    hasNumber: /\d/.test(password),
  }
})

const passwordRulePassCount = computed(() => {
  return Object.values(passwordChecks.value).filter(Boolean).length
})

const passwordStrength = computed(() => {
  if (!form.password) return { label: '', score: 0, tone: 'neutral' as const }
  if (passwordRulePassCount.value === 3) return { label: 'Strong', score: 100, tone: 'strong' as const }
  if (passwordRulePassCount.value === 2) return { label: 'Medium', score: 66, tone: 'medium' as const }
  return { label: 'Weak', score: 33, tone: 'weak' as const }
})

function isStrongPassword(password: string): boolean {
  if (password.length < 8) return false
  if (!/[A-Za-z]/.test(password)) return false
  if (!/\d/.test(password)) return false
  return true
}

const canSubmit = computed(() => {
  if (loading.value) return false
  if (!form.username.trim() || !form.email.trim()) return false
  if (!form.password || !form.confirmPassword) return false
  if (form.password !== form.confirmPassword) return false
  return isStrongPassword(form.password)
})

async function onSubmit() {
  errorMessage.value = ''

  if (form.password !== form.confirmPassword) {
    errorMessage.value = 'Passwords do not match.'
    return
  }

  if (!isStrongPassword(form.password)) {
    errorMessage.value = 'Password must be at least 8 characters and include both letters and numbers.'
    return
  }

  loading.value = true
  await new Promise((resolve) => setTimeout(resolve, 350))

  const result = await authStore.register({
    username: form.username,
    email: form.email,
    password: form.password,
  })

  loading.value = false
  if (!result.ok) {
    errorMessage.value = result.message
    return
  }

  router.push('/')
}
</script>

<template>
  <section class="auth-shell">
    <div class="auth-card">
      <div class="auth-icon" aria-hidden="true"><AppIcon name="play" :size="22" :stroke-width="2" /></div>
      <p class="brand-mark">MEDIA HUB</p>
      <h1>Create an account</h1>
      <p class="muted">Join the community to upload, subscribe, and engage.</p>

      <form class="auth-form" @submit.prevent="onSubmit">
        <label>
          Username
          <input v-model="form.username" type="text" placeholder="johndoe" required />
        </label>

        <label>
          Email
          <input v-model="form.email" type="email" placeholder="you@example.com" required />
        </label>

        <label>
          Password
          <input
            v-model="form.password"
            type="password"
            placeholder="At least 8 chars, letters + numbers"
            required
          />
          <div v-if="form.password" class="password-strength">
            <div class="strength-head">
              <span>Strength: {{ passwordStrength.label }}</span>
              <span>{{ passwordRulePassCount }}/3 rules</span>
            </div>
            <div class="strength-track" aria-hidden="true">
              <span
                class="strength-fill"
                :class="`tone-${passwordStrength.tone}`"
                :style="{ width: `${passwordStrength.score}%` }"
              />
            </div>
            <ul class="rule-list">
              <li :class="{ pass: passwordChecks.minLength }">At least 8 characters</li>
              <li :class="{ pass: passwordChecks.hasLetter }">Contains at least one letter</li>
              <li :class="{ pass: passwordChecks.hasNumber }">Contains at least one number</li>
            </ul>
          </div>
        </label>

        <label>
          Confirm Password
          <input v-model="form.confirmPassword" type="password" placeholder="Re-enter your password" required />
        </label>

        <button type="submit" :disabled="!canSubmit">
          {{ loading ? 'Creating account...' : 'Sign Up' }}
        </button>
      </form>

      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

      <div class="switch-link">
        Already have an account?
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
  background: var(--surface-auth-2);
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
  font-size: 18px;
  font-weight: 700;
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

.password-strength {
  margin-top: 8px;
  display: grid;
  gap: 8px;
}

.strength-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
}

.strength-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.25);
  overflow: hidden;
}

.strength-fill {
  display: block;
  height: 100%;
  transition: width 0.2s ease;
}

.strength-fill.tone-weak {
  background: #ef4444;
}

.strength-fill.tone-medium {
  background: #f59e0b;
}

.strength-fill.tone-strong {
  background: #22c55e;
}

.rule-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.rule-list .pass {
  color: #22c55e;
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
