<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/icons/AppIcon.vue'

const authStore = useAuthStore()
const router = useRouter()

const loading = ref(false)
const errorMessage = ref('')
const form = reactive({
  email: '',
  password: '',
})

async function onSubmit() {
  loading.value = true
  errorMessage.value = ''

  await new Promise((resolve) => setTimeout(resolve, 350))
  const result = await authStore.login({ email: form.email, password: form.password })

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
      <h1>Welcome back</h1>
      <p class="muted">Sign in to continue to your channels and saved videos.</p>

      <form class="auth-form" @submit.prevent="onSubmit">
        <label>
          Email
          <input v-model="form.email" type="email" placeholder="you@example.com" required />
        </label>

        <label>
          Password
          <input v-model="form.password" type="password" placeholder="Enter your password" required />
        </label>
        <RouterLink class="forgot-link" to="/reset-password">Forgot password?</RouterLink>

        <button type="submit" :disabled="loading">
          {{ loading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>

      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

      <div class="switch-link">
        Don't have an account?
        <RouterLink to="/register">Sign up</RouterLink>
      </div>

      <div class="demo-box">
        <p>Demo account: tech@example.com or admin@example.com</p>
        <p>Password: at least 8 characters with letters and numbers</p>
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
  width: min(460px, 100%);
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
  opacity: 0.7;
  cursor: wait;
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

.forgot-link {
  justify-self: end;
  font-size: 13px;
  color: var(--accent-text-strong);
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

.demo-box {
  margin-top: 18px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-faint);
  background: var(--surface-subtle);
  color: var(--text-muted);
  font-size: 12px;
}
</style>
