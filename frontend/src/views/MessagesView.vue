<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { authService } from '@/services/auth'
import { fetchSubscribedChannelIds, subscribeToChannel } from '@/services/dashboard'
import { createDirectChatSocket, isDirectMessagePayload, type DirectMessagePayload } from '@/services/chat'
import { fetchNotifications, markNotificationsRead } from '@/services/notifications'
import type { User } from '@/types/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const users = ref<User[]>([])
const directMessagePeerIds = ref<string[]>([])
const unreadDirectPeerIds = ref<string[]>([])
const selectedPeerId = ref('')
const messages = ref<DirectMessagePayload[]>([])
const inputMessage = ref('')
const status = ref('Disconnected')
const chatHint = ref('')
const quickSubscribeLoading = ref(false)
const quickSubscribeError = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
let socket: WebSocket | null = null

const peers = computed(() => {
  const currentUser = authStore.currentUser
  if (!currentUser) return []

  const allOtherUsers = users.value.filter((user) => user.id !== currentUser.id)
  let basePeers = allOtherUsers
  if (!currentUser.isAdmin) {
    const subscribedIds = new Set(currentUser.subscribedTo)
    const dmPeerIds = new Set(directMessagePeerIds.value)
    basePeers = allOtherUsers.filter((user) => subscribedIds.has(user.id) || dmPeerIds.has(user.id))
  }
  const unreadPeerIds = new Set(unreadDirectPeerIds.value)
  const sortedPeers = [...basePeers].sort(
    (a, b) => Number(unreadPeerIds.has(b.id)) - Number(unreadPeerIds.has(a.id)),
  )

  const preferredPeerId =
    (typeof route.query.peer === 'string' ? route.query.peer : '') || selectedPeerId.value
  if (!preferredPeerId) return sortedPeers

  const preferredInBase = sortedPeers.find((user) => user.id === preferredPeerId)
  if (preferredInBase) {
    return [preferredInBase, ...sortedPeers.filter((user) => user.id !== preferredPeerId)]
  }

  const preferredInAll = allOtherUsers.find((user) => user.id === preferredPeerId)
  if (!preferredInAll) return sortedPeers
  return [preferredInAll, ...sortedPeers]
})

const selectedPeer = computed(() => peers.value.find((peer) => peer.id === selectedPeerId.value) || null)
const isSelectedPeerSubscribed = computed(() => {
  const currentUser = authStore.currentUser
  if (!currentUser || !selectedPeer.value) return false
  return currentUser.subscribedTo.includes(selectedPeer.value.id)
})
const canQuickSubscribe = computed(() => {
  const currentUser = authStore.currentUser
  if (!currentUser || !selectedPeer.value) return false
  if (currentUser.id === selectedPeer.value.id) return false
  return !isSelectedPeerSubscribed.value
})

function scrollBottom() {
  if (!messagesContainer.value) return
  messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
}

function closeSocket() {
  if (socket) {
    socket.close()
    socket = null
  }
}

function connectSocket() {
  closeSocket()

  const currentUser = authStore.currentUser
  if (!currentUser || !selectedPeer.value) {
    status.value = 'Select a conversation'
    return
  }

  status.value = 'Connecting...'
  chatHint.value = ''
  messages.value = []
  socket = createDirectChatSocket({
    userId: currentUser.id,
    username: currentUser.username,
    peerId: selectedPeer.value.id,
  })

  socket.onopen = () => {
    status.value = 'Live'
  }

  socket.onmessage = async (event) => {
    try {
      const payload = JSON.parse(event.data) as
        | { type: 'history'; messages: DirectMessagePayload[] }
        | { type: 'direct_message'; [key: string]: unknown }
        | { type: 'error'; message: string }

      if (payload.type === 'history') {
        messages.value = payload.messages
        await nextTick()
        scrollBottom()
        return
      }

      if (payload.type === 'error') {
        if (payload.message.includes('only send one message')) {
          chatHint.value = 'You can send only one message unless both users subscribe to each other.'
        } else {
          status.value = payload.message
        }
        return
      }

      if (isDirectMessagePayload(payload)) {
        chatHint.value = ''
        messages.value.push(payload)
        await nextTick()
        scrollBottom()
      }
    } catch {
      // Ignore malformed websocket payload.
    }
  }

  socket.onclose = () => {
    status.value = 'Disconnected'
  }

  socket.onerror = () => {
    status.value = 'Connection error'
  }
}

