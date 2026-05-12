<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/icons/AppIcon.vue'
import { connectNotificationStream, fetchNotifications } from '@/services/notifications'
import { fetchSearchSuggestions, fetchSearchHistory } from '@/services/dashboard'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const searchInput = ref('')
const suggestions = ref<string[]>([])
const historyItems = ref<string[]>([])
const showSuggestions = ref(false)
let suggestionsDebounce: ReturnType<typeof setTimeout> | null = null
const unreadNotificationCount = ref(0)
const unreadChatCount = ref(0)
let disconnectNotificationStream: (() => void) | null = null
let notificationStreamReconnectTimer: ReturnType<typeof setTimeout> | null = null
const notificationStreamUserId = ref<string | null>(null)
const notificationStreamShouldReconnect = ref(false)
let notificationFallbackPollTimer: ReturnType<typeof setInterval> | null = null

const HIDE_SEARCH_ROUTES = new Set(['login', 'register', 'reset-password'])
const showSearch = computed(() => !HIDE_SEARCH_ROUTES.has(String(route.name ?? '')))

async function refreshUnreadNotifications() {
  if (!authStore.currentUser) {
    unreadNotificationCount.value = 0
    unreadChatCount.value = 0
    return
  }

  try {
    const items = await fetchNotifications({
      userId: authStore.currentUser.id,
      unreadOnly: true,
      limit: 200,
      offset: 0,
    })
    unreadNotificationCount.value = items.length
    unreadChatCount.value = items.filter((item) => item.type === 'direct_message').length
  } catch {
    unreadNotificationCount.value = 0
    unreadChatCount.value = 0
  }
}

function handleNotificationsUpdated() {
  refreshUnreadNotifications()
}

function stopNotificationStream() {
  if (disconnectNotificationStream) {
    disconnectNotificationStream()
    disconnectNotificationStream = null
  }
  if (notificationStreamReconnectTimer) {
    clearTimeout(notificationStreamReconnectTimer)
    notificationStreamReconnectTimer = null
  }
  notificationStreamShouldReconnect.value = false
  notificationStreamUserId.value = null
  if (notificationFallbackPollTimer) {
    clearInterval(notificationFallbackPollTimer)
    notificationFallbackPollTimer = null
  }
}

function startNotificationStream(userId: string) {
  stopNotificationStream()
  notificationStreamUserId.value = userId
  notificationStreamShouldReconnect.value = true

  const connect = () => {
    if (!notificationStreamShouldReconnect.value || notificationStreamUserId.value !== userId) return

    disconnectNotificationStream = connectNotificationStream({
      userId,
      onNotification: () => {
        refreshUnreadNotifications()
        window.dispatchEvent(new CustomEvent('notifications-updated'))
      },
      onStatusChange: (status) => {
        if (status === 'error' || status === 'disconnected') {
          if (!notificationStreamShouldReconnect.value || notificationStreamUserId.value !== userId) return
          if (notificationStreamReconnectTimer) clearTimeout(notificationStreamReconnectTimer)
          notificationStreamReconnectTimer = setTimeout(connect, 1500)
        }
      },
    })
  }

  connect()

  // Fallback: keep unread badge in sync even if WS is blocked/intermittent.
  if (notificationFallbackPollTimer) {
    clearInterval(notificationFallbackPollTimer)
  }
  notificationFallbackPollTimer = setInterval(() => {
    if (authStore.currentUser?.id !== userId) return
    refreshUnreadNotifications()
  }, 7000)
}

onMounted(() => {
  authStore.hydrate()
  refreshUnreadNotifications()
  window.addEventListener('notifications-updated', handleNotificationsUpdated)
})

onUnmounted(() => {
  window.removeEventListener('notifications-updated', handleNotificationsUpdated)
  stopNotificationStream()
})

watch(
  () => authStore.currentUser?.id,
  (userId) => {
    refreshUnreadNotifications()
    if (!userId) {
      stopNotificationStream()
      return
    }
    startNotificationStream(userId)
  },
  { immediate: true },
)

function logout() {
  stopNotificationStream()
  authStore.logout()
  router.push('/login')
}

async function onSearchFocus() {
  if (searchInput.value.trim()) return
  if (!authStore.currentUser) return
  try {
    const history = await fetchSearchHistory(String(authStore.currentUser.id), 10)
    historyItems.value = history.map((h) => h.query)
    showSuggestions.value = historyItems.value.length > 0
  } catch {
    historyItems.value = []
  }
}

function onSearchInput() {
  const q = searchInput.value.trim()
  if (suggestionsDebounce) clearTimeout(suggestionsDebounce)
  if (!q) {
    suggestions.value = []
    // restore history view if available
    showSuggestions.value = historyItems.value.length > 0
    return
  }
  historyItems.value = []
  suggestionsDebounce = setTimeout(async () => {
    try {
      suggestions.value = await fetchSearchSuggestions(q)
      showSuggestions.value = suggestions.value.length > 0
    } catch {
      suggestions.value = []
      showSuggestions.value = false
    }
  }, 200)
}

function selectSuggestion(s: string) {
  searchInput.value = s
  showSuggestions.value = false
  router.push({ name: 'search', query: { q: s } })
}

