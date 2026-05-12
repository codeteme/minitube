<script setup lang="ts">
import { computed, onMounted, reactive, ref, watchEffect } from 'vue'
import VideoCard from '@/components/VideoCard.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { authService, applyDocumentUiTheme } from '@/services/auth'
import { fetchVideos } from '@/services/videos'
import { fetchSubscriptionsFeed, fetchChannelSubscriberIds } from '@/services/dashboard'
import type { VideoItem } from '@/types/video'
import type { User, UserPreferencesDTO } from '@/types/auth'

const authStore = useAuthStore()
const tab = ref<'videos' | 'subscriptions' | 'subscribers'>('videos')
const editMode = ref(false)
const message = ref('')
const loadingVideos = ref(false)
const videoError = ref('')
const loadingSubscriptions = ref(false)
const subscriptionsError = ref('')
const allVideos = ref<VideoItem[]>([])
const subscriptionVideos = ref<VideoItem[]>([])
const subscribers = ref<User[]>([])
const loadingSubscribers = ref(false)
const subscribersError = ref('')

const form = reactive({
  username: '',
  bio: '',
})

const fileInputRef = ref<HTMLInputElement | null>(null)
const avatarUploading = ref(false)
const avatarCacheBust = ref(0)

const prefsLoading = ref(false)
const prefsSavingPrivacy = ref(false)
const prefsSavingNotifications = ref(false)
const prefsSavingUi = ref(false)
const prefsMessage = ref('')

const prefs = reactive({
  privacy: 'public' as 'public' | 'private',
  notifications: true,
  ui_theme: 'dark' as 'dark' | 'light',
})

function avatarDisplayUrl(): string {
  const u = authStore.currentUser?.avatar
  if (!u) return ''
  const sep = u.includes('?') ? '&' : '?'
  return avatarCacheBust.value ? `${u}${sep}t=${avatarCacheBust.value}` : u
}

function openAvatarPicker() {
  fileInputRef.value?.click()
}

async function onAvatarFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  avatarUploading.value = true
  message.value = ''
  const result = await authStore.uploadProfileAvatar(file)
  avatarUploading.value = false

  if (!result.ok) {
    message.value = result.message
    return
  }

  avatarCacheBust.value = Date.now()
  message.value = result.message
}

watchEffect(() => {
  if (!authStore.currentUser) return
  form.username = authStore.currentUser.username
  form.bio = authStore.currentUser.bio
})

const userVideos = computed(() => {
  if (!authStore.currentUser) return []
  return allVideos.value.filter((video) => video.authorId === authStore.currentUser?.id)
})

async function loadVideos() {
  loadingVideos.value = true
  videoError.value = ''

  try {
    allVideos.value = await fetchVideos()
  } catch (error) {
    videoError.value = error instanceof Error ? error.message : 'Failed to load videos.'
  } finally {
    loadingVideos.value = false
  }
}

async function loadSubscriptionsFeed() {
  if (!authStore.currentUser) return

  loadingSubscriptions.value = true
  subscriptionsError.value = ''

  try {
    subscriptionVideos.value = await fetchSubscriptionsFeed(authStore.currentUser.id, 20)
  } catch (error) {
    subscriptionsError.value = error instanceof Error ? error.message : 'Failed to load subscriptions feed.'
  } finally {
    loadingSubscriptions.value = false
  }
}

async function saveProfile() {
  message.value = ''
  const result = await authStore.updateProfile({ username: form.username, bio: form.bio })
  if (!result.ok) {
    message.value = result.message
    return
  }

  editMode.value = false
  message.value = result.message
}

function applyPrefsFromServer(p: UserPreferencesDTO) {
  prefs.privacy = p.privacy === 'private' ? 'private' : 'public'
  prefs.notifications = p.notifications
  prefs.ui_theme = p.ui_theme === 'light' ? 'light' : 'dark'
  applyDocumentUiTheme(prefs.ui_theme)
}

async function loadPreferences() {
  prefsLoading.value = true
  prefsMessage.value = ''
  const p = await authService.fetchUserPreferences()
  prefsLoading.value = false
  if (!p) {
    prefsMessage.value = 'Could not load preferences.'
    return
  }
  applyPrefsFromServer(p)
}

