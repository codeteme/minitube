import type {
  AuthResult,
  LoginPayload,
  RegisterPayload,
  User,
  BackendUser,
  BackendToken,
  UserPreferencesDTO,
  UserPreferencesPatch,
  PreferencesUpdateResult,
  ForgotPasswordPayload,
  ResetPasswordPayload,
  PasswordResetResult,
} from '@/types/auth'

// Use the environment variable of where the backend is hosted
const DEFAULT_HOST =
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? '127.0.0.1'
    : typeof window !== 'undefined'
      ? window.location.hostname
      : 'localhost'
const AUTH_API_BASE_URL = (
  import.meta.env.VITE_AUTH_API_BASE_URL || `http://${DEFAULT_HOST}:8003`
).replace(/\/$/, '')

// Simple String constants, names to save and retrieve data in the browser's localStorage
const ACCESS_TOKEN_KEY = 'media_frontend_access_token'
const CURRENT_USER_KEY = 'media_frontend_current_user'

const DEFAULT_AVATAR_URL = '/default-avatar.svg'

const AVATAR_FILE_PREFIX = '/user/profile/avatar/file/'

/** Turn stored profile paths into a browser-usable URL (uploads live under /file/{userId}/{filename}). */
function resolveAvatarUrl(avatar: string | null | undefined, backendUserId: number): string {
  if (avatar == null || avatar === '') return DEFAULT_AVATAR_URL
  if (avatar.startsWith('http://') || avatar.startsWith('https://')) return avatar
  if (avatar.startsWith(AVATAR_FILE_PREFIX)) {
    const filename = avatar.slice(AVATAR_FILE_PREFIX.length)
    return `${AUTH_API_BASE_URL}${AVATAR_FILE_PREFIX}${backendUserId}/${filename}`
  }
  if (avatar.startsWith('/')) return `${AUTH_API_BASE_URL}${avatar}`
  return avatar
}

// Maps the data returned by a backend to the frontend
function mapBackendUser(u: BackendUser): User {
  return {
    id: String(u.id),
    username: u.name,
    email: u.email,
    bio: u.bio ?? '',
    avatar: resolveAvatarUrl(u.avatar, u.id),
    isAdmin: u.role === 'admin',
    subscribedTo: [],
    notifications: [],
  }
}

function parseApiErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (typeof first === 'string' && first.trim()) return first
    if (first && typeof first === 'object' && 'msg' in first) {
      const msg = (first as { msg?: unknown }).msg
      if (typeof msg === 'string' && msg.trim()) return msg
    }
  }
  if (detail && typeof detail === 'object' && 'msg' in detail) {
    const msg = (detail as { msg?: unknown }).msg
    if (typeof msg === 'string' && msg.trim()) return msg
  }
  return fallback
}

// Wrappers around the browser's localStorage API
// NOTE: localStorage can only save text strings, when saving the user object, it uses JSON.stringify(user) to convert the object to a string. When getting the user back,
// it uses JSON.parse(raw) to turn the string back into a usable JavaScript object
function saveToken(token: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

function getToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

/** Sync stored UI theme to the document (backend values: dark | light, default dark). */
export function applyDocumentUiTheme(theme: string) {
  if (typeof document === 'undefined') return
  const normalized = theme === 'light' ? 'light' : 'dark'
  document.documentElement.dataset.uiTheme = normalized
}

async function fetchUserPreferences(tokenOverride?: string | null): Promise<UserPreferencesDTO | null> {
  const token = tokenOverride ?? getToken()
  if (!token) return null

  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/user/preferences`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (response.status === 401) {
      logout()
      return null
    }

    if (!response.ok) return null

    return (await response.json()) as UserPreferencesDTO
  } catch {
    return null
  }
}

async function updateUserPreferences(patch: UserPreferencesPatch): Promise<PreferencesUpdateResult> {
  const token = getToken()
  if (!token) {
    return { ok: false, message: 'No active session.' }
  }

  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/user/preferences/update`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(patch),
    })

    if (response.status === 401) {
      logout()
      return { ok: false, message: 'Session expired. Sign in again.' }
    }

    if (!response.ok) {
      const err = (await response.json().catch(() => null)) as { detail?: string } | null
      return {
        ok: false,
        message: err?.detail ?? 'Preferences update failed.',
      }
    }

    const preferences = (await response.json()) as UserPreferencesDTO
    applyDocumentUiTheme(preferences.ui_theme)
    return { ok: true, preferences }
  } catch {
    return { ok: false, message: 'Unable to reach auth service.' }
  }
}

