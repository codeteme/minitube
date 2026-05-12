<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VideoCard from '@/components/VideoCard.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import { formatViews } from '@/services/video-format'
import { fetchVideoById, fetchVideoTranscript, fetchVideos, updateVideo, deleteVideo, recordView } from '@/services/videos'
import { toApiUploaderId } from '@/services/user-id'
import { recordWatchEvent, fetchSubscribedChannelIds, subscribeToChannel, unsubscribeFromChannel } from '@/services/dashboard'
import { summarizeVideo, fetchAiSummaryStatus, retryAiSummary, fetchAiTags, fetchAiTagTaxonomy } from '@/services/intelligence'
import { createRealtimeVideoChatSocket, isVideoChatMessagePayload, type VideoChatMessagePayload } from '@/services/chat'
import { useAuthStore } from '@/stores/auth'
import type { VideoItem } from '@/types/video'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const currentVideo = ref<VideoItem | null>(null)
const allVideos = ref<VideoItem[]>([])
const loading = ref(false)
const errorMessage = ref('')
const isEditing = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
const editMessage = ref('')
const subscribeLoading = ref(false)
const subscribeMessage = ref('')
const subscribedChannelIds = ref<string[]>([])
const aiSummary = ref('')
const aiSummarySource = ref('')
const aiSummaryGeneratedAt = ref('')
const aiSummaryLoading = ref(false)
const aiSummaryError = ref('')
const aiSummaryStatus = ref<'idle' | 'pending' | 'queued' | 'processing' | 'ready' | 'failed'>('idle')
const aiSummaryCached = ref(false)
const aiSummaryProvider = ref('')
const aiSummaryRetryCount = ref(0)
const aiSummaryExpanded = ref(false)
const aiTags = ref<string[]>([])
const aiTagsProvider = ref('')
const aiTagDisplayByCanonical = ref<Record<string, string>>({})
const transcriptText = ref('')
const transcriptStatus = ref<'idle' | 'pending' | 'queued' | 'processing' | 'ready' | 'failed'>('idle')
const transcriptLoading = ref(false)
const transcriptError = ref('')
const transcriptFailureReason = ref('')
const transcriptSource = ref('')
const transcriptLanguage = ref('')
const transcriptUpdatedAt = ref('')
const transcriptExpanded = ref(false)
const chatMessages = ref<VideoChatMessagePayload[]>([])
const chatInput = ref('')
const chatConnected = ref(false)
const chatStatus = ref('Connecting...')
const chatContainer = ref<HTMLElement | null>(null)
const videoElement = ref<HTMLVideoElement | null>(null)
const viewRecorded = ref(false)
const VIEW_THRESHOLD_SECONDS = 10
let chatSocket: WebSocket | null = null
let watchEventInterval: ReturnType<typeof setInterval> | null = null
let aiTagsPollInterval: ReturnType<typeof setInterval> | null = null

const editForm = reactive({
  title: '',
  description: '',
  category: '',
  tags: '',
})

const playbackUrl = computed(() => {
  if (!currentVideo.value) return ''

  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
  const url = currentVideo.value.videoUrl

  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }

  return `${apiBaseUrl}${url}`
})

async function loadCurrentVideo() {
  const videoId = String(route.params.id)
  if (!videoId) {
    currentVideo.value = null
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const [video, videos] = await Promise.all([fetchVideoById(videoId), fetchVideos()])
    currentVideo.value = video
    allVideos.value = videos
  } catch (error) {
    currentVideo.value = null
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load video.'
  } finally {
    loading.value = false
  }
}

async function loadMySubscriptions() {
  if (!authStore.currentUser) {
    subscribedChannelIds.value = []
    return
  }

  try {
    subscribedChannelIds.value = await fetchSubscribedChannelIds(authStore.currentUser.id)
  } catch {
    subscribedChannelIds.value = []
  }
}

function scrollChatToBottom() {
  if (!chatContainer.value) return
  chatContainer.value.scrollTop = chatContainer.value.scrollHeight
}

function closeChatSocket() {
  if (chatSocket) {
    chatSocket.close()
    chatSocket = null
  }
}

function stopRecordingWatchEvents() {
  if (watchEventInterval) {
    clearInterval(watchEventInterval)
    watchEventInterval = null
  }
}

function stopAiTagsPolling() {
  if (aiTagsPollInterval) {
    clearInterval(aiTagsPollInterval)
    aiTagsPollInterval = null
  }
}

