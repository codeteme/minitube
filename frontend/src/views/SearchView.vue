<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import VideoCard from '@/components/VideoCard.vue'
import { searchVideos, searchUsers } from '@/services/dashboard'
import type { UserSearchResult } from '@/services/dashboard'
import type { VideoItem } from '@/types/video'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()
const videoResults = ref<VideoItem[]>([])
const userResults = ref<UserSearchResult[]>([])
const loading = ref(false)
const errorMessage = ref('')

const query = computed(() => String(route.query.q || '').trim())

async function loadResults(q: string) {
  if (!q) {
    videoResults.value = []
    userResults.value = []
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const userId = authStore.currentUser?.id
    const [videos, users] = await Promise.all([searchVideos(q, userId), searchUsers(q)])
    videoResults.value = videos
    userResults.value = users
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load results'
  } finally {
    loading.value = false
  }
}

onMounted(() => loadResults(query.value))
watch(query, loadResults)
</script>

<template>
  <main class="search-page">
    <header class="search-header">
      <h1><AppIcon name="search" :size="20" /> Search results for "{{ query }}"</h1>
      <p>{{ videoResults.length }} video{{ videoResults.length !== 1 ? 's' : '' }}, {{ userResults.length }} channel{{ userResults.length !== 1 ? 's' : '' }}</p>
    </header>

    <section v-if="loading" class="status-box">
      <p>Loading results…</p>
    </section>

    <template v-else-if="!errorMessage">
      <!-- Channels -->
      <section v-if="userResults.length > 0" class="results-section">
        <h2 class="section-title"><AppIcon name="users" :size="16" /> Channels</h2>
        <div class="channel-grid">
          <RouterLink
            v-for="user in userResults"
            :key="user.id"
            :to="`/users/${user.id}`"
            class="channel-card"
          >
            <div class="channel-avatar">{{ user.name.charAt(0).toUpperCase() }}</div>
            <div class="channel-info">
              <span class="channel-name">{{ user.name }}</span>
              <span v-if="user.role === 'admin'" class="channel-badge">Admin</span>
            </div>
          </RouterLink>
        </div>
      </section>

      <!-- Videos -->
      <section v-if="videoResults.length > 0" class="results-section">
        <h2 class="section-title"><AppIcon name="play" :size="16" /> Videos</h2>
        <div class="video-grid">
          <VideoCard v-for="video in videoResults" :key="video.id" :video="video" />
        </div>
      </section>

      <section v-if="videoResults.length === 0 && userResults.length === 0" class="empty-state">
        <AppIcon name="empty" :size="18" />
        <p>No results matched your search.</p>
      </section>
    </template>

    <section v-else class="status-box">
      <p>{{ errorMessage }}</p>
    </section>
  </main>
</template>

<style scoped>
.search-page {
  max-width: 1320px;
  margin: 0 auto;
  padding: 22px 16px 34px;
}

.search-header h1 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-main);
  font-size: 26px;
}

.search-header p {
  color: var(--text-muted);
}

.results-section {
  margin-top: 28px;
}

.section-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 14px;
}

.channel-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.channel-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--border-default);
  border-radius: 14px;
  background: var(--bg-1);
  text-decoration: none;
  color: var(--text-main);
  min-width: 180px;
  transition: background 0.15s;
}

.channel-card:hover {
  background: var(--overlay-hover-mid);
}

.channel-avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  color: var(--text-inverse);
  display: grid;
  place-items: center;
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
}

.channel-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.channel-name {
  font-weight: 600;
  font-size: 15px;
}

.channel-badge {
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
}

.status-box,
.empty-state {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 20px;
  border: 1px solid var(--border-default);
  border-radius: 14px;
  padding: 20px;
  color: var(--text-soft);
  background: var(--bg-1);
}
</style>