async function savePrivacySettings() {
  prefsSavingPrivacy.value = true
  prefsMessage.value = ''
  const result = await authService.updateUserPreferences({ privacy: prefs.privacy })
  prefsSavingPrivacy.value = false
  if (!result.ok) {
    prefsMessage.value = result.message
    return
  }
  applyPrefsFromServer(result.preferences)
  prefsMessage.value = 'Privacy settings saved.'
}

async function saveNotificationSettings() {
  prefsSavingNotifications.value = true
  prefsMessage.value = ''
  const result = await authService.updateUserPreferences({ notifications: prefs.notifications })
  prefsSavingNotifications.value = false
  if (!result.ok) {
    prefsMessage.value = result.message
    return
  }
  applyPrefsFromServer(result.preferences)
  prefsMessage.value = 'Notification preferences saved.'
}

async function saveUiSettings() {
  prefsSavingUi.value = true
  prefsMessage.value = ''
  const result = await authService.updateUserPreferences({ ui_theme: prefs.ui_theme })
  prefsSavingUi.value = false
  if (!result.ok) {
    prefsMessage.value = result.message
    return
  }
  applyPrefsFromServer(result.preferences)
  prefsMessage.value = 'Appearance saved.'
}

async function loadSubscribers() {
  if (!authStore.currentUser) return

  loadingSubscribers.value = true
  subscribersError.value = ''

  try {
    const subscriberIds = await fetchChannelSubscriberIds(authStore.currentUser.id)
    if (subscriberIds.length === 0) {
      subscribers.value = []
      return
    }
    const allUsers = await authService.getAllUsers()
    const idSet = new Set(subscriberIds)
    subscribers.value = allUsers.filter((u) => idSet.has(u.id))
  } catch (error) {
    subscribersError.value = error instanceof Error ? error.message : 'Failed to load subscribers.'
  } finally {
    loadingSubscribers.value = false
  }
}

onMounted(() => {
  loadVideos()
  loadSubscriptionsFeed()
  loadPreferences()
  loadSubscribers()
})
</script>

