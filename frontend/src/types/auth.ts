export interface UserNotification {
  id: string
  type: 'new_video' | 'subscription' | 'chat' | 'system'
  message: string
  timestamp: string
  read: boolean
  videoId?: string
}

export interface User {
  id: string
  username: string
  email: string
  bio: string
  avatar: string
  isAdmin: boolean
  subscribedTo: string[]
  notifications: UserNotification[]
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface ForgotPasswordPayload {
  email: string
}

export interface ResetPasswordPayload {
  token: string
  newPassword: string
}

export interface AuthResult {
  ok: boolean
  message: string
  user: User | null
}


// Define the shape of the JSON data FastAPI backend returns
export interface BackendUser { // mathches UserResponse
  id: number
  name: string
  email: string
  role: string
  is_active: boolean
  bio?: string | null
  avatar?: string | null
}

export interface BackendToken { // matches Token
  access_token: string
  token_type: string
}

/** Matches UserPreferencesResponse from user_prefs_and_accounts_service. */
export interface UserPreferencesDTO {
  user_id: number
  privacy: string
  notifications: boolean
  ui_theme: string
}

/** Matches UserPreferencesUpdate (PATCH body). */
export type UserPreferencesPatch = {
  privacy?: string
  notifications?: boolean
  ui_theme?: string
}

export type PreferencesUpdateResult =
  | { ok: true; preferences: UserPreferencesDTO }
  | { ok: false; message: string }

export type PasswordResetResult = {
  ok: boolean
  message: string
}
