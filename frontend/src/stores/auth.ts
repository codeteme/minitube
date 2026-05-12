// Single source of truth for the frontend application for "Who is currently logged in"

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authService } from '@/services/auth'
import type { ForgotPasswordPayload, LoginPayload, RegisterPayload, ResetPasswordPayload, User } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<User | null>(null)

  const isAuthenticated = computed(() => currentUser.value !== null)

  async function hydrate() {
    currentUser.value = await authService.hydrateCurrentUser()
  }

  async function login(payload: LoginPayload) {
    const result = await authService.login(payload)
    if (result.ok) currentUser.value = result.user
    return result
  }

  async function register(payload: RegisterPayload) {
    const result = await authService.register(payload)
    if (result.ok) currentUser.value = result.user
    return result
  }

  async function updateProfile(update: Pick<User, 'username' | 'bio'>) {
    const result = await authService.updateCurrentUser(update)
    if (result.ok) {
      currentUser.value = result.user
    }
    return result
  }

  async function uploadProfileAvatar(file: File) {
    const result = await authService.uploadAvatar(file)
    if (result.ok) {
      currentUser.value = result.user
    }
    return result
  }

  async function requestPasswordReset(payload: ForgotPasswordPayload) {
    return await authService.requestPasswordReset(payload)
  }

  async function confirmPasswordReset(payload: ResetPasswordPayload) {
    return await authService.confirmPasswordReset(payload)
  }

  function logout() {
    authService.logout()
    currentUser.value = null
  }

  return {
    currentUser,
    isAuthenticated,
    hydrate,
    login,
    register,
    updateProfile,
    uploadProfileAvatar,
    requestPasswordReset,
    confirmPasswordReset,
    logout,
  }
})