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
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/dashboard/Dashboard.vue'),
      meta: { title: '首页', requiresAuth: true }
    },
    {
      path: '/read/:id',
      name: 'Reading',
      component: () => import('@/views/literature/Reader.vue'),
      meta: { title: '阅读', requiresAuth: true }
    },
    {
      path: '/argument/:id',
      name: 'ArgumentReview',
      component: () => import('@/views/literature/ArgumentReview.vue'),
      meta: { title: '论文评审', requiresAuth: true }
    },
    {
      path: '/notes',
      name: 'Notes',
      component: () => import('@/views/notes/NoteList.vue'),
      meta: { title: '笔记', requiresAuth: true }
    },
    {
      path: '/writing',
      name: 'WritingAssistant',
      component: () => import('@/views/writing/WritingAssistant.vue'),
      meta: { title: '学术写作助手', requiresAuth: true }
    },
    {
      path: '/presentation',
      name: 'Presentation',
      component: () => import('@/views/presentation/PreMeeting.vue'),
      meta: { title: '组会', requiresAuth: true }
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
      path: '/settings/skills',
      name: 'SkillsSettings',
      component: () => import('@/views/settings/SkillsSettings.vue'),
      meta: { title: '技能管理', requiresAuth: true }
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
    },
    {
      path: '/index.html',
      redirect: '/'
    }
  ]
})

// 路由切换时更新页面标题和 meta 描述
const siteDescriptions: Record<string, string> = {
  Landing: '研墨InkLight - AI驱动的学术文献阅读与管理平台，支持PDF文献管理、AI翻译、AI摘要分析、笔记管理、组会汇报大纲生成。',
  Dashboard: '研墨InkLight - 首页仪表板，查看阅读统计、每日精选论文和个人阅读进度。',
  Login: '登录研墨账号，使用AI学术文献阅读与管理功能。支持DeepSeek、OpenAI、通义千问等AI引擎。',
  Register: '注册研墨账号，免费使用AI学术文献阅读与翻译平台。支持PDF管理、AI翻译、笔记标注等功能。',
  ForgotPassword: '找回研墨账号密码。输入注册邮箱，接收验证码重置密码。',
  WritingAssistant: '研墨学术写作助手 - 选择写作技能，AI按技能规则辅助你的论文写作。',
  TermsOfService: '阅读研墨InkLight用户服务协议，了解平台使用规则、用户权利义务和免责声明。',
  PrivacyPolicy: '阅读研墨InkLight隐私政策，了解个人信息收集、使用和保护规则。',
}

router.afterEach((to) => {
  const title = (to.meta.title as string) || '研墨 - 专业文献阅读平台'
  document.title = title + ' - 研墨'

  // 动态更新 meta description
  const name = to.name as string
  const desc = siteDescriptions[name] || siteDescriptions.Landing
  let meta = document.querySelector('meta[name="description"]')
  if (meta) {
    meta.setAttribute('content', desc)
  } else {
    meta = document.createElement('meta')
    meta.setAttribute('name', 'description')
    meta.setAttribute('content', desc)
    document.head.appendChild(meta)
  }
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth) {
    // 需要登录的页面，无论 user 是否已加载，都验证 token 有效性
    if (authStore.token) {
      try {
        await authStore.fetchUser()
      } catch {
        // token 无效或已过期，清除状态并跳转到登录页
        authStore.token = null
        authStore.user = null
        clearAuth()
        next('/login')
        return
      }
    } else {
      next('/login')
      return
    }
  }

  // 已登录用户访问首页 → 跳转仪表盘（避免 Landing.vue 一闪而过）
  if (to.path === '/' && authStore.isLoggedIn) {
    next('/dashboard')
    return
  }

  if (to.meta.adminOnly && !authStore.user?.is_admin) {
    next('/')
    return
  }

  if (to.meta.guestOnly && authStore.isLoggedIn) {
    next('/')
    return
  }

  next()
})

export default router