async function requestPasswordReset(payload: ForgotPasswordPayload): Promise<PasswordResetResult> {
  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: payload.email.trim(),
      }),
    })

    if (!response.ok) {
      const err = (await response.json().catch(() => null)) as { detail?: unknown } | null
      return {
        ok: false,
        message: parseApiErrorDetail(err?.detail, 'Could not process password reset request.'),
      }
    }

    const body = (await response.json().catch(() => null)) as { message?: unknown } | null
    return {
      ok: true,
      message:
        typeof body?.message === 'string' && body.message.trim()
          ? body.message
          : 'If that email is in our system, a reset link has been sent.',
    }
  } catch {
    return {
      ok: false,
      message: 'Unable to reach auth service.',
    }
  }
}

async function confirmPasswordReset(payload: ResetPasswordPayload): Promise<PasswordResetResult> {
  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: payload.token,
        new_password: payload.newPassword,
      }),
    })

    if (!response.ok) {
      const err = (await response.json().catch(() => null)) as { detail?: unknown } | null
      return {
        ok: false,
        message: parseApiErrorDetail(err?.detail, 'Password reset failed.'),
      }
    }

    const body = (await response.json().catch(() => null)) as { message?: unknown } | null
    return {
      ok: true,
      message:
        typeof body?.message === 'string' && body.message.trim()
          ? body.message
          : 'Password has been reset successfully.',
    }
  } catch {
    return {
      ok: false,
      message: 'Unable to reach auth service.',
    }
  }
}

function saveCurrentUser(user: User | null) {
  if (!user) {
    localStorage.removeItem(CURRENT_USER_KEY)
    return
  }
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user))
}

function getCurrentUser(): User | null {
  const raw = localStorage.getItem(CURRENT_USER_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

// Takes a JWT token, attaches it to the HTTP headers as a Bearer token, and asks the backend for the current user's profile data
// If successful, it runs that data through the mapBackendUser function), saves the mapped user to localStorage, and returns it
async function fetchProfile(token: string): Promise<User | null> {
  const response = await fetch(`${AUTH_API_BASE_URL}/profile/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) return null

  const backendUser = (await response.json()) as BackendUser
  const mapped = mapBackendUser(backendUser)
  saveCurrentUser(mapped)

  const prefs = await fetchUserPreferences(token)
  if (prefs) applyDocumentUiTheme(prefs.ui_theme)

  return mapped
}

// login flow
async function login(payload: LoginPayload): Promise<AuthResult> {
  try {
    // OAuth2PasswordRequestForm expects x-www-form-urlencoded + "username"
    const form = new URLSearchParams()
    form.set('username', payload.email.trim())
    form.set('password', payload.password)

    const response = await fetch(`${AUTH_API_BASE_URL}/auth/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: form.toString(),
    })

    if (!response.ok) {
      return {
        ok: false,
        message: 'Invalid email or password.',
        user: null,
      }
    }

    const tokenBody = (await response.json()) as BackendToken
    saveToken(tokenBody.access_token)

    const user = await fetchProfile(tokenBody.access_token)
    if (!user) {
      logout()
      return {
        ok: false,
        message: 'Login succeeded but profile fetch failed.',
        user: null,
      }
    }

    return {
      ok: true,
      message: 'Login successful.',
      user,
    }
  } catch {
    return {
      ok: false,
      message: 'Unable to reach auth service.',
      user: null,
    }
  }
}

// register flow
async function register(payload: RegisterPayload): Promise<AuthResult> {
  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: payload.username, // backend expects "name"
        email: payload.email,
        role: 'user', // backend requires role - for now automatically hardcode to user
        password: payload.password,
      }),
    })

    if (!response.ok) {
      const err = (await response.json().catch(() => null)) as { detail?: unknown } | null
      return {
        ok: false,
        message: parseApiErrorDetail(err?.detail, 'Registration failed.'),
        user: null,
      }
    }

    // backend register returns user, not token -> auto-login
    return await login({
      email: payload.email,
      password: payload.password,
    })
  } catch {
    return {
      ok: false,
      message: 'Unable to reach auth service.',
      user: null,
    }
  }
}

// resume to restore the local session (Should be replaced with JWT?)
async function hydrateCurrentUser(): Promise<User | null> {
  const token = getToken()
  if (!token) return null

  const user = await fetchProfile(token)
  if (!user) logout()
  return user
}