<template>
  <main v-if="authStore.currentUser" class="profile-page">
    <section class="profile-header">
      <div class="avatar-wrap">
        <img :src="avatarDisplayUrl()" :alt="authStore.currentUser.username" class="avatar" />
        <input
          ref="fileInputRef"
          type="file"
          class="sr-only"
          accept="image/jpeg,image/png,image/webp"
          @change="onAvatarFileChange"
        />
        <button
          type="button"
          class="avatar-upload ghost"
          :disabled="avatarUploading"
          @click="openAvatarPicker"
        >
          <AppIcon name="user" :size="14" />
          {{ avatarUploading ? 'Uploading…' : 'Change photo' }}
        </button>
      </div>

      <div class="header-main">
        <h1>{{ authStore.currentUser.username }}</h1>
        <p class="email">{{ authStore.currentUser.email }}</p>
        <p class="bio">{{ authStore.currentUser.bio || 'No bio yet.' }}</p>

        <div class="stats">
          <span><AppIcon name="video" :size="14" /> {{ userVideos.length }} videos</span>
          <span
            ><AppIcon name="users" :size="14" />
            {{ authStore.currentUser.subscribedTo.length }} subscriptions</span
          >
          <span
            ><AppIcon name="users" :size="14" />
            {{ subscribers.length }} subscribers</span
          >
          <span
            ><AppIcon name="bell" :size="14" />
            {{ prefs.notifications ? 'Push-style alerts enabled' : 'Notifications muted in preferences' }}</span
          >
        </div>
      </div>
    </section>

    <section class="editor">
      <header>
        <h2>Profile settings</h2>
        <button v-if="!editMode" class="ghost" @click="editMode = true">
          <AppIcon name="user" :size="14" /> Edit profile
        </button>
      </header>

      <div v-if="editMode" class="form-grid">
        <label>
          Username
          <input v-model="form.username" type="text" />
        </label>

        <label>
          Bio
          <textarea v-model="form.bio" rows="3"></textarea>
        </label>

        <div class="actions">
          <button @click="saveProfile"><AppIcon name="check" :size="14" /> Save</button>
          <button class="ghost" @click="editMode = false"><AppIcon name="logout" :size="14" /> Cancel</button>
        </div>
      </div>
    </section>

    <section class="preferences">
      <header>
        <h2>Privacy</h2>
        <p class="prefs-hint">Control whether your profile is visible to other signed-in users.</p>
      </header>

      <p v-if="prefsLoading" class="muted">Loading preferences…</p>
      <div v-else class="prefs-grid">
        <label class="prefs-field">
          Profile visibility
          <select v-model="prefs.privacy" class="prefs-select">
            <option value="public">Public — others can open your profile</option>
            <option value="private">Private — others see “User not found”</option>
          </select>
        </label>
        <div class="prefs-actions">
          <button type="button" :disabled="prefsSavingPrivacy" @click="savePrivacySettings">
            <AppIcon name="check" :size="14" />
            {{ prefsSavingPrivacy ? 'Saving…' : 'Save privacy' }}
          </button>
        </div>
      </div>
    </section>

    <section class="preferences">
      <header>
        <h2>Notifications</h2>
        <p class="prefs-hint">Stored on your account; product notifications may still respect this flag as services adopt it.</p>
      </header>

      <p v-if="prefsLoading" class="muted">Loading preferences…</p>
      <div v-else class="prefs-grid prefs-notifications">
        <label class="toggle-row">
          <input v-model="prefs.notifications" type="checkbox" class="prefs-checkbox" />
          <span>Enable Notification Preferences</span>
        </label>
        <div class="prefs-actions">
          <button type="button" :disabled="prefsSavingNotifications" @click="saveNotificationSettings">
            <AppIcon name="bell" :size="14" />
            {{ prefsSavingNotifications ? 'Saving…' : 'Save notifications' }}
          </button>
        </div>
      </div>
    </section>

    <section class="preferences">
      <header>
        <h2>Appearance</h2>
        <p class="prefs-hint">Choose light or dark UI. This applies across the app after you save.</p>
      </header>

      <p v-if="prefsLoading" class="muted">Loading preferences…</p>
      <div v-else class="prefs-grid">
        <label class="prefs-field">
          Theme
          <select v-model="prefs.ui_theme" class="prefs-select">
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>
        <div class="prefs-actions">
          <button type="button" :disabled="prefsSavingUi" @click="saveUiSettings">
            <AppIcon name="check" :size="14" />
            {{ prefsSavingUi ? 'Saving…' : 'Save appearance' }}
          </button>
        </div>
      </div>
    </section>

    <section class="tabs">
      <button :class="{ active: tab === 'videos' }" @click="tab = 'videos'">
        <AppIcon name="video" :size="14" /> My videos
      </button>
      <button :class="{ active: tab === 'subscriptions' }" @click="tab = 'subscriptions'">
        <AppIcon name="users" :size="14" /> Subscriptions
      </button>
      <RouterLink to="/notifications" class="notifications-link">
        <AppIcon name="bell" :size="14" /> Notifications
      </RouterLink>
    </section>

    <section v-if="tab === 'videos'" class="video-grid">
      <p v-if="loadingVideos" class="muted">Loading videos...</p>
      <p v-else-if="videoError" class="muted">{{ videoError }}</p>
      <VideoCard v-for="video in userVideos" :key="video.id" :video="video" />
      <p v-if="!loadingVideos && !videoError && userVideos.length === 0" class="muted">No videos uploaded yet.</p>
    </section>

    <section v-if="tab === 'subscriptions'" class="video-grid">
      <p v-if="loadingSubscriptions" class="muted">Loading subscriptions feed...</p>
      <p v-else-if="subscriptionsError" class="muted">{{ subscriptionsError }}</p>
      <VideoCard v-for="video in subscriptionVideos" :key="video.id" :video="video" />
      <p v-if="!loadingSubscriptions && !subscriptionsError && subscriptionVideos.length === 0" class="muted">No videos from subscriptions yet.</p>
    </section>

    <section v-if="tab === 'subscribers'" class="subscriber-grid">
      <p v-if="loadingSubscribers" class="muted">Loading subscribers...</p>
      <p v-else-if="subscribersError" class="muted">{{ subscribersError }}</p>
      <RouterLink
        v-for="sub in subscribers"
        :key="sub.id"
        :to="`/users/${sub.id}`"
        class="subscriber-card"
      >
        <img :src="sub.avatar" :alt="sub.username" class="sub-avatar" />
        <span class="sub-name">{{ sub.username }}</span>
      </RouterLink>
      <p v-if="!loadingSubscribers && !subscribersError && subscribers.length === 0" class="muted">No subscribers yet.</p>
    </section>

    <p v-if="message" class="ok">{{ message }}</p>
    <p v-if="prefsMessage" class="ok prefs-toast">{{ prefsMessage }}</p>
  </main>
