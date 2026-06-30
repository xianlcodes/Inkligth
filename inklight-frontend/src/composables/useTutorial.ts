import { ref, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { driver, type Driver, type DriveStep } from 'driver.js'
import 'driver.js/dist/driver.css'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

export interface TutorialStep extends DriveStep {
  route?: string
}

const steps: TutorialStep[] = [
  {
    route: '/dashboard',
    element: '[data-tour="sidebar-ai"]',
    popover: {
      title: '配置 AI 引擎',
      description: '首先配置 AI Key，所有翻译与分析功能都依赖它。使用教程中可获取免费的 API Key。',
      side: 'right',
      align: 'start',
    },
  },
  {
    route: '/settings/ai',
    element: '.ai-settings-header .el-button--primary',
    popover: {
      title: '添加 AI 引擎',
      description: '点击添加引擎，填入 API Key、接口地址和模型名称。没有 Key？教程中有免费获取方式。',
      side: 'bottom',
      align: 'start',
    },
  },
  {
    route: '/literature',
    element: '.page-header .el-button--primary',
    popover: {
      title: '上传文献',
      description: '上传 PDF 文献，系统会自动提取标题、作者和摘要。支持批量拖拽上传。',
      side: 'bottom',
      align: 'start',
    },
  },
  {
    route: '/literature',
    element: '.page-header',
    popover: {
      title: '开始阅读',
      description: '上传文献后，在列表中点击文献标题即可进入阅读器，支持 PDF 预览、标注和全文搜索。',
      side: 'bottom',
      align: 'start',
    },
  },
  {
    popover: {
      title: '一切就绪',
      description: '选中文本即可翻译，全文支持原位翻译，还能 AI 分析论文摘要和创新点。开始你的高效研读吧。',
      side: 'bottom',
      align: 'start',
    },
  },
]

let driverInstance: Driver | null = null
const active = ref(false)
const pendingStep = ref(-1)

export function useTutorial() {
  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()

  function buildDriver(fromStep: number) {
    if (driverInstance) {
      driverInstance.destroy()
      driverInstance = null
    }

    driverInstance = driver({
      showProgress: true,
      progressText: '{{current}} / {{total}}',
      showButtons: ['next', 'previous'],
      nextBtnText: '下一步',
      prevBtnText: '上一步',
      doneBtnText: '完成',
      steps,
      popoverClass: 'inklight-driver-popover',
      stageRadius: 16,
      stagePadding: 16,
      animate: true,
      allowClose: false,
      overlayOpacity: 0.5,
      onNextClick: () => {
        const idx = driverInstance?.getActiveIndex?.() ?? fromStep
        const next = steps[idx + 1]

        if (!next) {
          driverInstance?.destroy()
          driverInstance = null
          router.push('/dashboard')
          return
        }

        const nextRoute = next.route || ''
        const currentPath = route.path

        const routeChanged = nextRoute && nextRoute !== '/read'
          ? currentPath !== nextRoute
          : nextRoute === '/read'
            ? !currentPath.startsWith('/read')
            : false

        if (routeChanged) {
          pendingStep.value = idx + 1
          driverInstance?.destroy()
          driverInstance = null
          router.push(nextRoute)
        } else {
          driverInstance?.moveNext()
        }
      },
      onDestroyed: () => {
        if (pendingStep.value === -1) {
          active.value = false
          markDone()
        }
      },
    })

    driverInstance.drive(fromStep)
  }

  function start() {
    if (isDone()) return

    active.value = true
    pendingStep.value = -1

    const firstRoute = steps[0].route
    if (firstRoute && route.path !== firstRoute) {
      pendingStep.value = 0
      router.push(firstRoute)
      return
    }

    buildDriver(0)
  }

  function restart() {
    clearDone()
    active.value = true
    pendingStep.value = -1

    const firstRoute = steps[0].route
    if (firstRoute && route.path !== firstRoute) {
      pendingStep.value = 0
      router.push(firstRoute)
      return
    }

    buildDriver(0)
  }

  function onRouteChanged() {
    if (!active.value || pendingStep.value < 0) return

    const stepIdx = pendingStep.value
    pendingStep.value = -1

    nextTick(() => {
      setTimeout(() => {
        buildDriver(stepIdx)
      }, 400)
    })
  }

  async function markDone() {
    try {
      await apiClient.patch('/users/me/tutorial', { tutorial_completed: true })
      if (authStore.user) {
        authStore.user.tutorial_completed = true
      }
    } catch {
      // 网络异常时仍标记本地状态，避免无限弹出
      if (authStore.user) {
        authStore.user.tutorial_completed = true
      }
    }
  }

  async function clearDone() {
    try {
      await apiClient.patch('/users/me/tutorial', { tutorial_completed: false })
      if (authStore.user) {
        authStore.user.tutorial_completed = false
      }
    } catch {
      if (authStore.user) {
        authStore.user.tutorial_completed = false
      }
    }
  }

  function isDone(): boolean {
    return authStore.user?.tutorial_completed === true
  }

  return { active, isDone, start, restart, onRouteChanged }
}