function startRecordingWatchEvents() {
  stopRecordingWatchEvents()

  if (!authStore.currentUser || !currentVideo.value) return

  recordWatchEvent(authStore.currentUser.id, currentVideo.value.id, 0).catch(() => {
    // Silently fail - don't show error to user
  })

  watchEventInterval = setInterval(() => {
    if (!videoElement.value || !authStore.currentUser || !currentVideo.value) return
    const currentPosition = Math.floor(videoElement.value.currentTime)
    recordWatchEvent(authStore.currentUser.id, currentVideo.value.id, currentPosition).catch(() => {
      // Silently fail - don't show error to user
    })
  }, 10000)
}

function onTimeUpdate() {
  if (viewRecorded.value || !currentVideo.value || !videoElement.value) return
  const duration = videoElement.value.duration || Infinity
  const threshold = Math.min(VIEW_THRESHOLD_SECONDS, duration * 0.2)
  if (videoElement.value.currentTime >= threshold) {
    viewRecorded.value = true
    recordView(currentVideo.value.id).catch(() => {})
  }
}

function connectChat() {
  closeChatSocket()

  if (!currentVideo.value || !authStore.currentUser) {
    chatMessages.value = []
    chatConnected.value = false
    chatStatus.value = 'Login required to join chat'
    return
  }

  chatStatus.value = 'Connecting...'
  chatSocket = createRealtimeVideoChatSocket({
    videoId: currentVideo.value.id,
    userId: authStore.currentUser.id,
    username: authStore.currentUser.username,
  })

  chatSocket.onopen = () => {
    chatConnected.value = true
    chatStatus.value = 'Live'
  }

  chatSocket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data) as
        | { type: 'history'; messages: VideoChatMessagePayload[] }
        | { type: 'chat_message' | 'system'; message: string; [key: string]: unknown }
        | { type: 'error'; message: string }

      if (payload.type === 'history') {
        chatMessages.value = payload.messages
        setTimeout(scrollChatToBottom, 0)
        return
      }

      if (payload.type === 'error') {
        chatStatus.value = payload.message
        return
      }

      if (isVideoChatMessagePayload(payload)) {
        chatMessages.value.push(payload)
        setTimeout(scrollChatToBottom, 0)
      }
    } catch {
      // Ignore malformed messages from peers.
    }
  }

  chatSocket.onclose = () => {
    chatConnected.value = false
    chatStatus.value = 'Disconnected'
  }

  chatSocket.onerror = () => {
    chatConnected.value = false
    chatStatus.value = 'Connection error'
  }
}

function sendChatMessage() {
  if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) return
  const text = chatInput.value.trim()
  if (!text) return

  chatSocket.send(JSON.stringify({ message: text }))
  chatInput.value = ''
}

function openUserProfileFromChat(userId: string) {
  if (!userId) return
  if (authStore.currentUser?.id === userId) {
    void router.push({ name: 'profile' })
    return
  }
  void router.push({ name: 'user-profile', params: { userId } })
}

function openCurrentVideoAuthorProfile() {
  if (!currentVideo.value) return
  openUserProfileFromChat(String(currentVideo.value.authorId))
}

const relatedVideos = computed(() => {
  if (!currentVideo.value) return []
  return allVideos.value
    .filter((item) => item.id !== currentVideo.value?.id)
    .filter((item) => {
      return item.category === currentVideo.value?.category || item.tags.some((tag) => currentVideo.value?.tags.includes(tag))
    })
    .slice(0, 6)
})

const manualVideoTags = computed(() => {
  if (!currentVideo.value) return [] as string[]
  return (currentVideo.value.tags || []).map((t) => t.trim()).filter((t) => t.length > 0)
})

const displayTags = computed(() => {
  return aiTags.value.length > 0 ? aiTags.value : manualVideoTags.value
})

const tagsHeading = computed(() => {
  return 'Tags'
})

const tagsSourceLabel = computed(() => {
  return aiTags.value.length > 0 ? 'AI generated' : 'From video metadata'
})

