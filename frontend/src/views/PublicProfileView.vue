<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import { authService } from '@/services/auth'
import { subscribeToChannel, unsubscribeFromChannel } from '@/services/dashboard'
import VideoCard from '@/components/VideoCard.vue'
import { fetchVideosByUploader } from '@/services/videos'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types/auth'
import type { VideoItem } from '@/types/video'

const route = useRoute()
const authStore = useAuthStore()

const loading = ref(true)
const errorMessage = ref('')
const actionMessage = ref('')
const subscribeLoading = ref(false)
const profileUser = ref<User | null>(null)
const uploadedVideos = ref<VideoItem[]>([])

const numericUserId = computed(() => {
  const raw = route.params.userId
  const s = Array.isArray(raw) ? raw[0] : raw
  const n = Number.parseInt(String(s), 10)
  return Number.isFinite(n) ? n : NaN
})

const isOwnProfile = computed(() => {
  if (!authStore.currentUser || !profileUser.value) return false
  return authStore.currentUser.id === profileUser.value.id
})

const isSubscribed = computed(() => {
  if (!authStore.currentUser || !profileUser.value) return false
  return authStore.currentUser.subscribedTo.includes(profileUser.value.id)
})

const chatRoute = computed(() => {
  if (!profileUser.value) return { name: 'chat' as const }
  return { name: 'chat' as const, query: { peer: profileUser.value.id } }
})

async function loadProfile() {
  loading.value = true
  errorMessage.value = ''
  actionMessage.value = ''
  profileUser.value = null
  uploadedVideos.value = []

  const id = numericUserId.value
  if (Number.isNaN(id)) {
    loading.value = false
    errorMessage.value = 'Invalid user id in the URL.'
    return
  }

  const [result, videos] = await Promise.all([
    authService.fetchPublicProfile(id),
    fetchVideosByUploader(String(id)),
  ])
  loading.value = false

  if (result.ok) {
    profileUser.value = result.user
    uploadedVideos.value = videos
    return
  }

  errorMessage.value = result.message
}

async function toggleSubscription() {
  if (!authStore.currentUser || !profileUser.value || isOwnProfile.value) return

  subscribeLoading.value = true
  actionMessage.value = ''
  const currentUserId = authStore.currentUser.id
  const targetUserId = profileUser.value.id

  try {
    if (isSubscribed.value) {
      await unsubscribeFromChannel(currentUserId, targetUserId)
      if (authStore.currentUser) {
        authStore.currentUser.subscribedTo = authStore.currentUser.subscribedTo.filter((id) => id !== targetUserId)
      }
    } else {
      await subscribeToChannel(currentUserId, targetUserId)
      if (authStore.currentUser && !authStore.currentUser.subscribedTo.includes(targetUserId)) {
        authStore.currentUser.subscribedTo = [...authStore.currentUser.subscribedTo, targetUserId]
      }
    }
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : 'Subscription update failed.'
  } finally {
    subscribeLoading.value = false
  }
}

onMounted(loadProfile)

watch(
  () => route.params.userId,
  () => {
    loadProfile()
  },
)
</script>

