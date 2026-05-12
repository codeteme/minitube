export interface NotificationApiItem {
  notification_id: string
  type: 'new_video' | 'subscription' | 'direct_message'
  recipient_user_id: string
  title: string
  message: string
  actor_user_id: string | null
  channel_id: string | null
  video_id: string | null
  is_read: boolean
  read_at: string | null
  created_at: string | null
}

export interface NotificationListResponse {
  user_id: string
  count: number
  unread_only: boolean
  notifications: NotificationApiItem[]
}

export interface NotificationItem {
  id: string
  type: 'new_video' | 'subscription' | 'direct_message'
  title: string
  message: string
  recipientUserId: string
  actorUserId: string | null
  channelId: string | null
  videoId: string | null
  isRead: boolean
  readAt: string | null
  createdAt: string
}

export function mapNotificationApiItemToNotificationItem(item: NotificationApiItem): NotificationItem {
  return {
    id: item.notification_id,
    type: item.type,
    title: item.title,
    message: item.message,
    recipientUserId: item.recipient_user_id,
    actorUserId: item.actor_user_id,
    channelId: item.channel_id,
    videoId: item.video_id,
    isRead: item.is_read,
    readAt: item.read_at,
    createdAt: item.created_at || new Date().toISOString(),
  }
}