function titleizeTag(raw: string): string {
  return raw
    .split('-')
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

const displayTagLabels = computed(() => {
  return displayTags.value.map((tag) => aiTagDisplayByCanonical.value[tag] || titleizeTag(tag))
})

async function loadAiTagTaxonomy() {
  try {
    const result = await fetchAiTagTaxonomy()
    const mapping: Record<string, string> = {}
    for (const item of result.tags || []) {
      if (item.canonical_tag && item.display_name) {
        mapping[item.canonical_tag] = item.display_name
      }
    }
    aiTagDisplayByCanonical.value = mapping
  } catch {
    aiTagDisplayByCanonical.value = {}
  }
}

onMounted(() => {
  loadCurrentVideo()
  loadMySubscriptions()
  loadAiTagTaxonomy()
})

onUnmounted(() => {
  closeChatSocket()
  stopAiTagsPolling()
  stopRecordingWatchEvents()
})

const isOwner = computed(() => {
  if (!currentVideo.value || !authStore.currentUser) return false
  const currentUserUploaderId = toApiUploaderId(authStore.currentUser.id)
  if (currentUserUploaderId === null) return false
  return String(currentVideo.value.authorId) === String(currentUserUploaderId)
})

const canSubscribe = computed(() => {
  if (!authStore.currentUser || !currentVideo.value) return false
  return !isOwner.value
})

const isSubscribed = computed(() => {
  if (!currentVideo.value) return false
  return subscribedChannelIds.value.includes(String(currentVideo.value.authorId))
})

function startEditing() {
  if (!currentVideo.value) return
  editForm.title = currentVideo.value.title
  editForm.description = currentVideo.value.description
  editForm.category = currentVideo.value.category
  editForm.tags = currentVideo.value.tags.join(', ')
  isEditing.value = true
  editMessage.value = ''
}

function cancelEditing() {
  isEditing.value = false
  editMessage.value = ''
}

async function saveChanges() {
  if (!currentVideo.value) return

  if (!editForm.title.trim()) {
    editMessage.value = 'Title cannot be empty.'
    return
  }

  isSaving.value = true
  editMessage.value = ''

  try {
    const updated = await updateVideo({
      videoId: currentVideo.value.id,
      title: editForm.title,
      description: editForm.description,
      category: editForm.category,
      tags: editForm.tags,
    })
    currentVideo.value = updated
    isEditing.value = false
    editMessage.value = 'Video updated successfully!'
    setTimeout(() => { editMessage.value = '' }, 3000)
  } catch (error) {
    editMessage.value = error instanceof Error ? error.message : 'Failed to update video.'
  } finally {
    isSaving.value = false
  }
}

async function onDelete() {
  if (!currentVideo.value) return
  if (!confirm('Are you sure you want to delete this video?')) return
  
  isDeleting.value = true
  
  try {
    await deleteVideo(currentVideo.value.id)
    router.push('/')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to delete video.'
    isDeleting.value = false
  }
}

async function toggleSubscription() {
  if (!authStore.currentUser || !currentVideo.value || isOwner.value) return

  subscribeLoading.value = true
  subscribeMessage.value = ''

  const subscriberId = authStore.currentUser.id
  const channelId = String(currentVideo.value.authorId)

  try {
    if (isSubscribed.value) {
      await unsubscribeFromChannel(subscriberId, channelId)
      subscribeMessage.value = ''
      subscribedChannelIds.value = subscribedChannelIds.value.filter((id) => id !== channelId)
      if (authStore.currentUser) {
        authStore.currentUser.subscribedTo = authStore.currentUser.subscribedTo.filter((id) => id !== channelId)
      }
    } else {
      await subscribeToChannel(subscriberId, channelId)
      subscribeMessage.value = ''
      if (!subscribedChannelIds.value.includes(channelId)) {
        subscribedChannelIds.value = [...subscribedChannelIds.value, channelId]
      }
      if (authStore.currentUser && !authStore.currentUser.subscribedTo.includes(channelId)) {
        authStore.currentUser.subscribedTo = [...authStore.currentUser.subscribedTo, channelId]
      }
    }
  } catch (error) {
    subscribeMessage.value = error instanceof Error ? error.message : 'Subscription update failed.'
  } finally {
    subscribeLoading.value = false
  }
}

async function generateAiSummary() {
  if (!currentVideo.value) return

  aiSummaryExpanded.value = true
  aiSummaryLoading.value = true
  aiSummaryError.value = ''
  aiSummaryStatus.value = 'queued'

  try {
    let result = await summarizeVideo({ videoId: currentVideo.value.id, maxSentences: 3 })
    aiSummaryStatus.value = result.status
    aiSummaryCached.value = result.cached
    aiSummaryProvider.value = result.provider || ''
    aiSummaryRetryCount.value = result.retry_count || 0

    for (let i = 0; i < 25 && (result.status === 'queued' || result.status === 'processing'); i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 600))
      result = await fetchAiSummaryStatus(currentVideo.value.id)
      aiSummaryStatus.value = result.status
      aiSummaryCached.value = result.cached
      aiSummaryProvider.value = result.provider || ''
      aiSummaryRetryCount.value = result.retry_count || 0
    }

    if (result.status === 'failed') {
      aiSummary.value = ''
      aiSummarySource.value = ''
      aiSummaryGeneratedAt.value = ''
      aiSummaryError.value = result.error_message || 'AI summary job failed.'
      return
    }

    if (result.status === 'ready' && result.summary) {
      aiSummary.value = result.summary
      aiSummarySource.value = result.source_kind || ''
      aiSummaryGeneratedAt.value = result.generated_at || ''
      return
    }

    aiSummaryError.value = 'AI summary is still processing. Try again in a moment.'
  } catch (error) {
    aiSummaryError.value = error instanceof Error ? error.message : 'Failed to generate AI summary.'
  } finally {
    aiSummaryLoading.value = false
  }
}

