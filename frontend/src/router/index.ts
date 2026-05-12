import { createRouter, createWebHistory } from 'vue-router'
import { authService } from '@/services/auth'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('../views/ResetPasswordView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/users/:userId',
      name: 'user-profile',
      component: () => import('../views/PublicProfileView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('../views/NotificationsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/history',
      name: 'watch-history',
      component: () => import('../views/WatchHistoryView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/chat',
      alias: ['/messages'],
      name: 'chat',
      component: () => import('../views/MessagesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('../views/SearchView.vue'),
    },
    {
      path: '/video/:id',
      name: 'video-player',
      component: () => import('../views/VideoPlayerView.vue'),
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('../views/UploadView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminDashboardView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to) => {
  const currentUser = authService.getCurrentUser()
  const loggedIn = Boolean(currentUser)

  if (to.meta.requiresAuth && !loggedIn) {
    return { name: 'login' }
  }

  if (to.meta.guestOnly && loggedIn) {
    return { name: 'home' }
  }

  return true
})

export default router
