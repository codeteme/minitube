<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { uploadVideo } from '@/services/videos'
import { toApiUploaderId } from '@/services/user-id'
import { fetchAiTagTaxonomy, type AiTagTaxonomyItem } from '@/services/intelligence'

const authStore = useAuthStore()
const router = useRouter()
const loading = ref(false)
const errorMessage = ref('')
const selectedFile = ref<File | null>(null)
const videoDuration = ref<number>(0)
const tagOptions = ref<AiTagTaxonomyItem[]>([])
const tagLoading = ref(false)
const selectedCanonicalTags = ref<string[]>([])
const uploadSuccessModalOpen = ref(false)
const uploadedVideoTitle = ref('')
const uploadedVideoId = ref('')
const uploadRedirectSeconds = ref(3)
const isNavigatingAfterUpload = ref(false)
let uploadRedirectTimer: ReturnType<typeof setTimeout> | null = null
let uploadCountdownTimer: ReturnType<typeof setInterval> | null = null
let uploadNavigateTimer: ReturnType<typeof setTimeout> | null = null

const form = reactive({
  title: '',
  description: '',
})

const tagsByCategory = computed<Record<string, AiTagTaxonomyItem[]>>(() => {
  const grouped: Record<string, AiTagTaxonomyItem[]> = {}
  for (const tag of tagOptions.value) {
    const category = tag.category
    const list = grouped[category] ?? []
    list.push(tag)
    grouped[category] = list
  }
  return grouped
})

function _displayCategory(raw: string): string {
  return raw
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

const inferredPrimaryCategory = computed<string | null>(() => {
  if (selectedCanonicalTags.value.length === 0) return null
  const canonicalToCategory = new Map(tagOptions.value.map((item) => [item.canonical_tag, item.category]))
  const counts: Record<string, number> = {}
  for (const tag of selectedCanonicalTags.value) {
    const category = canonicalToCategory.get(tag)
    if (!category) continue
    counts[category] = (counts[category] || 0) + 1
  }
  const entries = Object.entries(counts)
  if (entries.length === 0) return null
  entries.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  const top = entries[0]
  if (!top) return null
  return top[0]
})

const uploadCategory = computed<string>(() => {
  if (!inferredPrimaryCategory.value) return 'General'
  return _displayCategory(inferredPrimaryCategory.value)
})

async function loadTagTaxonomy() {
  tagLoading.value = true
  try {
    const result = await fetchAiTagTaxonomy()
    tagOptions.value = result.tags || []
  } catch {
    tagOptions.value = []
  } finally {
    tagLoading.value = false
  }
}

function toggleTag(canonicalTag: string) {
  if (selectedCanonicalTags.value.includes(canonicalTag)) {
    selectedCanonicalTags.value = selectedCanonicalTags.value.filter((v) => v !== canonicalTag)
    return
  }
  selectedCanonicalTags.value = [...selectedCanonicalTags.value, canonicalTag]
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0] || null
  selectedFile.value = file
  
  if (file) {
    // Extract duration from video file metadata
    const video = document.createElement('video')
    video.src = URL.createObjectURL(file)
    video.onloadedmetadata = () => {
      videoDuration.value = Math.round(video.duration)
      URL.revokeObjectURL(video.src)
    }
  } else {
    videoDuration.value = 0
  }
}

async function onSubmit() {
  errorMessage.value = ''

  if (!selectedFile.value) {
    errorMessage.value = 'Please choose a video file.'
    return
  }

  const uploaderId = toApiUploaderId(authStore.currentUser?.id)
  if (uploaderId === null) {
    errorMessage.value = 'Current user id is not compatible with upload API.'
    return
  }

  loading.value = true

  try {
    const created = await uploadVideo({
      file: selectedFile.value,
      title: form.title,
      description: form.description,
      category: uploadCategory.value,
      tags: selectedCanonicalTags.value.join(','),
      uploaderId,
      durationSeconds: videoDuration.value,
    })

    uploadedVideoTitle.value = created.title
    uploadedVideoId.value = created.id
    isNavigatingAfterUpload.value = false
    uploadSuccessModalOpen.value = true
    startUploadRedirectCountdown()
    form.title = ''
    form.description = ''
    selectedCanonicalTags.value = []
    selectedFile.value = null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Upload failed.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadTagTaxonomy()
})

