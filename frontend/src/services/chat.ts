export interface DirectMessagePayload {
  type: 'direct_message'
  room_key: string
  sender_user_id: string
  sender_username: string
  peer_user_id: string
  message: string
  timestamp: string
}

export interface VideoChatMessagePayload {
  type: 'chat_message' | 'system'
  video_id: string
  user_id: string
  username: string
  message: string
  timestamp: string
}

export function isDirectMessagePayload(value: unknown): value is DirectMessagePayload {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  return (
    candidate.type === 'direct_message' &&
    typeof candidate.room_key === 'string' &&
    typeof candidate.sender_user_id === 'string' &&
    typeof candidate.sender_username === 'string' &&
    typeof candidate.peer_user_id === 'string' &&
    typeof candidate.message === 'string' &&
    typeof candidate.timestamp === 'string'
  )
}

export function isVideoChatMessagePayload(value: unknown): value is VideoChatMessagePayload {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  return (
    (candidate.type === 'chat_message' || candidate.type === 'system') &&
    typeof candidate.video_id === 'string' &&
    typeof candidate.user_id === 'string' &&
    typeof candidate.username === 'string' &&
    typeof candidate.message === 'string' &&
    typeof candidate.timestamp === 'string'
  )
}

function commWsBaseUrl(): string {
  const explicitWsBase = (import.meta.env.VITE_COMM_WS_BASE_URL || '').trim()
  if (explicitWsBase) return explicitWsBase.replace(/\/$/, '')
  return `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://localhost:8002`
}

export function createDirectChatSocket(options: {
  userId: string
  username: string
  peerId: string
}): WebSocket {
  const query = new URLSearchParams({
    user_id: options.userId,
    username: options.username,
    peer_id: options.peerId,
  })
  return new WebSocket(`${commWsBaseUrl()}/comm/direct-chat?${query.toString()}`)
}

export function createRealtimeVideoChatSocket(options: {
  videoId: string
  userId: string
  username: string
}): WebSocket {
  const query = new URLSearchParams({
    video_id: options.videoId,
    user_id: options.userId,
    username: options.username,
  })
  return new WebSocket(`${commWsBaseUrl()}/comm/real-time-chat?${query.toString()}`)
}
