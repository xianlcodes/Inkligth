import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/tw.css'
import './styles/theme.css'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import { setRouter, setOnUnauthorized } from './api/client'

setRouter(router)

const app = createApp(App)
const pinia = createPinia()
app.use(ElementPlus)
app.use(router)
app.use(pinia)

// 注入清除 Pinia auth store 的回调，避免 401 死循环
import { useAuthStore } from '@/stores/auth'
const authStore = useAuthStore(pinia)
setOnUnauthorized(() => {
  authStore.token = null
  authStore.user = null
})

app.mount('#app')