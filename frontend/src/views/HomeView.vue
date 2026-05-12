<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { VideoItem } from '@/types/video'
import VideoCard from '@/components/VideoCard.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import { fetchRecommended } from '@/services/dashboard'
import { useAuthStore } from '@/stores/auth'

const activeCategory = ref('All')
const showFilterPanel = ref(false)
const sortBy = ref<'recommended' | 'latest' | 'popular'>('recommended')
const loading = ref(false)
const errorMessage = ref('')
const videos = ref<VideoItem[]>([])
const authStore = useAuthStore()

const categories = computed(() => {
  const unique = new Set(videos.value.map((video) => video.category).filter(Boolean))
  return ['All', ...Array.from(unique).sort((a, b) => a.localeCompare(b))]
})

const filteredVideos = computed(() => {
  if (activeCategory.value === 'All') return videos.value
  return videos.value.filter((video) => video.category === activeCategory.value)
})

const displayVideos = computed(() => {
  const list = [...filteredVideos.value]

  if (sortBy.value === 'latest') {
    return list.sort((a, b) => +new Date(b.uploadDate) - +new Date(a.uploadDate))
  }

  if (sortBy.value === 'popular') {
    return list.sort((a, b) => b.views - a.views)
  }

  return list
})

function toggleFilterPanel() {
  showFilterPanel.value = !showFilterPanel.value
}

function resetFilters() {
  activeCategory.value = 'All'
  sortBy.value = 'recommended'
}

async function loadVideos() {
  loading.value = true
  errorMessage.value = ''

  try {
    videos.value = await fetchRecommended(authStore.currentUser?.id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load videos'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadVideos()
})
</script>

<template>
  <main class="home-page">
    <section class="category-row">
      <button class="chip filter-chip" :class="{ active: showFilterPanel }" @click="toggleFilterPanel">
        <AppIcon name="filter" :size="14" />
        Filters
      </button>
      <button
        v-for="category in categories"
        :key="category"
        class="chip"
        :class="{ active: category === activeCategory }"
        @click="activeCategory = category"
      >
        {{ category }}
      </button>
    </section>

    <section v-if="showFilterPanel" class="filter-panel">
      <div class="filter-block">
        <p>Sort by</p>
        <div class="mini-row">
          <button class="mini-chip" :class="{ active: sortBy === 'recommended' }" @click="sortBy = 'recommended'">
            Recommended
          </button>
          <button class="mini-chip" :class="{ active: sortBy === 'latest' }" @click="sortBy = 'latest'">
            Latest
          </button>
          <button class="mini-chip" :class="{ active: sortBy === 'popular' }" @click="sortBy = 'popular'">
            Most viewed
          </button>
        </div>
      </div>

      <div class="filter-block">
        <p>Category</p>
        <div class="mini-row">
          <button
            v-for="category in categories"
            :key="`panel-${category}`"
            class="mini-chip"
            :class="{ active: category === activeCategory }"
            @click="activeCategory = category"
          >
            {{ category }}
          </button>
        </div>
      </div>

      <button class="reset-btn" @click="resetFilters">Reset filters</button>
    </section>

    <section v-if="loading" class="status-box">Loading videos...</section>

    <section v-else-if="errorMessage" class="status-box error-box">
      <p>{{ errorMessage }}</p>
      <button class="retry-btn" @click="loadVideos">Try again</button>
    </section>

    <section v-else-if="displayVideos.length === 0" class="status-box">No videos available yet.</section>

    <section v-else class="video-grid">
      <VideoCard v-for="video in displayVideos" :key="video.id" :video="video" />
    </section>
  </main>
</template>

<style scoped>
.home-page {
  max-width: 1480px;
  margin: 0 auto;
  padding: 18px 16px 34px;
}

.category-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--border-strong);
  background: var(--bg-1);
  color: var(--text-subtle);
  border-radius: 999px;
  padding: 8px 12px;
  white-space: nowrap;
  cursor: pointer;
}

.filter-chip {
  color: var(--text-main);
}

.chip.active {
  color: var(--text-main);
  border-color: var(--accent-outline-soft);
  background: rgba(220, 38, 38, 0.22);
}

.filter-panel {
  margin-top: 8px;
  border: 1px solid var(--border-medium);
  border-radius: 14px;
  background: var(--bg-2);
  padding: 12px;
  display: grid;
  gap: 12px;
}

.filter-block p {
  color: var(--text-main);
  font-size: 13px;
  margin-bottom: 6px;
}

.mini-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mini-chip {
  border: 1px solid var(--border-medium);
  background: var(--bg-1);
  color: var(--text-subtle);
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 13px;
  cursor: pointer;
}

.mini-chip.active {
  color: var(--text-main);
  border-color: var(--accent-outline-soft);
  background: rgba(220, 38, 38, 0.22);
}

.reset-btn {
  justify-self: start;
  border: 1px solid var(--border-strong);
  background: transparent;
  color: var(--text-main);
  border-radius: 9px;
  padding: 7px 11px;
  cursor: pointer;
}

.video-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
}

.status-box {
  margin-top: 14px;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-1);
  color: var(--text-subtle);
  padding: 14px;
}

.error-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.retry-btn {
  border: 1px solid var(--border-strong);
  background: transparent;
  color: var(--text-main);
  border-radius: 8px;
  padding: 7px 10px;
  cursor: pointer;
}
</style>