function sendMessage() {
  if (!socket || socket.readyState !== WebSocket.OPEN) return
  const message = inputMessage.value.trim()
  if (!message) return

  chatHint.value = ''
  socket.send(JSON.stringify({ message }))
  inputMessage.value = ''
}

function pickPeer(peerId: string) {
  selectedPeerId.value = peerId
  quickSubscribeError.value = ''
  unreadDirectPeerIds.value = unreadDirectPeerIds.value.filter((id) => id !== peerId)
  router.replace({ name: 'chat', query: { peer: peerId } })
}

function syncSelectedPeerFromRoute() {
  const peerFromQuery = typeof route.query.peer === 'string' ? route.query.peer : ''
  if (peerFromQuery && peers.value.some((peer) => peer.id === peerFromQuery)) {
    selectedPeerId.value = peerFromQuery
    return
  }
  if (selectedPeerId.value && peers.value.some((peer) => peer.id === selectedPeerId.value)) {
    return
  }
  selectedPeerId.value = peers.value[0]?.id || ''
}

function openUserProfile(userId: string) {
  if (!userId) return
  if (authStore.currentUser?.id === userId) {
    void router.push({ name: 'profile' })
    return
  }
  void router.push({ name: 'user-profile', params: { userId } })
}

async function quickSubscribeToSelectedPeer() {
  const currentUser = authStore.currentUser
  const peer = selectedPeer.value
  if (!currentUser || !peer || isSelectedPeerSubscribed.value) return

  quickSubscribeLoading.value = true
  quickSubscribeError.value = ''
  try {
    await subscribeToChannel(currentUser.id, peer.id)
    if (!currentUser.subscribedTo.includes(peer.id)) {
      currentUser.subscribedTo = [...currentUser.subscribedTo, peer.id]
    }
  } catch (error) {
    quickSubscribeError.value = error instanceof Error ? error.message : 'Subscribe failed.'
  } finally {
    quickSubscribeLoading.value = false
  }
}

async function refreshDirectoryAndSubscriptions() {
  const currentUser = authStore.currentUser
  if (!currentUser) {
    users.value = []
    directMessagePeerIds.value = []
    unreadDirectPeerIds.value = []
    return
  }

  users.value = await authService.getAllUsers()
  try {
    const subscribedIds = await fetchSubscribedChannelIds(currentUser.id)
    if (authStore.currentUser?.id === currentUser.id) {
      authStore.currentUser.subscribedTo = subscribedIds
    }
  } catch {
    // Keep existing values when fetch fails.
  }
}

async function refreshDirectMessagePeers() {
  const currentUser = authStore.currentUser
  if (!currentUser) {
    directMessagePeerIds.value = []
    return
  }

  try {
    const items = await fetchNotifications({
      userId: currentUser.id,
      unreadOnly: false,
      limit: 200,
      offset: 0,
    })
    const ids = new Set(
      items
        .filter((item) => item.type === 'direct_message' && item.actorUserId)
        .map((item) => String(item.actorUserId))
        .filter((id) => id !== currentUser.id),
    )
    directMessagePeerIds.value = Array.from(ids)
  } catch {
    // Keep existing values when notification fetch fails.
  }
}

async function refreshUnreadDirectMessagePeers() {
  const currentUser = authStore.currentUser
  if (!currentUser) {
    unreadDirectPeerIds.value = []
    return
  }

  try {
    const items = await fetchNotifications({
      userId: currentUser.id,
      unreadOnly: true,
      limit: 200,
      offset: 0,
    })
    unreadDirectPeerIds.value = Array.from(
      new Set(
        items
          .filter((item) => item.type === 'direct_message' && item.actorUserId)
          .map((item) => String(item.actorUserId))
          .filter((id) => id !== currentUser.id),
      ),
    )
  } catch {
    // Keep existing values when notification fetch fails.
  }
}