onUnmounted(() => {
  clearUploadRedirectTimers()
})

function clearUploadRedirectTimers() {
  if (uploadRedirectTimer) {
    clearTimeout(uploadRedirectTimer)
    uploadRedirectTimer = null
  }
  if (uploadCountdownTimer) {
    clearInterval(uploadCountdownTimer)
    uploadCountdownTimer = null
  }
  if (uploadNavigateTimer) {
    clearTimeout(uploadNavigateTimer)
    uploadNavigateTimer = null
  }
}

function goToUploadedVideoAfterUpload() {
  if (isNavigatingAfterUpload.value) return
  clearUploadRedirectTimers()
  isNavigatingAfterUpload.value = true
  const targetPath = uploadedVideoId.value ? `/video/${uploadedVideoId.value}` : '/profile'
  uploadNavigateTimer = setTimeout(() => {
    void router.push(targetPath)
  }, 420)
}

function startUploadRedirectCountdown() {
  clearUploadRedirectTimers()
  uploadRedirectSeconds.value = 4
  uploadCountdownTimer = setInterval(() => {
    if (uploadRedirectSeconds.value <= 1) {
      if (uploadCountdownTimer) {
        clearInterval(uploadCountdownTimer)
        uploadCountdownTimer = null
      }
      return
    }
    uploadRedirectSeconds.value -= 1
  }, 1000)
  uploadRedirectTimer = setTimeout(() => {
    goToUploadedVideoAfterUpload()
  }, 4000)
}
</script>

<template>
  <main class="upload-page">
    <section class="upload-card">
      <h1><AppIcon name="upload" :size="22" /> Upload video</h1>
      <p class="sub">Fields marked with * are required. Leave tags empty to let AI generate them.</p>

      <form class="form" @submit.prevent="onSubmit">
        <label>
          <span class="label-line">Video file <span class="required-mark" aria-hidden="true">*</span></span>
          <input type="file" accept="video/*,.mp4,.webm,.mov" @change="onFileChange" required />
        </label>

        <label>
          <span class="label-line">Title <span class="required-mark" aria-hidden="true">*</span></span>
          <input v-model="form.title" type="text" placeholder="Enter video title" required />
        </label>

        <label>
          Description
          <textarea v-model="form.description" rows="5" placeholder="Describe your video"></textarea>
        </label>

        <label>
          Canonical tags (optional, leave empty for AI auto-generation)
          <div class="tag-box">
            <p v-if="tagLoading" class="muted-mini">Loading canonical tags...</p>
            <template v-else>
              <div v-if="tagOptions.length === 0" class="muted-mini">
                Tag list is unavailable now. You can still upload without manual tags.
              </div>
              <div v-for="(items, category) in tagsByCategory" :key="category" class="tag-group">
                <div class="tag-category">{{ category }}</div>
                <div class="tag-grid">
                  <button
                    v-for="item in items"
                    :key="item.canonical_tag"
                    type="button"
                    class="tag-chip"
                    :class="{ active: selectedCanonicalTags.includes(item.canonical_tag) }"
                    @click="toggleTag(item.canonical_tag)"
                  >
                    {{ item.display_name }}
                  </button>
                </div>
              </div>
            </template>
          </div>
          <p class="muted-mini category-note">
            Primary category:
            {{
              inferredPrimaryCategory
                ? _displayCategory(inferredPrimaryCategory)
                : 'General (will be inferred by AI when tags are auto-generated)'
            }}
          </p>
        </label>

        <button :disabled="loading" type="submit" class="submit-btn">
          <AppIcon name="upload" :size="15" /> {{ loading ? 'Uploading...' : 'Upload Video' }}
        </button>
      </form>

      <p v-if="errorMessage" class="error">
        {{ errorMessage }}
      </p>
    </section>

    <transition name="modal-fade">
      <div v-if="uploadSuccessModalOpen" class="modal-mask" role="dialog" aria-modal="true" aria-labelledby="upload-success-title">
        <div class="success-modal">
          <div class="modal-icon"><AppIcon name="check" :size="18" /></div>
          <h2 id="upload-success-title">Upload successful</h2>
          <p v-if="!isNavigatingAfterUpload">
            Your video
            <strong>"{{ uploadedVideoTitle }}"</strong>
            is uploaded. Redirecting to the video page in {{ uploadRedirectSeconds }}s.
          </p>
          <p v-else class="navigating-text">Opening your video...</p>
          <button type="button" class="modal-btn" :disabled="isNavigatingAfterUpload" @click="goToUploadedVideoAfterUpload">
            {{ isNavigatingAfterUpload ? 'Opening...' : 'Go to Video Now' }}
          </button>
        </div>
      </div>
    </transition>
  </main>