function submitSearch() {
  const keyword = searchInput.value.trim()
  if (!keyword) return
  showSuggestions.value = false
  router.push({ name: 'search', query: { q: keyword } })
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink to="/" class="brand">
        <span class="brand-icon" aria-hidden="true"><AppIcon name="play" :size="14" :stroke-width="1.9" /></span>
        <span>Media Hub</span>
      </RouterLink>

      <form v-if="showSearch" class="searchbar" @submit.prevent="submitSearch">
        <div class="search-input-wrap">
          <input
            v-model="searchInput"
            type="text"
            placeholder="Search videos"
            autocomplete="off"
            @focus="onSearchFocus"
            @input="onSearchInput"
            @blur="showSuggestions = false"
          />
          <ul v-if="showSuggestions" class="suggestions-list">
            <li v-if="historyItems.length" class="suggestions-label">Recent</li>
            <li
              v-for="h in historyItems"
              :key="'h-' + h"
              class="suggestions-history-item"
              @mousedown.prevent="selectSuggestion(h)"
            >{{ h }}</li>
            <li v-if="suggestions.length" class="suggestions-label">Suggestions</li>
            <li
              v-for="s in suggestions"
              :key="'s-' + s"
              @mousedown.prevent="selectSuggestion(s)"
            >{{ s }}</li>
          </ul>
        </div>
        <button type="submit" class="search-btn"><AppIcon name="search" :size="16" /> Search</button>
      </form>

      <nav class="topnav">
        <RouterLink to="/"><AppIcon name="home" :size="16" /> Home</RouterLink>
        <RouterLink v-if="authStore.isAuthenticated" to="/upload"
          ><AppIcon name="upload" :size="16" /> Upload</RouterLink
        >
        <RouterLink v-if="authStore.isAuthenticated" to="/notifications" class="notify-link">
          <span class="nav-icon-wrap">
            <AppIcon name="bell" :size="16" />
            <span v-if="unreadNotificationCount > 0" class="nav-badge">
              {{ unreadNotificationCount > 99 ? '99+' : unreadNotificationCount }}
            </span>
          </span>
          Notifications
        </RouterLink>
        <RouterLink v-if="authStore.isAuthenticated" to="/chat" class="chat-link">
          <span class="nav-icon-wrap">
            <AppIcon name="users" :size="16" />
            <span v-if="unreadChatCount > 0" class="nav-badge">
              {{ unreadChatCount > 99 ? '99+' : unreadChatCount }}
            </span>
          </span>
          Chat
        </RouterLink>
        <RouterLink v-if="!authStore.isAuthenticated" to="/login"
          ><AppIcon name="login" :size="16" /> Login</RouterLink
        >
        <RouterLink v-if="!authStore.isAuthenticated" to="/register"
          ><AppIcon name="register" :size="16" /> Register</RouterLink
        >
        <RouterLink v-if="authStore.isAuthenticated" to="/profile"
          ><AppIcon name="user" :size="16" /> Profile</RouterLink
        >
        <RouterLink
          v-if="authStore.isAuthenticated && authStore.currentUser?.isAdmin"
          to="/admin"
          ><AppIcon name="admin" :size="16" /> Admin</RouterLink
        >
        <button v-if="authStore.isAuthenticated" class="logout-btn" @click="logout">
          <AppIcon name="logout" :size="16" /> Logout
        </button>
      </nav>
    </header>

    <RouterView />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 5;
  height: 68px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(8px);
  background: var(--topbar-bg);
  border-bottom: 1px solid var(--border-default);
}

.searchbar {
  flex: 1;
  max-width: 640px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  margin: 0 16px;
}

.search-input-wrap {
  position: relative;
}

.searchbar input {
  width: 100%;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--bg-3);
  color: var(--text-main);
  padding: 9px 14px;
}

.suggestions-list {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--bg-1);
  border: 1px solid var(--border-medium);
  border-radius: 12px;
  list-style: none;
  margin: 0;
  padding: 4px 0;
  z-index: 20;
  box-shadow: var(--shadow-dropdown);
}

.suggestions-list li {
  padding: 8px 14px;
  color: var(--text-subtle);
  font-size: 14px;
  cursor: pointer;
}

.suggestions-list li:hover {
  background: var(--overlay-hover);
  color: var(--text-main);
}

.suggestions-label {
  padding: 6px 14px 2px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-faint, #888);
  cursor: default;
  pointer-events: none;
}

.suggestions-label:hover {
  background: none;
  color: var(--text-faint, #888);
}

.suggestions-history-item {
  padding-left: 28px;
}

.searchbar button {
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--surface-raised);
  color: var(--text-main);
  padding: 9px 14px;
  cursor: pointer;
}

.search-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  color: var(--text-main);
  text-decoration: none;
  letter-spacing: 0.03em;
  font-weight: 700;
}

.brand-icon {
  width: 26px;
  height: 26px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-size: 11px;
  color: var(--text-inverse);
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
}

.topnav {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topnav a {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-subtle);
  text-decoration: none;
  font-size: 14px;
  padding: 8px 10px;
  border-radius: 8px;
}

.nav-icon-wrap {
  position: relative;
  display: inline-flex;
}

.nav-badge {
  position: absolute;
  right: -10px;
  top: -9px;
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  padding: 0 5px;
  font-size: 11px;
  display: grid;
  place-items: center;
  background: var(--accent-soft);
  color: var(--text-inverse);
  border: 1px solid rgba(0, 0, 0, 0.45);
}

.topnav a.router-link-exact-active,
.topnav a:hover {
  background: var(--overlay-hover-mid);
  color: var(--text-main);
}

.logout-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--border-extra);
  background: transparent;
  color: var(--text-main);
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
}

@media (max-width: 740px) {
  .topbar {
    height: auto;
    padding: 12px;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .searchbar {
    width: 100%;
    max-width: none;
    margin: 0;
  }

  .topnav {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
