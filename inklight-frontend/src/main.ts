import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/tw.css'
import './styles/theme.css'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import { setRouter, setOnUnauthorized } from './api/client'
import { reportClientError } from './api/clientLog'

setRouter(router)

const app = createApp(App)
const pinia = createPinia()
app.use(ElementPlus)
app.use(router)
app.use(pinia)

// ---------------------------------------------------------------------------
// 全局错误捕获：JS 异常 / 未处理的 Promise 拒绝 / Vue 渲染错误统一上报后端，
// 后端日志可按 request_id 与对应 API 请求串联（见 api/clientLog.ts）
// ---------------------------------------------------------------------------
window.addEventListener('error', (event) => {
  reportClientError({
    level: 'error',
    message: event.message || 'Script error',
    stack: event.error?.stack || null,
  })
})

window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason as { message?: string; stack?: string } | undefined
  reportClientError({
    level: 'error',
    message: reason?.message || String(reason ?? 'Unhandled promise rejection'),
    stack: reason?.stack || null,
  })
})

app.config.errorHandler = (err, _instance, info) => {
  // 保留控制台输出，便于本地调试与 devtools 定位
  console.error('[Vue errorHandler]', err, info)
  const e = err as { message?: string; stack?: string } | undefined
  reportClientError({
    level: 'error',
    message: e?.message || String(err),
    stack: e?.stack ? `${e.stack}\n[vue-info] ${info}` : `[vue-info] ${info}`,
  })
}

// 注入清除 Pinia auth store 的回调，避免 401 死循环
import { useAuthStore } from '@/stores/auth'
const authStore = useAuthStore(pinia)
setOnUnauthorized(() => {
  authStore.token = null
  authStore.user = null
})

app.mount('#app')