export type FetchPublicProfileResult =
  | { ok: true; user: User }
  | { ok: false; status: number; message: string }

async function fetchPublicProfile(userId: number): Promise<FetchPublicProfileResult> {
  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/user/public/${userId}`)

    if (response.status === 404) {
      const err = (await response.json().catch(() => null)) as { detail?: string } | null
      return {
        ok: false,
        status: 404,
        message: err?.detail ?? 'User not found.',
      }
    }

    if (response.status === 401) {
      return { ok: false, status: 401, message: 'Session expired or invalid. Sign in again.' }
    }

    if (!response.ok) {
      return { ok: false, status: response.status, message: 'Failed to load profile.' }
    }

    const backendUser = (await response.json()) as BackendUser
    return { ok: true, user: mapBackendUser(backendUser) }
  } catch {
    return { ok: false, status: 0, message: 'Unable to reach auth service.' }
  }
}

// Keep compatibility with existing UI code that calls getAllUsers()
async function getAllUsers(): Promise<User[]> {
  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/users/public/`)
    if (!response.ok) return []
    const backendUsers = (await response.json()) as BackendUser[]
    return backendUsers.map(mapBackendUser)
  } catch {
    return []
  }
}

// Keep local profile update for now (backend endpoint currently expects full UserCreate)
async function updateCurrentUser(update: Pick<User, 'username' | 'bio'>): Promise<AuthResult> {
  const current = getCurrentUser()
  if (!current) {
    return {
      ok: false,
      message: 'No active user session.',
      user: null,
    }
  }

  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/user/profile/edit`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: update.username.trim(),
        bio: update.bio.trim(),
      }),
    })
    if (response.status === 401) {
      logout()
      return { ok: false, message: 'Session expired. Sign in again.', user: null }
    }
    if (!response.ok) {
      const err = (await response.json().catch(() => null)) as { detail?: string } | null
      return {
        ok: false,
        message: err?.detail ?? 'Profile update failed.',
        user: null,
      }
    }
    const backendUser = (await response.json()) as BackendUser
    const mapped = mapBackendUser(backendUser)
    const next: User = {
      ...current,
      id: mapped.id,
      username: mapped.username,
      email: mapped.email,
      isAdmin: mapped.isAdmin,
      bio: update.bio.trim(),
      avatar: mapped.avatar,
    }
    saveCurrentUser(next)
    return { ok: true, message: 'Profile saved.', user: next }
  } catch {
    return { ok: false, message: 'Unable to reach auth service.', user: null }
  }
}

async function uploadAvatar(file: File): Promise<AuthResult> {
  const token = getToken()
  if (!token) {
    return { ok: false, message: 'No active session.', user: null }
  }

  const current = getCurrentUser()
  if (!current) {
    return { ok: false, message: 'No active user session.', user: null }
  }

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(`${AUTH_API_BASE_URL}/user/profile/avatar`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    })

    if (response.status === 401) {
      logout()
      return { ok: false, message: 'Session expired. Sign in again.', user: null }
    }

    if (response.status === 400) {
      const err = (await response.json().catch(() => null)) as { detail?: string } | null
      return {
        ok: false,
        message: err?.detail ?? 'Invalid image. Use JPEG, PNG, or WebP under 5MB.',
        user: null,
      }
    }

    if (!response.ok) {
      const err = (await response.json().catch(() => null)) as { detail?: string } | null
      return {
        ok: false,
        message: err?.detail ?? 'Avatar upload failed.',
        user: null,
      }
    }

    const backendUser = (await response.json()) as BackendUser
    const mapped = mapBackendUser(backendUser)
    const next: User = {
      ...current,
      id: mapped.id,
      username: mapped.username,
      email: mapped.email,
      bio: mapped.bio,
      isAdmin: mapped.isAdmin,
      avatar: mapped.avatar,
    }
    saveCurrentUser(next)
    return { ok: true, message: 'Profile photo updated.', user: next }
  } catch {
    return { ok: false, message: 'Unable to reach auth service.', user: null }
  }
}

// logout 
function logout() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(CURRENT_USER_KEY)
}

// bundle all the functions into the authService object and exports it, so that other parts of React/Vue app can use them
export const authService = {
  login,
  register,
  hydrateCurrentUser,
  getCurrentUser,
  getToken,
  getAllUsers,
  fetchPublicProfile,
  updateCurrentUser,
  uploadAvatar,
  fetchUserPreferences,
  updateUserPreferences,
  requestPasswordReset,
  confirmPasswordReset,
  logout,
}
