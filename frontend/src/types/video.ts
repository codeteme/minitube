export interface VideoItem {
  id: string
  title: string
  description: string
  thumbnail: string
  videoUrl: string
  authorId: string
  authorName: string
  authorAvatar: string
  views: number
  likes: number
  uploadDate: string
  duration: string
  tags: string[]
  category: string
}

export interface VideoApiItem {
  id: string
  title: string
  description: string
  category: string
  tags: string[]
  thumbnail_url: string
  uploader_id: number
  original_filename: string
  saved_filename: string
  content_type: string
  size: number
  path: string
  views: number
  likes: number
  duration_seconds: number
  playback_url: string
  created_at?: string
}

export interface SearchHistoryItem {
  query: string
  searched_at: string
}

const DEFAULT_THUMBNAIL =
  'https://images.unsplash.com/photo-1492619375914-88005aa9e8fb?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080'
const DEFAULT_HOST =
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? '127.0.0.1'
    : typeof window !== 'undefined'
      ? window.location.hostname
      : 'localhost'
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || `http://${DEFAULT_HOST}:8000`
).replace(/\/$/, '')

function formatDuration(totalSeconds: number): string {
  if (totalSeconds <= 0) return '00:00'
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export function mapVideoApiItemToVideoItem(video: VideoApiItem): VideoItem {
  const createdAt = video.created_at || new Date().toISOString()
  const thumbnailUrl = video.thumbnail_url.startsWith('http')
    ? video.thumbnail_url
    : `${API_BASE_URL}${video.thumbnail_url}`

  return {
    id: video.id,
    title: video.title,
    description: video.description,
    thumbnail: video.thumbnail_url ? thumbnailUrl : DEFAULT_THUMBNAIL,
    videoUrl: video.playback_url,
    authorId: String(video.uploader_id),
    authorName: 'Unknown User',
    authorAvatar: '/default-avatar.svg',
    views: video.views,
    likes: video.likes,
    uploadDate: createdAt,
    duration: formatDuration(video.duration_seconds),
    tags: video.tags,
    category: video.category,
  }
}
