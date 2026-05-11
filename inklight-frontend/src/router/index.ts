import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/literature'
    },
    {
      path: '/literature',
      name: 'Literature',
      component: () => import('@/views/literature/LiteratureList.vue'),
      meta: { title: '文献库', requiresAuth: true }
    },
    {
      path: '/read/:id',
      name: 'Reading',
      component: () => import('@/views/literature/Reader.vue'),
      meta: { title: '阅读', requiresAuth: true }
    },
    {
      path: '/notes',
      name: 'Notes',
      component: () => import('@/views/notes/NoteList.vue'),
      meta: { title: '笔记', requiresAuth: true }
    },
    {
      path: '/presentation',
      name: 'Presentation',
      component: () => import('@/views/presentation/PreMeeting.vue'),
      meta: { title: '组会', requiresAuth: true }
    },
    {
      path: '/calendar',
      name: 'Calendar',
      component: () => import('@/views/stats/ReadingCalendar.vue'),
      meta: { title: '阅读日历', requiresAuth: true }
    },
    {
      path: '/settings/ai',
      name: 'AiEngineSettings',
      component: () => import('@/views/settings/AiEngineSettings.vue'),
      meta: { title: 'AI 引擎设置', requiresAuth: true }
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/Login.vue'),
      meta: { title: '登录', guestOnly: true }
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const isLoggedIn = authStore.isLoggedIn

  if (to.meta.requiresAuth && !isLoggedIn) {
    next('/login')
  } else if (to.meta.guestOnly && isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