async function toggleAiSummaryPanel() {
  aiSummaryExpanded.value = !aiSummaryExpanded.value
  if (!aiSummaryExpanded.value) {
    return
  }
  if (!aiSummary.value && !aiSummaryLoading.value && aiSummaryStatus.value === 'idle') {
    await generateAiSummary()
  }
}

async function retryAiSummaryJob() {
  if (!currentVideo.value) return
  aiSummaryLoading.value = true
  aiSummaryError.value = ''
  aiSummaryStatus.value = 'queued'
  aiSummary.value = ''
  aiSummarySource.value = ''
  aiSummaryGeneratedAt.value = ''
  try {
    await retryAiSummary(currentVideo.value.id, 3)
    await generateAiSummary()
  } catch (error) {
    aiSummaryError.value = error instanceof Error ? error.message : 'Failed to retry AI summary.'
  } finally {
    aiSummaryLoading.value = false
  }
}

async function loadAiTags() {
  if (!currentVideo.value) return
  try {
    const result = await fetchAiTags(currentVideo.value.id)
    aiTags.value = result.tags || []
    aiTagsProvider.value = result.provider || ''
  } finally {
    if (aiTags.value.length > 0) {
      stopAiTagsPolling()
    }
  }
}

function startAiTagsPolling() {
  stopAiTagsPolling()
  let attempts = 0
  aiTagsPollInterval = setInterval(async () => {
    attempts += 1
    await loadAiTags()
    if (aiTags.value.length > 0 || transcriptStatus.value === 'failed' || attempts >= 20) {
      stopAiTagsPolling()
    }
  }, 3000)
}

async function loadTranscript() {
  if (!currentVideo.value) return

  transcriptLoading.value = true
  transcriptError.value = ''

  try {
    const result = await fetchVideoTranscript(currentVideo.value.id)
    transcriptStatus.value = result.status
    transcriptText.value = result.transcript_text || ''
    transcriptFailureReason.value = result.error_message || ''
    transcriptSource.value = result.source || ''
    transcriptLanguage.value = result.language || ''
    transcriptUpdatedAt.value = result.updated_at || ''
  } catch (error) {
    transcriptError.value = error instanceof Error ? error.message : 'Failed to load transcript.'
  } finally {
    transcriptLoading.value = false
  }
}

async function toggleTranscriptPanel() {
  transcriptExpanded.value = !transcriptExpanded.value
  if (transcriptExpanded.value && transcriptStatus.value === 'idle') {
    await loadTranscript()
  }
}

watch(
  () => route.params.id,
  () => {
    subscribeMessage.value = ''
    aiSummary.value = ''
    aiSummarySource.value = ''
    aiSummaryGeneratedAt.value = ''
    aiSummaryError.value = ''
    aiSummaryStatus.value = 'idle'
    aiSummaryCached.value = false
    aiSummaryProvider.value = ''
    aiSummaryRetryCount.value = 0
    aiSummaryExpanded.value = false
    aiTags.value = []
    aiTagsProvider.value = ''
    transcriptText.value = ''
    transcriptStatus.value = 'idle'
    transcriptError.value = ''
    transcriptFailureReason.value = ''
    transcriptSource.value = ''
    transcriptLanguage.value = ''
    transcriptUpdatedAt.value = ''
    transcriptExpanded.value = false
    viewRecorded.value = false
    stopAiTagsPolling()
    stopRecordingWatchEvents()
    loadCurrentVideo()
  },
)

watch(
  () => [currentVideo.value?.id, authStore.currentUser?.id],
  () => {
    connectChat()
    loadMySubscriptions()
    loadTranscript()
    loadAiTags()
    startAiTagsPolling()
  },
)

watch(
  () => videoElement.value?.paused,
  (isPaused) => {
    if (isPaused) {
      stopRecordingWatchEvents()
    } else {
      startRecordingWatchEvents()
    }
  },
)
</script>