<template>
  <main class="public-profile-page">
    <nav class="back-nav">
      <RouterLink to="/" class="back-link">
        <AppIcon name="home" :size="14" /> Home
      </RouterLink>
      <RouterLink v-if="authStore.currentUser" to="/profile" class="back-link">
        <AppIcon name="user" :size="14" /> My profile
      </RouterLink>
    </nav>

    <p v-if="loading" class="muted">Loading profile…</p>

    <p v-else-if="errorMessage" class="error">{{ errorMessage }}</p>

    <section v-else-if="profileUser" class="profile-card">
      <img :src="profileUser.avatar" :alt="profileUser.username" class="avatar" />

      <div class="header-main">
        <div class="title-row">
          <h1>{{ profileUser.username }}</h1>
          <span v-if="profileUser.isAdmin" class="badge admin">Admin</span>
          <span v-else class="badge">Member</span>
        </div>

        <p class="email">{{ profileUser.email }}</p>

        <p v-if="isOwnProfile" class="own-hint">
          <AppIcon name="user" :size="14" /> This is your account.
          <RouterLink to="/profile" class="inline-link">Open full profile</RouterLink>
        </p>
        <p v-else-if="authStore.currentUser && !isSubscribed" class="chat-hint">
          You can send one message even without subscribing. Subscribe to unlock full two-way chat.
        </p>

        <div class="stats">
          <span><AppIcon name="users" :size="14" /> User id {{ profileUser.id }}</span>
          <span><AppIcon name="video" :size="14" /> {{ uploadedVideos.length }} uploads</span>
        </div>

        <div class="actions" v-if="authStore.currentUser && !isOwnProfile">
          <button type="button" class="subscribe-btn" :disabled="subscribeLoading" @click="toggleSubscription">
            <AppIcon name="users" :size="14" />
            {{ subscribeLoading ? 'Updating...' : isSubscribed ? 'Unsubscribe' : 'Subscribe' }}
          </button>
          <RouterLink :to="chatRoute" class="chat-btn">
            <AppIcon name="users" :size="14" /> Chat
          </RouterLink>
        </div>
        <p v-if="actionMessage" class="error action-error">{{ actionMessage }}</p>
      </div>
    </section>

    <section v-if="profileUser" class="uploads-section">
      <div class="section-head">
        <h2><AppIcon name="video" :size="16" /> Uploaded videos</h2>
      </div>

      <p v-if="uploadedVideos.length === 0" class="muted">
        {{ profileUser.username }} has not uploaded any videos yet.
      </p>

      <div v-else class="uploads-grid">
        <VideoCard v-for="video in uploadedVideos" :key="video.id" :video="video" />
      </div>
    </section>
  </main>
</template>

<style scoped>
.public-profile-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 22px 16px 34px;
}

.back-nav {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.back-link {
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

.back-link:hover {
  border-color: var(--accent-outline-soft);
  background: var(--accent-wash);
  color: var(--text-main);
}

.profile-card {
  border-radius: 14px;
  border: 1px solid var(--border-default);
  background: var(--bg-1);
  padding: 16px;
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 14px;
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
  margin: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.badge {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--border-faint);
  color: var(--text-soft);
  border: 1px solid var(--border-default);
}

.badge.admin {
  background: var(--accent-wash-hover);
  border-color: var(--accent-outline);
  color: var(--accent-text-soft);
}

.email {
  color: var(--text-soft);
  margin: 6px 0 0;
}

.own-hint {
  margin-top: 10px;
  color: var(--ok-text);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 14px;
}

.inline-link {
  color: var(--ok-text-strong);
}

.stats {
  margin-top: 12px;
  color: var(--text-body);
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 14px;
}

.actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.subscribe-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--border-medium);
  border-radius: 9px;
  color: var(--text-body);
  padding: 8px 12px;
  background: var(--bg-5);
  cursor: pointer;
}

.subscribe-btn:hover {
  border-color: var(--accent-outline-soft);
  background: var(--accent-wash);
  color: var(--text-main);
}

.subscribe-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-btn {
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

.chat-btn:hover {
  border-color: var(--accent-outline-soft);
  background: var(--accent-wash);
  color: var(--text-main);
}

.chat-hint {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 14px;
}

.action-error {
  margin-top: 10px;
}

.uploads-section {
  margin-top: 20px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-head h2 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-main);
  font-size: 20px;
  margin: 0;
}

.uploads-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
}

.muted {
  color: var(--text-muted);
}

.error {
  color: var(--accent-text-soft);
}

@media (max-width: 560px) {
  .profile-card {
    grid-template-columns: 1fr;
    justify-items: center;
    text-align: center;
  }

  .title-row {
    justify-content: center;
  }

  .own-hint {
    justify-content: center;
  }

  .stats {
    justify-content: center;
  }
}
</style>
