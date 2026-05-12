import { mapVideoApiItemToVideoItem, type VideoApiItem, type VideoItem } from '@/types/video'
import { authService } from '@/services/auth'

const DEFAULT_HOST =
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? '127.0.0.1'
    : typeof window !== 'undefined'
      ? window.location.hostname
      : 'localhost'
const DASHBOARD_API_BASE_URL = (
  import.meta.env.VITE_DASHBOARD_API_BASE_URL || `http://${DEFAULT_HOST}:8004`
).replace(/\/$/, '')

async function enrichWithUsernames(items: VideoItem[]): Promise<void> {
  const users = await authService.getAllUsers()
  if (!users.length) return
  const userMap = new Map(users.map((u) => [u.id, u]))
  for (const item of items) {
    const user = userMap.get(item.authorId)
    if (user) {
      item.authorName = user.username
      item.authorAvatar = user.avatar
    }
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    if (body.detail) return body.detail
  } catch {
    // ignore
  }
  return `Request failed with status ${response.status}`
}

export async function fetchRecommended(userId?: string): Promise<VideoItem[]> {
  const qs = userId ? `?user_id=${encodeURIComponent(userId)}` : ''
  const response = await fetch(`${DASHBOARD_API_BASE_URL}/dashboard/recommend${qs}`)

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as { videos: VideoApiItem[] }
  const items = payload.videos.map(mapVideoApiItemToVideoItem)
  await enrichWithUsernames(items)
  return items
}

export async function searchVideos(query: string, userId?: string): Promise<VideoItem[]> {
  const qs = userId ? `&user_id=${encodeURIComponent(userId)}` : ''
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/search?q=${encodeURIComponent(query)}${qs}`,
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as { query: string; results: VideoApiItem[] }
  const items = payload.results.map(mapVideoApiItemToVideoItem)
  await enrichWithUsernames(items)
  return items
}

export async function fetchSearchSuggestions(query: string): Promise<string[]> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/search/suggestions?q=${encodeURIComponent(query)}`,
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as { query: string; suggestions: string[] }
  return payload.suggestions
}

/**
 * Fetch search history for a user.
 * @param userId - The ID of the user.
 * @param limit - The maximum number of history items to fetch (default: 10).
 * @returns A promise resolving to the user's search history.
 */
export interface UserSearchResult {
  id: number
  name: string
  role: string
}

export async function searchUsers(query: string): Promise<UserSearchResult[]> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/search/users?q=${encodeURIComponent(query)}`,
  )
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  const payload = (await response.json()) as { query: string; results: UserSearchResult[] }
  return payload.results
}

export async function fetchSearchHistory(userId: string, limit: number = 10): Promise<{ query: string; searched_at: string }[]> {
    const response = await fetch(
        `${DASHBOARD_API_BASE_URL}/search/history?user_id=${encodeURIComponent(userId)}&limit=${limit}`
    );

    if (!response.ok) {
        throw new Error(`Failed to fetch search history: ${response.statusText}`);
    }

    const payload = (await response.json()) as { user_id: string; history: { query: string; searched_at: string }[] };
    return payload.history;
}

export interface WatchedVideo extends VideoItem {
  lastWatchedAt: string
  lastPositionSeconds: number
}

/**
 * Fetch watched video history for a user.
 * @param userId - The ID of the user.
 * @param limit - The maximum number of history items to fetch (default: 20).
 * @returns A promise resolving to the user's watched video history.
 */
export async function fetchWatchedHistory(userId: string, limit: number = 20): Promise<WatchedVideo[]> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/user/history/watched?user_id=${encodeURIComponent(userId)}&limit=${limit}`,
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as {
    user_id: string
    videos: Array<VideoApiItem & { last_watched_at: string; last_position_seconds: number }>
  }
  const items = payload.videos.map((v) => ({
    ...mapVideoApiItemToVideoItem(v),
    lastWatchedAt: v.last_watched_at,
    lastPositionSeconds: v.last_position_seconds,
  }))
  await enrichWithUsernames(items)
  return items
}

/**
 * Record or update a watch event for a user.
 * @param userId - The ID of the user.
 * @param videoId - The ID of the video.
 * @param positionSeconds - The watch position in seconds.
 */
export async function recordWatchEvent(userId: string, videoId: string, positionSeconds: number = 0): Promise<void> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/user/history/watched?user_id=${encodeURIComponent(userId)}&video_id=${encodeURIComponent(videoId)}&position_seconds=${positionSeconds}`,
    { method: 'POST' },
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }
}

/**
 * Fetch subscription feed for a user.
 * @param userId - The ID of the user.
 * @param limit - The maximum number of videos to fetch (default: 20, max: 100).
 * @returns A promise resolving to videos from subscribed channels.
 */
export async function fetchSubscriptionsFeed(userId: string, limit: number = 20): Promise<VideoItem[]> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/subscriptions/feed?user_id=${encodeURIComponent(userId)}&limit=${limit}`,
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as { user_id: string; videos: VideoApiItem[] }
  const items = payload.videos.map(mapVideoApiItemToVideoItem)
  await enrichWithUsernames(items)
  return items
}

export async function fetchSubscribedChannelIds(userId: string): Promise<string[]> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/subscriptions?user_id=${encodeURIComponent(userId)}`,
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as { user_id: string; channel_user_ids: string[] }
  return payload.channel_user_ids
}

export async function fetchChannelSubscriberIds(channelUserId: string): Promise<string[]> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/subscriptions/channel-subscribers?channel_user_id=${encodeURIComponent(channelUserId)}`,
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as { channel_user_id: string; subscriber_user_ids: string[] }
  return payload.subscriber_user_ids
}

export async function subscribeToChannel(subscriberUserId: string, channelUserId: string): Promise<void> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/subscriptions?subscriber_user_id=${encodeURIComponent(subscriberUserId)}&channel_user_id=${encodeURIComponent(channelUserId)}`,
    { method: 'POST' },
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }
}

export async function unsubscribeFromChannel(subscriberUserId: string, channelUserId: string): Promise<void> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/subscriptions?subscriber_user_id=${encodeURIComponent(subscriberUserId)}&channel_user_id=${encodeURIComponent(channelUserId)}`,
    { method: 'DELETE' },
  )

  if (!response.ok) {
    throw new Error(await parseError(response))
  }
}