<template>
  <main v-if="loading" class="watch-page">
    <section class="channel-card">
      <p>Loading video...</p>
    </section>
  </main>

  <main v-if="currentVideo" class="watch-page">
    <section class="main-col">
      <div class="player-wrap">
        <video ref="videoElement" :src="playbackUrl" :poster="currentVideo.thumbnail" controls preload="metadata" @play="startRecordingWatchEvents" @pause="stopRecordingWatchEvents" @timeupdate="onTimeUpdate" />
      </div>

      <h1>{{ currentVideo.title }}</h1>
      <p class="meta">
        <span><AppIcon name="views" :size="14" /> {{ formatViews(currentVideo.views) }} views</span>
        <span>•</span>
        <span><AppIcon name="clock" :size="14" /> {{ new Date(currentVideo.uploadDate).toLocaleDateString() }}</span>
      </p>
      <div class="actions">
        <button v-if="canSubscribe" @click="toggleSubscription" :disabled="subscribeLoading" class="btn-subscribe">
          <AppIcon name="users" :size="14" />
          {{ subscribeLoading ? 'Updating...' : isSubscribed ? 'Unsubscribe' : 'Subscribe' }}
        </button>
        <button @click="toggleAiSummaryPanel" :disabled="aiSummaryLoading" class="btn-ai-summary" :class="{ loading: aiSummaryLoading }">
          <AppIcon name="search" :size="14" />
          {{ aiSummaryLoading ? 'Generating summary...' : aiSummaryExpanded ? 'Hide Summary' : 'AI Summary' }}
        </button>
        <button @click="toggleTranscriptPanel" class="btn-transcript">
          <AppIcon name="search" :size="14" />
          {{ transcriptExpanded ? 'Hide Transcript' : 'Auto Transcript' }}
        </button>
        <button v-if="isOwner && !isEditing" @click="startEditing" class="btn-edit">
          <AppIcon name="video" :size="14" /> Edit
        </button>
        <button v-if="isOwner && !isEditing" @click="onDelete" :disabled="isDeleting" class="btn-delete">
          <AppIcon name="empty" :size="14" /> {{ isDeleting ? 'Deleting...' : 'Delete' }}
        </button>
      </div>
      <p v-if="subscribeMessage" class="subscribe-error">{{ subscribeMessage }}</p>
      <p v-if="aiSummaryError" class="subscribe-error">{{ aiSummaryError }}</p>
      <p v-if="transcriptError" class="subscribe-error">{{ transcriptError }}</p>

      <section v-if="aiSummaryExpanded" class="ai-summary-card">
        <header class="ai-summary-head">
          <h2><AppIcon name="search" :size="14" /> AI Summary</h2>
          <div class="transcript-actions">
            <button class="transcript-refresh" :disabled="aiSummaryLoading" @click="generateAiSummary">
              {{ aiSummaryLoading ? 'Refreshing...' : (aiSummary ? 'Regenerate' : 'Generate') }}
            </button>
            <button class="transcript-refresh" @click="aiSummaryExpanded = false">Close</button>
          </div>
        </header>
        <div class="ai-summary-meta" v-if="aiSummary">
          <span class="ai-chip">{{ aiSummarySource === 'subtitle_text' ? 'From Transcript' : 'From Metadata' }}</span>
          <small class="ai-time">{{ new Date(aiSummaryGeneratedAt).toLocaleString() }}</small>
        </div>
        <p
          v-if="aiSummaryLoading || aiSummaryStatus === 'queued' || aiSummaryStatus === 'processing'"
          class="ai-summary-placeholder"
        >
          Crafting a concise summary...
        </p>
        <p v-else-if="aiSummaryStatus === 'failed'" class="transcript-failed">
          AI summary failed. {{ aiSummaryError || 'Please retry.' }}
        </p>
        <p v-else-if="aiSummary" class="ai-summary-text">{{ aiSummary }}</p>
        <p v-else class="transcript-note">
          No AI summary yet. Click Generate to create one.
        </p>
        <small v-if="aiSummary" class="ai-time">
          <span v-if="aiSummaryCached">Cached</span>
          <span v-if="aiSummaryProvider"> • {{ aiSummaryProvider }}</span>
          <span> • Retries: {{ aiSummaryRetryCount }}</span>
        </small>
        <button
          v-if="aiSummaryStatus === 'failed'"
          class="transcript-refresh"
          :disabled="aiSummaryLoading"
          @click="retryAiSummaryJob"
        >
          {{ aiSummaryLoading ? 'Retrying...' : 'Retry Summary' }}
        </button>
      </section>

      <section v-if="displayTags.length > 0" class="transcript-card">
        <header class="transcript-head">
          <h2><AppIcon name="search" :size="14" /> {{ tagsHeading }}</h2>
          <small class="ai-time">
            {{ tagsSourceLabel }}<span v-if="aiTags.length > 0 && aiTagsProvider"> • {{ aiTagsProvider }}</span>
          </small>
        </header>
        <div class="tag-list">
          <span v-for="(label, idx) in displayTagLabels" :key="`${displayTags[idx]}-${idx}`" class="tag-chip">{{ label }}</span>
        </div>
      </section>

      <section v-if="transcriptExpanded" class="transcript-card">
        <header class="transcript-head">
          <h2><AppIcon name="search" :size="14" /> Auto Transcript</h2>
          <div class="transcript-actions">
            <button class="transcript-refresh" :disabled="transcriptLoading" @click="loadTranscript">
              {{ transcriptLoading ? 'Refreshing...' : 'Refresh' }}
            </button>
            <button class="transcript-refresh" @click="transcriptExpanded = false">Close</button>
          </div>
        </header>
        <p v-if="transcriptStatus === 'pending' || transcriptStatus === 'queued' || transcriptStatus === 'processing'" class="transcript-note">
          Transcript is still processing. Try refresh in a moment.
        </p>
        <p v-else-if="transcriptStatus === 'failed'" class="transcript-failed">
          Transcript processing failed. {{ transcriptFailureReason || 'Check video service logs and retry.' }}
        </p>
        <p v-else-if="transcriptText" class="transcript-text">{{ transcriptText }}</p>
        <p v-else class="transcript-note">No transcript yet.</p>
        <small v-if="transcriptText" class="transcript-meta">
          Source: {{ transcriptSource || 'unknown' }}
          <span v-if="transcriptLanguage">• Language: {{ transcriptLanguage }}</span>
          <span v-if="transcriptUpdatedAt">• Updated: {{ new Date(transcriptUpdatedAt).toLocaleString() }}</span>
        </small>
      </section>

      <div v-if="isEditing" class="edit-form">
        <h2>Edit Video</h2>
        <label>
          Title
          <input v-model="editForm.title" type="text" />
        </label>
        <label>
          Description
          <textarea v-model="editForm.description" rows="4"></textarea>
        </label>
        <label>
          Category
          <select v-model="editForm.category">
            <option>Education</option>
            <option>Technology</option>
            <option>Nature</option>
            <option>Food</option>
            <option>Fitness</option>
            <option>Music</option>
            <option>Gaming</option>
          </select>
        </label>
        <label>
          Tags (comma-separated)
          <input v-model="editForm.tags" type="text" placeholder="e.g., tutorial, beginner" />
        </label>
        <div class="edit-actions">
          <button @click="saveChanges" :disabled="isSaving" class="btn-save">
            {{ isSaving ? 'Saving...' : 'Save Changes' }}
          </button>
          <button @click="cancelEditing" :disabled="isSaving" class="btn-cancel">
            Cancel
          </button>
        </div>
        <p v-if="editMessage" class="edit-message">{{ editMessage }}</p>
      </div>

      <section class="channel-card">
        <button
          type="button"
          class="channel-link"
          :aria-label="`Open ${currentVideo.authorName} profile`"
          @click="openCurrentVideoAuthorProfile"
        >
          <img :src="currentVideo.authorAvatar" :alt="currentVideo.authorName" class="avatar" />
        </button>
        <div>
          <button type="button" class="name channel-link" @click="openCurrentVideoAuthorProfile">
            {{ currentVideo.authorName }}
          </button>
          <p class="desc">{{ currentVideo.description }}</p>
        </div>
      </section>
    </section>

    <aside class="side-col">
      <section class="chat-card">
        <header class="chat-header">
          <h3><AppIcon name="users" :size="15" /> Live chat</h3>
          <span :class="['chat-state', { live: chatConnected }]">{{ chatStatus }}</span>
        </header>

        <div ref="chatContainer" class="chat-messages">
          <p v-if="chatMessages.length === 0" class="chat-empty">No messages yet.</p>

          <article
            v-for="(item, index) in chatMessages"
            :key="`${item.timestamp}-${index}`"
            class="chat-row"
            :class="{ system: item.type === 'system' }"
          >
            <p class="chat-meta">
              <button
                v-if="item.type !== 'system'"
                type="button"
                class="chat-user-link"
                @click="openUserProfileFromChat(item.user_id)"
              >
                {{ item.username }}
              </button>
              <strong v-else>{{ item.username }}</strong>
              <small>{{ new Date(item.timestamp).toLocaleTimeString() }}</small>
            </p>
            <p class="chat-text">{{ item.message }}</p>
          </article>
        </div>

        <form class="chat-form" @submit.prevent="sendChatMessage">
          <input
            v-model="chatInput"
            :disabled="!authStore.currentUser || !chatConnected"
            type="text"
            placeholder="Say something..."
            maxlength="2000"
          />
          <button type="submit" :disabled="!chatInput.trim() || !chatConnected">
            <AppIcon name="play" :size="12" /> Send
          </button>
        </form>
      </section>

      <h2 class="related-heading"><AppIcon name="video" :size="16" /> Related videos</h2>
      <div class="related-list">
        <VideoCard v-for="video in relatedVideos" :key="video.id" :video="video" />
      </div>
    </aside>
  </main>

  <main v-else class="watch-page">
    <section class="channel-card">
      <p>{{ errorMessage || 'Video not found.' }}</p>
    </section>
  </main>
