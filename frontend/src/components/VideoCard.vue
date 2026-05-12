<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { VideoItem } from '@/types/video'
import { formatViews, timeAgo } from '@/services/video-format'
import AppIcon from '@/components/icons/AppIcon.vue'

const props = defineProps<{ video: VideoItem }>()
const router = useRouter()

function openVideo() {
  void router.push(`/video/${props.video.id}`)
}

function openAuthorProfile(event?: Event) {
  event?.stopPropagation()
  void router.push(`/users/${props.video.authorId}`)
}

function handleCardKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openVideo()
  }
}
</script>

<template>
  <article
    class="video-card"
    role="link"
    tabindex="0"
    @click="openVideo"
    @keydown="handleCardKeydown"
  >
    <div class="thumb-wrap">
      <img :src="video.thumbnail" :alt="video.title" class="thumb" />
      <span class="duration">{{ video.duration }}</span>
    </div>

    <div class="meta">
      <button
        type="button"
        class="author-trigger"
        :aria-label="`Open ${video.authorName} profile`"
        @click="openAuthorProfile"
      >
        <img :src="video.authorAvatar" :alt="video.authorName" class="avatar" />
      </button>
      <div class="meta-text">
        <h3>{{ video.title }}</h3>
        <button type="button" class="author author-trigger" @click="openAuthorProfile">
          {{ video.authorName }}
        </button>
        <p class="sub">
          <span><AppIcon name="views" :size="13" /> {{ formatViews(video.views) }} views</span>
          <span>•</span>
          <span><AppIcon name="clock" :size="13" /> {{ timeAgo(video.uploadDate) }}</span>
        </p>
      </div>
    </div>
  </article>
</template>

<style scoped>
.video-card {
  display: grid;
  gap: 10px;
  text-decoration: none;
  cursor: pointer;
}

.thumb-wrap {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 14px;
  overflow: hidden;
  background: var(--bg-7);
}

.thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 180ms ease;
}

.video-card:hover .thumb {
  transform: scale(1.03);
}

.duration {
  position: absolute;
  right: 8px;
  bottom: 8px;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 6px;
  color: var(--text-inverse);
  background: rgba(0, 0, 0, 0.72);
}

.meta {
  display: grid;
  grid-template-columns: 38px 1fr;
  gap: 10px;
}

.author-trigger {
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 999px;
  object-fit: cover;
}

.meta-text h3 {
  color: var(--text-main);
  font-size: 14px;
  line-height: 1.3;
  margin-bottom: 2px;
}

.author {
  color: var(--text-soft);
  font-size: 13px;
  display: inline-flex;
  width: fit-content;
}

.author:hover,
.author-trigger:hover .avatar {
  opacity: 0.88;
}

.sub {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 12px;
}

.sub span {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
</style>