async function markUnreadDirectMessageNotificationsForPeer(peerId: string) {
  const currentUser = authStore.currentUser
  if (!currentUser || !peerId) return

  try {
    const unreadItems = await fetchNotifications({
      userId: currentUser.id,
      unreadOnly: true,
      limit: 200,
      offset: 0,
    })
    const unreadDirectIds = unreadItems
      .filter((item) => item.type === 'direct_message' && item.actorUserId)
      .filter((item) => String(item.actorUserId) === peerId)
      .map((item) => item.id)

    if (unreadDirectIds.length === 0) return

    await markNotificationsRead({
      notificationIds: unreadDirectIds,
      recipientUserId: currentUser.id,
    })
    unreadDirectPeerIds.value = unreadDirectPeerIds.value.filter((id) => id !== peerId)
    window.dispatchEvent(new CustomEvent('notifications-updated'))
  } catch {
    // Keep chat page functional even if notification update fails.
  }
}

function handleNotificationsUpdated() {
  void Promise.all([refreshDirectMessagePeers(), refreshUnreadDirectMessagePeers()])
}

onMounted(async () => {
  await authStore.hydrate()
  await Promise.all([
    refreshDirectoryAndSubscriptions(),
    refreshDirectMessagePeers(),
    refreshUnreadDirectMessagePeers(),
  ])
  syncSelectedPeerFromRoute()

  connectSocket()

  window.addEventListener('notifications-updated', handleNotificationsUpdated)
})

onUnmounted(() => {
  closeSocket()
  window.removeEventListener('notifications-updated', handleNotificationsUpdated)
})

watch(
  () => selectedPeerId.value,
  () => {
    quickSubscribeError.value = ''
    if (selectedPeerId.value) {
      void markUnreadDirectMessageNotificationsForPeer(selectedPeerId.value)
    }
    connectSocket()
  },
)

watch(
  () => authStore.currentUser?.id,
  async () => {
    await Promise.all([
      refreshDirectoryAndSubscriptions(),
      refreshDirectMessagePeers(),
      refreshUnreadDirectMessagePeers(),
    ])
    syncSelectedPeerFromRoute()
  },
)

watch(
  () => route.query.peer,
  () => {
    syncSelectedPeerFromRoute()
  },
)
</script>

<template>
  <main class="messages-page">
    <section class="messages-shell">
      <aside class="contact-list">
        <h2><AppIcon name="users" :size="16" /> Conversations</h2>

        <button
          v-for="peer in peers"
          :key="peer.id"
          class="contact-item"
          :class="{ active: peer.id === selectedPeerId }"
          @click="pickPeer(peer.id)"
        >
          <img :src="peer.avatar" :alt="peer.username" class="avatar" />
          <div class="contact-meta">
            <p class="name">{{ peer.username }}</p>
            <small>{{ peer.email }}</small>
          </div>
          <span
            v-if="unreadDirectPeerIds.includes(peer.id)"
            class="unread-dot"
            aria-label="Unread direct messages"
            title="Unread direct messages"
          />
        </button>

        <p v-if="peers.length === 0" class="empty">No contacts available.</p>
      </aside>

      <section class="chat-panel">
        <header class="chat-header">
          <h1>
            <AppIcon name="users" :size="16" />
            {{ selectedPeer ? `Chat with ${selectedPeer.username}` : 'Chat' }}
          </h1>
          <div class="chat-header-actions">
            <button v-if="selectedPeer" type="button" class="profile-jump-btn" @click="openUserProfile(selectedPeer.id)">
              View profile
            </button>
            <button
              v-if="canQuickSubscribe"
              type="button"
              class="subscribe-jump-btn"
              :disabled="quickSubscribeLoading"
              @click="quickSubscribeToSelectedPeer"
            >
              {{ quickSubscribeLoading ? 'Subscribing...' : 'Subscribe' }}
            </button>
            <span class="status">{{ status }}</span>
          </div>
        </header>
        <p v-if="quickSubscribeError" class="action-error">{{ quickSubscribeError }}</p>
        <p v-if="chatHint" class="chat-hint">{{ chatHint }}</p>

        <div ref="messagesContainer" class="chat-messages">
          <article
            v-for="(item, index) in messages"
            :key="`${item.timestamp}-${index}`"
            class="msg"
            :class="{ mine: authStore.currentUser?.id === item.sender_user_id }"
          >
            <p class="meta">
              <button type="button" class="sender-link" @click="openUserProfile(item.sender_user_id)">
                {{ item.sender_username }}
              </button>
              <small>{{ new Date(item.timestamp).toLocaleTimeString() }}</small>
            </p>
            <p>{{ item.message }}</p>
          </article>

          <p v-if="messages.length === 0" class="empty">No messages yet.</p>
        </div>

        <form class="composer" @submit.prevent="sendMessage">
          <input
            v-model="inputMessage"
            type="text"
            placeholder="Say hi..."
            maxlength="2000"
            :disabled="status !== 'Live'"
          />
          <button type="submit" :disabled="!inputMessage.trim() || status !== 'Live'">Send</button>
        </form>
      </section>
    </section>
  </main>