</template>

<style scoped>
.watch-page {
  max-width: 1450px;
  margin: 0 auto;
  padding: 20px 16px 34px;
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(300px, 1fr);
  gap: 20px;
}

.player-wrap {
  aspect-ratio: 16 / 9;
  border-radius: 14px;
  overflow: hidden;
  background: #000;
}

.player-wrap video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

h1 {
  margin-top: 14px;
  color: var(--text-main);
  font-size: 24px;
}

.meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  margin-top: 4px;
}

.meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.btn-edit,
.btn-delete,
.btn-subscribe,
.btn-ai-summary,
.btn-transcript,
.btn-save,
.btn-cancel {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.btn-ai-summary {
  background: linear-gradient(135deg, #1f2937, #111827);
  color: #e6f6fb;
  border: 1px solid rgba(34, 211, 238, 0.44);
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  letter-spacing: 0.01em;
  box-shadow: 0 6px 16px rgba(2, 6, 23, 0.35);
  transition: transform 160ms ease, box-shadow 160ms ease, background-color 160ms ease, border-color 160ms ease;
}

.btn-ai-summary:hover:not(:disabled) {
  transform: translateY(-1px);
  background: linear-gradient(135deg, #273548, #172033);
  border-color: rgba(34, 211, 238, 0.7);
  box-shadow: 0 9px 20px rgba(8, 47, 73, 0.4);
}

.btn-ai-summary.loading {
  border-color: rgba(103, 232, 249, 0.9);
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.2), 0 9px 20px rgba(8, 47, 73, 0.4);
}

.btn-ai-summary:disabled {
  opacity: 0.8;
  cursor: not-allowed;
}

.btn-ai-summary:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.35), 0 9px 20px rgba(8, 47, 73, 0.4);
}

