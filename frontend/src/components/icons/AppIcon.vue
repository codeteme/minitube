<script setup lang="ts">
withDefaults(
  defineProps<{
    name:
      | 'play'
      | 'search'
      | 'home'
      | 'upload'
      | 'login'
      | 'register'
      | 'user'
      | 'admin'
      | 'logout'
      | 'users'
      | 'video'
      | 'views'
      | 'bell'
      | 'check'
      | 'clock'
      | 'filter'
      | 'empty'
    size?: number
    strokeWidth?: number
  }>(),
  {
    size: 20,
    strokeWidth: 1.75,
  },
)
</script>

<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
    :stroke-width="strokeWidth"
    aria-hidden="true"
  >
    <template v-if="name === 'play'">
      <circle cx="12" cy="12" r="9" />
      <path d="m10 9 6 3-6 3z" fill="currentColor" stroke="none" />
    </template>

    <template v-else-if="name === 'search'">
      <circle cx="11" cy="11" r="6" />
      <path d="m20 20-4.35-4.35" />
    </template>

    <template v-else-if="name === 'home'">
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M6.5 10.5V20h11v-9.5" />
    </template>

    <template v-else-if="name === 'upload'">
      <path d="M12 16V6" />
      <path d="m8 10 4-4 4 4" />
      <rect x="4" y="16" width="16" height="4" rx="1.5" />
    </template>

    <template v-else-if="name === 'login'">
      <path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5" />
      <path d="M14 16l4-4-4-4" />
      <path d="M18 12H8" />
    </template>

    <template v-else-if="name === 'register'">
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20a6 6 0 0 1 12 0" />
      <path d="M19 8v6" />
      <path d="M16 11h6" />
    </template>

    <template v-else-if="name === 'user'">
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4 20a8 8 0 0 1 16 0" />
    </template>

    <template v-else-if="name === 'admin'">
      <path d="M12 3 4 7v5c0 5 3.5 7.7 8 9 4.5-1.3 8-4 8-9V7z" />
      <path d="M9.5 12.5 11.5 14.5 15 11" />
    </template>

    <template v-else-if="name === 'logout'">
      <path d="M14 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-5" />
      <path d="m10 16-4-4 4-4" />
      <path d="M6 12h10" />
    </template>

    <template v-else-if="name === 'users'">
      <circle cx="8" cy="9" r="2.7" />
      <circle cx="16.5" cy="10.5" r="2.2" />
      <path d="M2.8 19a5.2 5.2 0 0 1 10.4 0" />
      <path d="M14 19a4.2 4.2 0 0 1 7.2-2.9" />
    </template>

    <template v-else-if="name === 'video'">
      <rect x="3" y="6" width="14" height="12" rx="2" />
      <path d="m17 10 4-2v8l-4-2z" />
    </template>

    <template v-else-if="name === 'views'">
      <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" />
      <circle cx="12" cy="12" r="2.7" />
    </template>

    <template v-else-if="name === 'bell'">
      <path d="M18 16H6l1.1-1.8A5 5 0 0 0 8 11.6V10a4 4 0 1 1 8 0v1.6a5 5 0 0 0 .9 2.6z" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </template>

    <template v-else-if="name === 'check'">
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12.5 2.3 2.3 4.7-4.7" />
    </template>

    <template v-else-if="name === 'clock'">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </template>

    <template v-else-if="name === 'filter'">
      <path d="M3 6h18" />
      <path d="M6 12h12" />
      <path d="M10 18h4" />
    </template>

    <template v-else-if="name === 'empty'">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9.5h.01" />
      <path d="M14.5 9.5h.01" />
      <path d="M9 15c.9-1 2-1.5 3-1.5s2.1.5 3 1.5" />
    </template>
  </svg>
</template>