</template>

<style scoped>
.upload-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 22px 16px 34px;
}

.upload-card {
  border-radius: 16px;
  border: 1px solid var(--border-default);
  background: var(--bg-1);
  padding: 20px;
}

h1 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-main);
  font-size: 28px;
  margin: 0;
}

.sub {
  color: var(--text-muted);
  margin: 8px 0 0;
  line-height: 1.4;
}

.form {
  margin-top: 16px;
  display: grid;
  gap: 12px;
}

label {
  display: grid;
  gap: 6px;
  color: var(--text-body);
  font-size: 14px;
}

.required-mark {
  color: #f87171;
  font-weight: 700;
}

.label-line {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

input,
textarea,
select {
  background: var(--bg-0);
  border: 1px solid var(--border-medium);
  color: var(--text-main);
  border-radius: 10px;
  padding: 10px 12px;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 8px;
  border: none;
  border-radius: 10px;
  padding: 11px 14px;
  color: var(--text-inverse);
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  font-weight: 600;
  cursor: pointer;
}

.submit-btn:disabled {
  cursor: not-allowed;
}

.tag-box {
  background: #0f0f0f;
  border: 1px solid rgba(255, 255, 255, 0.17);
  border-radius: 10px;
  padding: 10px;
}

.muted-mini {
  color: #9ca3af;
  font-size: 12px;
}

.tag-group + .tag-group {
  margin-top: 10px;
}

.tag-category {
  font-size: 12px;
  color: #9ca3af;
  text-transform: capitalize;
  margin-bottom: 6px;
}

.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip {
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: #171717;
  color: #e5e7eb;
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
}

.tag-chip.active {
  background: #dc2626;
  border-color: #dc2626;
  color: #fff;
}

.error {
  margin-top: 12px;
  color: var(--accent-text-mid);
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.66);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 1000;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.success-modal {
  width: min(460px, 100%);
  border-radius: 14px;
  border: 1px solid rgba(34, 197, 94, 0.4);
  background: linear-gradient(165deg, #111827, #0f172a);
  box-shadow: 0 22px 50px rgba(2, 6, 23, 0.6);
  padding: 18px;
}

.modal-icon {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #dcfce7;
  background: rgba(34, 197, 94, 0.3);
  border: 1px solid rgba(34, 197, 94, 0.45);
  margin-bottom: 10px;
}

.success-modal h2 {
  margin: 0 0 8px;
  font-size: 20px;
  color: #ecfdf5;
}

.success-modal p {
  margin: 0;
  color: #d1fae5;
  line-height: 1.45;
}

.navigating-text {
  color: #bbf7d0;
}

.modal-btn {
  margin-top: 14px;
  border: none;
  border-radius: 10px;
  background: #22c55e;
  color: #052e16;
  font-weight: 700;
  padding: 10px 14px;
  cursor: pointer;
}

.modal-btn:hover {
  background: #16a34a;
}

.modal-btn:disabled {
  opacity: 0.75;
  cursor: wait;
}
</style>