.btn-transcript {
  background: #20242c;
  color: #e6ecf8;
  border: 1px solid rgba(148, 163, 184, 0.38);
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
}

.btn-transcript:hover {
  background: #2a303a;
  border-color: rgba(148, 163, 184, 0.62);
}

.btn-subscribe {
  background: #f59e0b;
  color: #111827;
}

.btn-subscribe:hover:not(:disabled) {
  background: #d97706;
}

.btn-subscribe:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.subscribe-error {
  margin-top: 8px;
  color: var(--accent-text-mid);
  font-size: 14px;
}

.ai-summary-card {
  margin-top: 12px;
  border-radius: 14px;
  border: 1px solid rgba(34, 211, 238, 0.34);
  background: linear-gradient(155deg, rgba(3, 105, 161, 0.2), rgba(12, 74, 110, 0.12));
  padding: 13px 14px;
  position: relative;
  overflow: hidden;
}

.ai-summary-card::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: linear-gradient(180deg, #22d3ee, #0ea5e9);
}

.ai-summary-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.ai-summary-head .transcript-actions {
  margin-left: auto;
}

.ai-summary-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.ai-summary-card h2 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #f0f9ff;
  font-size: 14px;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.ai-chip {
  border: 1px solid rgba(103, 232, 249, 0.42);
  background: rgba(14, 116, 144, 0.25);
  color: #a5f3fc;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.ai-time {
  color: #bae6fd;
  font-size: 11px;
}

.ai-summary-placeholder,
.ai-summary-text {
  margin-top: 8px;
  color: #e0f2fe;
  line-height: 1.5;
  font-size: 14px;
}

.ai-summary-placeholder {
  opacity: 0.88;
  font-style: italic;
}

.transcript-card {
  margin-top: 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: #17191f;
  padding: 12px;
}

.transcript-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.transcript-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.transcript-head h2 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #e5e7eb;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.transcript-refresh {
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: #21242d;
  color: #eef2ff;
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}

.transcript-refresh:hover:not(:disabled) {
  background: #2a2f3a;
}

.transcript-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.transcript-note {
  margin-top: 8px;
  color: #9ca3af;
  font-size: 14px;
}

.transcript-failed {
  margin-top: 8px;
  color: #fca5a5;
  font-size: 14px;
}