</template>

<style scoped>
.profile-page {
  max-width: 1320px;
  margin: 0 auto;
  padding: 22px 16px 34px;
}

.profile-header,
.editor,
.preferences,
.notification-item {
  border-radius: 14px;
  border: 1px solid var(--border-default);
  background: var(--bg-1);
}

.profile-header {
  padding: 16px;
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 14px;
}

.avatar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.avatar-upload {
  font-size: 12px;
  padding: 6px 10px;
}

.avatar {
  width: 110px;
  height: 110px;
  border-radius: 999px;
  object-fit: cover;
}

h1 {
  color: var(--text-main);
  font-size: 28px;
}

.email,
.bio {
  color: var(--text-soft);
}

.stats {
  margin-top: 8px;
  color: var(--text-body);
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 14px;
}

.editor {
  margin-top: 12px;
  padding: 14px;
}

.preferences {
  margin-top: 12px;
  padding: 14px;
}

.preferences header {
  margin-bottom: 10px;
}

.preferences h2 {
  color: var(--text-main);
  font-size: 18px;
}

.prefs-hint {
  color: var(--text-muted);
  font-size: 13px;
  margin-top: 4px;
}

.prefs-grid {
  display: grid;
  gap: 12px;
}

.prefs-field {
  display: grid;
  gap: 6px;
  color: var(--text-body);
  font-size: 14px;
}

.prefs-notifications .toggle-row {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-body);
  font-size: 14px;
  cursor: pointer;
}

.prefs-checkbox {
  width: 18px;
  height: 18px;
  accent-color: var(--accent-soft);
}

.prefs-select {
  max-width: 420px;
  background: var(--bg-0);
  border: 1px solid var(--border-strong);
  color: var(--text-main);
  border-radius: 9px;
  padding: 9px 11px;
  color-scheme: inherit;
}

.prefs-select option {
  background-color: var(--bg-0);
  color: var(--text-main);
}

.prefs-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.prefs-toast {
  margin-top: 8px;
}

.editor header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.editor h2 {
  color: var(--text-main);
  font-size: 18px;
}

.form-grid {
  margin-top: 10px;
  display: grid;
  gap: 10px;
}

label {
  display: grid;
  gap: 6px;
  color: var(--text-body);
  font-size: 14px;
}

input,
textarea {
  background: var(--bg-0);
  border: 1px solid var(--border-strong);
  color: var(--text-main);
  border-radius: 9px;
  padding: 9px 11px;
  color-scheme: inherit;
}

input:disabled,
textarea:disabled,
select:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  color: var(--text-body);
}

.actions {
  display: flex;
  gap: 8px;
}

button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  border-radius: 9px;
  padding: 8px 12px;
  color: var(--text-inverse);
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
}

button.ghost {
  border: 1px solid var(--border-heavy);
  background: transparent;
  color: var(--text-main);
}

button:disabled,
button.ghost:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  color: var(--text-subtle);
}

button:disabled:not(.ghost) {
  color: var(--text-inverse);
}

.tabs {
  margin-top: 14px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tabs button {
  background: var(--bg-5);
  border: 1px solid var(--border-medium);
  color: var(--text-subtle);
}

.tabs button.active {
  background: var(--accent-wash-hover);
  border-color: var(--accent-outline-soft);
  color: var(--text-main);
}

.notifications-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  border: 1px solid var(--border-medium);
  border-radius: 9px;
  color: var(--text-body);
  padding: 8px 12px;
  background: var(--bg-5);
}

.notifications-link:hover {
  border-color: var(--accent-outline-soft);
  background: var(--accent-wash);
  color: var(--text-main);
}

.video-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.subscriber-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}

.subscriber-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: var(--bg-1);
  text-decoration: none;
  color: var(--text-body);
  transition: background 0.15s, border-color 0.15s;
}

.subscriber-card:hover {
  background: var(--accent-wash);
  border-color: var(--accent-outline-soft);
  color: var(--text-main);
}

.sub-avatar {
  width: 64px;
  height: 64px;
  border-radius: 999px;
  object-fit: cover;
}

.sub-name {
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  word-break: break-word;
}

.muted {
  color: var(--text-muted);
}

.ok {
  margin-top: 10px;
  color: var(--ok-text);
}

@media (max-width: 760px) {
  .profile-header {
    grid-template-columns: 1fr;
  }
}
</style>
