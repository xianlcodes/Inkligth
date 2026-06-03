import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { clearAuth } from '@/api/client'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Landing',
      component: () => import('@/views/Landing.vue'),
      meta: { title: '研墨 - 专业文献阅读平台' }
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
      path: '/task/storage',
      name: 'StorageOverview',
      component: () => import('@/views/task/StorageOverview.vue'),
      meta: { title: '个人空间', requiresAuth: true }
    },
    {
      path: '/settings/ai',
      name: 'AiEngineSettings',
      component: () => import('@/views/settings/AiEngineSettings.vue'),
      meta: { title: 'AI 引擎设置', requiresAuth: true }
    },
    {
      path: '/settings/profile',
      name: 'ProfileSettings',
      component: () => import('@/views/settings/ProfileSettings.vue'),
      meta: { title: '个人设置', requiresAuth: true }
    },
    {
      path: '/announcements',
      name: 'Announcements',
      component: () => import('@/views/announcements/AnnouncementList.vue'),
      meta: { title: '系统公告', requiresAuth: true }
    },
    {
      path: '/admin',
      component: () => import('@/views/admin/AdminLayout.vue'),
      meta: { requiresAuth: true, adminOnly: true },
      children: [
        {
          path: '',
          redirect: '/admin/statistics',
        },
        {
          path: 'statistics',
          name: 'AdminStatistics',
          component: () => import('@/views/admin/Statistics.vue'),
          meta: { title: '数据统计', requiresAuth: true, adminOnly: true },
        },
        {
          path: 'users',
          name: 'AdminUsers',
          component: () => import('@/views/admin/UserManagement.vue'),
          meta: { title: '用户管理', requiresAuth: true, adminOnly: true },
        },
        {
          path: 'notifications',
          name: 'AdminNotifications',
          component: () => import('@/views/admin/NotificationManagement.vue'),
          meta: { title: '通知管理', requiresAuth: true, adminOnly: true },
        },
        {
          path: 'config',
          name: 'AdminConfig',
          component: () => import('@/views/admin/SystemConfig.vue'),
          meta: { title: '系统配置', requiresAuth: true, adminOnly: true },
        },
        {
          path: 'logs',
          name: 'AdminLogs',
          component: () => import('@/views/admin/OperationLogs.vue'),
          meta: { title: '操作日志', requiresAuth: true, adminOnly: true },
        },
        {
          path: 'tutorials',
          name: 'AdminTutorials',
          component: () => import('@/views/admin/TutorialManager.vue'),
          meta: { title: '使用教程管理', requiresAuth: true, adminOnly: true },
        },
        {
          path: 'feedback',
          name: 'AdminFeedback',
          component: () => import('@/views/admin/FeedbackManagement.vue'),
          meta: { title: '用户反馈', requiresAuth: true, adminOnly: true },
        },
      ],
    },
    {
      path: '/tutorials',
      name: 'TutorialList',
      component: () => import('@/views/tutorial/TutorialList.vue'),
      meta: { title: '使用教程', requiresAuth: true },
    },
    {
      path: '/tutorials/:id',
      name: 'TutorialView',
      component: () => import('@/views/tutorial/TutorialView.vue'),
      meta: { title: '教程详情', requiresAuth: true },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/auth/Register.vue'),
      meta: { title: '注册', guestOnly: true }
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/Login.vue'),
      meta: { title: '登录', guestOnly: true }
    },
    {
      path: '/forgot-password',
      name: 'ForgotPassword',
      component: () => import('@/views/auth/ForgotPassword.vue'),
      meta: { title: '忘记密码' }
    },
    {
      path: '/terms-of-service',
      name: 'TermsOfService',
      component: () => import('@/views/legal/TermsOfService.vue'),
      meta: { title: '用户服务协议' }
    },
    {
      path: '/privacy-policy',
      name: 'PrivacyPolicy',
      component: () => import('@/views/legal/PrivacyPolicy.vue'),
      meta: { title: '隐私政策' }
    }
  ]
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 如果有 token 但未加载用户信息，先验证 token 有效性
  if (authStore.token && !authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      // token 无效或已过期，本地清除登录状态
      authStore.token = null
      authStore.user = null
      clearAuth()
    }
  }

  const isLoggedIn = authStore.isLoggedIn

  if (to.meta.requiresAuth && !isLoggedIn) {
    next('/login')
  } else if (to.meta.adminOnly && !authStore.user?.is_admin) {
    next('/')
  } else if (to.meta.guestOnly && isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