.transcript-text {
  margin-top: 8px;
  color: #e5e7eb;
  line-height: 1.55;
  font-size: 14px;
  max-height: 180px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.transcript-meta {
  margin-top: 8px;
  display: block;
  color: #94a3b8;
  font-size: 12px;
}

.tag-list {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid rgba(56, 189, 248, 0.35);
  background: rgba(14, 116, 144, 0.2);
  color: #bae6fd;
  font-size: 12px;
  font-weight: 600;
}

.btn-edit {
  background: #0ea5e9;
  color: var(--text-main);
}

.btn-edit:hover {
  background: #0284c7;
}

.btn-delete {
  background: #ef4444;
  color: var(--text-main);
}

.btn-delete:hover:not(:disabled) {
  background: #dc2626;
}

.btn-delete:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.edit-form {
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: var(--bg-1);
  padding: 16px;
  margin-top: 14px;
}

.edit-form h2 {
  color: var(--text-main);
  margin-bottom: 12px;
  font-size: 18px;
}

.edit-form label {
  display: block;
  color: var(--text-soft);
  margin-bottom: 10px;
  font-size: 14px;
}

.edit-form input,
.edit-form textarea,
.edit-form select {
  width: 100%;
  padding: 8px 12px;
  background: var(--surface-2a);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-main);
  margin-top: 4px;
  font-family: inherit;
}

.edit-form input:focus,
.edit-form textarea:focus,
.edit-form select:focus {
  outline: none;
  border-color: #0ea5e9;
  box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.2);
}

.edit-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.btn-save {
  background: #10b981;
  color: var(--text-main);
  flex: 1;
}

.btn-save:hover:not(:disabled) {
  background: #059669;
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: var(--text-faint);
  color: var(--text-main);
  flex: 1;
}

.btn-cancel:hover:not(:disabled) {
  background: #4b5563;
}

.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.edit-message {
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid #10b981;
  border-radius: 6px;
  color: #10b981;
  font-size: 14px;
}

.channel-card {
  margin-top: 14px;
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: var(--bg-1);
  padding: 14px;
  display: flex;
  gap: 10px;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 999px;
}

.channel-link {
  border: none;
  background: transparent;
  padding: 0;
  margin: 0;
  text-align: left;
  cursor: pointer;
}

.name {
  color: var(--text-main);
  font-weight: 600;
}

.name:hover,
.channel-link:hover .avatar {
  opacity: 0.88;
}

.desc {
  margin-top: 4px;
  color: var(--text-soft);
  font-size: 14px;
}

.side-col h2 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-main);
  font-size: 18px;
  margin-bottom: 10px;
}

.related-list {
  display: grid;
  gap: 14px;
}

.related-heading {
  margin-top: 16px;
}

.chat-card {
  margin-top: 0;
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: var(--bg-1);
  padding: 12px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.chat-header h3 {
  color: var(--text-main);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.chat-state {
  color: var(--text-muted);
  font-size: 12px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  padding: 2px 8px;
}

.chat-state.live {
  color: #d1fae5;
  border-color: rgba(16, 185, 129, 0.65);
  background: rgba(16, 185, 129, 0.2);
}

.chat-messages {
  height: 260px;
  overflow-y: auto;
  border-radius: 10px;
  border: 1px solid var(--border-faint);
  background: var(--bg-9);
  padding: 10px;
}

.chat-empty {
  color: var(--text-muted);
  text-align: center;
  margin-top: 100px;
}

.chat-row {
  margin-bottom: 10px;
}

.chat-row.system .chat-meta strong {
  color: var(--accent-text-soft);
}

.chat-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.chat-meta strong {
  color: var(--text-main);
  font-size: 13px;
}

.chat-user-link {
  border: none;
  background: transparent;
  color: var(--text-main);
  font-size: 13px;
  font-weight: 700;
  padding: 0;
  margin: 0;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.chat-user-link:hover {
  color: var(--accent-text-strong);
}

.chat-meta small {
  color: var(--text-muted);
  font-size: 11px;
}

.chat-text {
  color: var(--text-subtle);
  margin-top: 2px;
  line-height: 1.45;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-form {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.chat-form input {
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--bg-3);
  color: var(--text-main);
  padding: 9px 12px;
}

.chat-form button {
  border-radius: 999px;
  border: 1px solid var(--border-heavy);
  background: rgba(220, 38, 38, 0.92);
  color: var(--text-main);
  padding: 8px 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.chat-form button:disabled,
.chat-form input:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 1100px) {
  .watch-page {
    grid-template-columns: 1fr;
  }

  .chat-messages {
    height: 220px;
  }
}
</style>
