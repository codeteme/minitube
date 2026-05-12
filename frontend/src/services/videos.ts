import { mapVideoApiItemToVideoItem, type VideoApiItem, type VideoItem } from '@/types/video'
import { authService } from '@/services/auth'

const DEFAULT_HOST =
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? '127.0.0.1'
    : typeof window !== 'undefined'
      ? window.location.hostname
      : 'localhost'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || `http://${DEFAULT_HOST}:8000`).replace(/\/$/, '')

function getAuthHeader(): Record<string, string> {
  const token = authService.getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    if (body.detail) return body.detail
  } catch {
    // Ignore JSON parse failures and use HTTP fallback below.
  }

  return `Request failed with status ${response.status}`
}

export async function fetchVideos(): Promise<VideoItem[]> {
  const [response, users] = await Promise.all([
    fetch(`${API_BASE_URL}/videos`),
    authService.getAllUsers(),
  ])

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const userMap = new Map(users.map((u) => [u.id, u]))
  const payload = (await response.json()) as VideoApiItem[]
  return payload.map((v) => {
    const item = mapVideoApiItemToVideoItem(v)
    const user = userMap.get(String(v.uploader_id))
    if (user) {
      item.authorName = user.username
      item.authorAvatar = user.avatar
    }
    return item
  })
}

export async function fetchVideoById(videoId: string): Promise<VideoItem> {
  const [response, users] = await Promise.all([
    fetch(`${API_BASE_URL}/videos/${videoId}`),
    authService.getAllUsers(),
  ])

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as VideoApiItem
  const item = mapVideoApiItemToVideoItem(payload)
  const userMap = new Map(users.map((u) => [u.id, u]))
  const user = userMap.get(String(payload.uploader_id))
  if (user) {
    item.authorName = user.username
    item.authorAvatar = user.avatar
  }
  return item
}

export async function fetchVideosByUploader(userId: string): Promise<VideoItem[]> {
  const items = await fetchVideos()
  return items.filter((item) => item.authorId === userId)
}

export interface VideoTranscriptItem {
  video_id: string
  status: 'pending' | 'queued' | 'processing' | 'ready' | 'failed'
  transcript_text: string
  source: string | null
  error_message: string | null
  language: string | null
  updated_at: string | null
}

export async function fetchVideoTranscript(videoId: string): Promise<VideoTranscriptItem> {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/transcript`)

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return (await response.json()) as VideoTranscriptItem
}

export interface UploadVideoPayload {
  file: File
  title: string
  description: string
  category: string
  tags: string
  uploaderId: number
  thumbnailUrl?: string
  durationSeconds?: number
}

export async function uploadVideo(payload: UploadVideoPayload): Promise<VideoItem> {
  const formData = new FormData()
  formData.append('file', payload.file)
  formData.append('title', payload.title)
  formData.append('description', payload.description)
  formData.append('category', payload.category)
  formData.append('tags', payload.tags)
  formData.append('uploader_id', String(payload.uploaderId))
  formData.append('thumbnail_url', payload.thumbnailUrl || '')
  formData.append('duration_seconds', String(payload.durationSeconds || 0))

  const response = await fetch(`${API_BASE_URL}/videos/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const video = (await response.json()) as VideoApiItem
  const item = mapVideoApiItemToVideoItem(video)
  const currentUser = authService.getCurrentUser()
  if (currentUser) {
    item.authorName = currentUser.username
    item.authorAvatar = currentUser.avatar
  }
  return item
}

export interface UpdateVideoPayload {
  videoId: string
  title?: string
  description?: string
  category?: string
  tags?: string
}

export async function updateVideo(payload: UpdateVideoPayload): Promise<VideoItem> {
  const formData = new FormData()
  if (payload.title !== undefined) formData.append('title', payload.title)
  if (payload.description !== undefined) formData.append('description', payload.description)
  if (payload.category !== undefined) formData.append('category', payload.category)
  if (payload.tags !== undefined) formData.append('tags', payload.tags)

  const response = await fetch(`${API_BASE_URL}/videos/${payload.videoId}`, {
    method: 'PATCH',
    headers: getAuthHeader(),
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const video = (await response.json()) as VideoApiItem
  const item = mapVideoApiItemToVideoItem(video)
  const currentUser = authService.getCurrentUser()
  if (currentUser) {
    item.authorName = currentUser.username
    item.authorAvatar = currentUser.avatar
  }
  return item
}

export async function recordView(videoId: string): Promise<void> {
  await fetch(`${API_BASE_URL}/videos/${videoId}/view`, { method: 'POST' })
}

export async function deleteVideo(videoId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}`, {
    method: 'DELETE',
    headers: getAuthHeader(),
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }
}
