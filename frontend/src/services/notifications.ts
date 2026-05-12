import {
  mapNotificationApiItemToNotificationItem,
  type NotificationApiItem,
  type NotificationItem,
  type NotificationListResponse,
} from '@/types/notification'

const DEFAULT_HOST =
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? '127.0.0.1'
    : typeof window !== 'undefined'
      ? window.location.hostname
      : 'localhost'
const COMM_API_BASE_URL = (
  import.meta.env.VITE_COMM_API_BASE_URL || `http://${DEFAULT_HOST}:8002`
).replace(/\/$/, '')

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    if (body.detail) return body.detail
  } catch {
    // Ignore JSON parse failures and use HTTP fallback below.
  }

  return `Request failed with status ${response.status}`
}

export async function fetchNotifications(options: {
  userId: string
  unreadOnly?: boolean
  limit?: number
  offset?: number
}): Promise<NotificationItem[]> {
  const params = new URLSearchParams({
    user_id: options.userId,
    unread_only: String(Boolean(options.unreadOnly)),
    limit: String(options.limit ?? 50),
    offset: String(options.offset ?? 0),
  })

  const response = await fetch(`${COMM_API_BASE_URL}/comm/notifications?${params.toString()}`)

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const payload = (await response.json()) as NotificationListResponse
  return payload.notifications.map(mapNotificationApiItemToNotificationItem)
}

export async function markNotificationsRead(options: {
  notificationIds: string[]
  recipientUserId?: string
}): Promise<void> {
  const response = await fetch(`${COMM_API_BASE_URL}/comm/notifications/read`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      notification_ids: options.notificationIds,
      recipient_user_id: options.recipientUserId,
    }),
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }
}

type StreamEnvelope =
  | { type: 'connected'; user_id: string }
  | { type: 'error'; message: string }
  | { type: 'notification_created'; notification: NotificationApiItem }

export function connectNotificationStream(options: {
  userId: string
  onNotification: (item: NotificationItem) => void
  onStatusChange?: (status: 'connected' | 'disconnected' | 'error') => void
}): () => void {
  const explicitWsBase = (import.meta.env.VITE_COMM_WS_BASE_URL || '').trim()
  const wsBase = explicitWsBase
    ? explicitWsBase.replace(/\/$/, '')
    : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://localhost:8002`

  const query = new URLSearchParams({ user_id: options.userId })
  const socket = new WebSocket(`${wsBase}/comm/notifications/stream?${query.toString()}`)
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null

  socket.onopen = () => {
    heartbeatTimer = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send('ping')
      }
    }, 20000)
    options.onStatusChange?.('connected')
  }

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data) as StreamEnvelope
      if (payload.type === 'notification_created') {
        options.onNotification(mapNotificationApiItemToNotificationItem(payload.notification))
      }
    } catch {
      // Ignore malformed payloads.
    }
  }

  socket.onerror = () => {
    options.onStatusChange?.('error')
  }

  socket.onclose = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
    options.onStatusChange?.('disconnected')
  }

  return () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
    socket.close()
  }
}