</template>

<style scoped>
.messages-page {
  max-width: 1320px;
  margin: 0 auto;
  padding: 20px 16px 34px;
}

.messages-shell {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 12px;
}

.contact-list,
.chat-panel {
  border: 1px solid var(--border-default);
  border-radius: 14px;
  background: var(--bg-1);
}

.contact-list {
  padding: 12px;
}

.contact-list h2 {
  color: var(--text-main);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.contact-item {
  width: 100%;
  border: 1px solid var(--border-default);
  background: var(--bg-2);
  color: var(--text-body);
  border-radius: 10px;
  padding: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}

.contact-item.active {
  border-color: var(--accent-outline-soft);
  background: var(--accent-wash-hover);
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 999px;
}

.contact-meta {
  min-width: 0;
}

.name {
  color: var(--text-main);
}

.unread-dot {
  margin-left: auto;
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #ef4444;
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.18);
}

.contact-item small,
.empty {
  color: var(--text-muted);
}

.chat-panel {
  display: grid;
  grid-template-rows: auto 1fr auto;
}

.chat-header {
  padding: 12px;
  border-bottom: 1px solid var(--border-faint);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.chat-header h1 {
  color: var(--text-main);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 18px;
}

.chat-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.profile-jump-btn {
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: var(--bg-3);
  color: var(--text-soft);
  font-size: 12px;
  padding: 3px 10px;
  cursor: pointer;
}

.profile-jump-btn:hover {
  border-color: var(--accent-outline-soft);
  color: var(--text-main);
}

.subscribe-jump-btn {
  border: 1px solid var(--accent-outline-soft);
  border-radius: 999px;
  background: var(--accent-wash);
  color: var(--text-main);
  font-size: 12px;
  padding: 3px 10px;
  cursor: pointer;
}

.subscribe-jump-btn:hover {
  border-color: var(--accent-outline);
  background: var(--accent-wash-hover);
}

.subscribe-jump-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status {
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  color: var(--text-soft);
  font-size: 12px;
  padding: 2px 8px;
}

.chat-hint {
  margin: 10px 12px 0;
  border: 1px solid rgba(245, 158, 11, 0.45);
  background: rgba(245, 158, 11, 0.12);
  color: var(--warn-text);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
}

.action-error {
  margin: 10px 12px 0;
  color: var(--accent-text-soft);
  font-size: 13px;
}

.chat-messages {
  height: 480px;
  overflow-y: auto;
  padding: 12px;
}

.msg {
  max-width: 72%;
  margin-bottom: 10px;
  border: 1px solid var(--border-default);
  background: var(--bg-3);
  border-radius: 10px;
  padding: 8px;
}

.msg.mine {
  margin-left: auto;
  border-color: rgba(239, 68, 68, 0.6);
  background: var(--accent-wash-hover);
}

.meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.sender-link {
  border: none;
  background: transparent;
  color: var(--text-main);
  font-size: 12px;
  font-weight: 700;
  padding: 0;
  margin: 0;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.sender-link:hover {
  color: var(--accent-text-strong);
}

.msg p:last-child {
  margin-top: 3px;
  color: var(--text-body);
  white-space: pre-wrap;
  word-break: break-word;
}

.composer {
  border-top: 1px solid var(--border-faint);
  padding: 10px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.composer input {
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--bg-4);
  color: var(--text-main);
  padding: 9px 12px;
}

.composer button {
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  color: var(--text-inverse);
  padding: 8px 14px;
}

.composer button:disabled,
.composer input:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 980px) {
  .messages-shell {
    grid-template-columns: 1fr;
  }

  .chat-messages {
    height: 360px;
  }
}
</style>
