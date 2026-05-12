<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/icons/AppIcon.vue'
import { fetchWatchedHistory, type WatchedVideo } from '@/services/dashboard'

const authStore = useAuthStore()
const router = useRouter()
const loading = ref(false)
const errorMessage = ref('')
const watchedVideos = ref<WatchedVideo[]>([])
const limit = ref(20)
const offset = ref(0)

async function loadWatchHistory() {
  if (!authStore.currentUser) return

  loading.value = true
  errorMessage.value = ''

  try {
    watchedVideos.value = await fetchWatchedHistory(authStore.currentUser.id, limit.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load watch history.'
  } finally {
    loading.value = false
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  return date.toLocaleDateString()
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }
  return `${minutes}:${String(secs).padStart(2, '0')}`
}

function openVideo(videoId: string, positionSeconds: number) {
  router.push({
    name: 'video-player',
    params: { id: videoId },
    query: { startPosition: positionSeconds },
  })
}

onMounted(() => {
  loadWatchHistory()
})
</script>

<template>
  <main class="watch-history-page">
    <section class="history-shell">
      <header class="history-header">
        <div>
          <h1><AppIcon name="clock" :size="18" /> Watch History</h1>
          <p>Videos you've watched recently.</p>
        </div>

        <div class="header-actions">
          <button class="ghost" @click="loadWatchHistory">
            <AppIcon name="upload" :size="14" /> Refresh
          </button>
        </div>
      </header>

      <section v-if="loading" class="status-box">
        <AppIcon name="play" :size="16" />
        Loading watch history...
      </section>

      <section v-else-if="errorMessage" class="status-box error-box">
        <p>{{ errorMessage }}</p>
        <button class="ghost" @click="loadWatchHistory">Retry</button>
      </section>

      <section v-else-if="watchedVideos.length === 0" class="status-box">
        <AppIcon name="empty" :size="18" />
        <p>No watch history yet. Start watching videos!</p>
      </section>

      <section v-else class="video-grid">
        <article
          v-for="video in watchedVideos"
          :key="video.id"
          class="video-card"
        >
          <div class="card-thumbnail">
            <img
              :src="video.thumbnail"
              :alt="video.title"
              class="thumbnail-image"
            />
            <div class="position-bar">
              <div
                class="position-fill"
                :style="{ width: `${((Number(video.lastPositionSeconds) || 0) / Math.max(Number(video.duration) || 1, 1)) * 100}%` }"
              />
            </div>
            <div class="position-label">
              {{ formatDuration(Number(video.lastPositionSeconds) || 0) }} / {{ formatDuration(Math.max(Number(video.duration) || 0, 0)) }}
            </div>
          </div>

          <div class="card-content">
            <h3 class="video-title">{{ video.title }}</h3>
            <p class="channel-name">{{ video.authorName }}</p>
            <p class="last-watched">
              <AppIcon name="clock" :size="12" />
              Watched {{ formatDate(video.lastWatchedAt) }}
            </p>
          </div>

          <div class="card-actions">
            <button
              class="continue-btn"
              @click="openVideo(video.id, video.lastPositionSeconds)"
            >
              <AppIcon name="play" :size="14" />
              Continue
            </button>
          </div>
        </article>
      </section>
    </section>
  </main>
</template>

<style scoped>
.watch-history-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px 16px 34px;
}

.history-shell {
  border: 1px solid var(--border-default);
  border-radius: 16px;
  background: var(--bg-6);
  padding: 14px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.history-header h1 {
  color: var(--text-main);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 24px;
}

.history-header p {
  color: var(--text-muted);
  margin-top: 4px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  border-radius: 9px;
  padding: 8px 11px;
  color: var(--text-inverse);
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

button:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

button.ghost {
  border: 1px solid var(--border-heavy);
  background: transparent;
}

button.ghost:hover:not(:disabled) {
  border-color: var(--accent-outline-soft);
  background: var(--accent-wash-hover);
}

.status-box {
  border: 1px dashed var(--border-strong);
  border-radius: 12px;
  color: var(--text-subtle);
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
  min-height: 120px;
  justify-content: center;
}

.error-box {
  justify-content: flex-start;
  flex-direction: column;
}

.error-box p {
  margin-bottom: 12px;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.video-card {
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-7);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: border-color 120ms ease, transform 120ms ease;
}

.video-card:hover {
  border-color: var(--accent-outline);
  transform: translateY(-2px);
}

.card-thumbnail {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--bg-8);
  overflow: hidden;
}

.thumbnail-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.position-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: var(--border-default);
}

.position-fill {
  height: 100%;
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  transition: width 300ms ease;
}

.position-label {
  position: absolute;
  bottom: 6px;
  right: 6px;
  font-size: 11px;
  color: var(--text-main);
  background: rgba(0, 0, 0, 0.6);
  padding: 2px 6px;
  border-radius: 4px;
}

.card-content {
  padding: 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.video-title {
  color: var(--text-main);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.channel-name {
  color: var(--text-muted);
  font-size: 13px;
  margin: 4px 0 0;
}

.last-watched {
  color: var(--text-faint);
  font-size: 12px;
  margin-top: auto;
  padding-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.card-actions {
  padding: 0 12px 12px;
  display: flex;
  gap: 8px;
}

.continue-btn {
  flex: 1;
  padding: 8px 12px;
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  color: var(--text-inverse);
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.continue-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

@media (max-width: 820px) {
  .history-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    width: 100%;
  }

  .video-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
  }
}
</style>
