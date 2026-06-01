<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <el-icon :size="28"><Reading /></el-icon>
        </div>
        <h1 class="login-title">ScholarFocus</h1>
        <p class="login-subtitle">研墨文献 · 智能研读平台</p>
      </div>

      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" label-position="top">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="loginForm.email" placeholder="请输入邮箱" size="large" class="login-input" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" show-password size="large" class="login-input" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" class="login-btn">
            登录
          </el-button>
        </el-form-item>
        <div class="login-actions">
          <router-link to="/forgot-password" class="action-link">忘记密码？</router-link>
        </div>
      </el-form>

      <div class="register-link-row">
        <span>还没有账号？</span>
        <router-link to="/register" class="register-link">立即注册</router-link>
      </div>
    </div>

    <div class="icp-footer">
      <a href="http://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">渝ICP备2026008976号</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Reading } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import bgImage from '@/assets/bg_image.jpg'

const bgUrl = `url(${bgImage})`

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const loginFormRef = ref()

const loginForm = reactive({
  email: '',
  password: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.login(loginForm.email, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  box-sizing: border-box;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: v-bind(bgUrl) no-repeat center center;
  background-size: cover;
  padding: 20px;
}

.login-card {
  width: 440px;
  max-width: 100%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-3xl);
  padding: 40px 36px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.login-logo {
  width: 52px;
  height: 52px;
  background: var(--accent-primary);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px;
  box-shadow: 0 8px 16px -4px rgba(13, 148, 136, 0.3);
  color: #ffffff;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.login-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  box-shadow: none !important;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.5);
  transition: background 0.2s ease, border-color 0.2s ease;
}

.login-input :deep(.el-input__wrapper:hover) {
  border-color: var(--teal-300);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: none !important;
}

.login-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: none !important;
  background: rgba(255, 255, 255, 0.85);
}

.login-input :deep(.el-input__wrapper:-webkit-autofill),
.login-input :deep(.el-input__wrapper:autofill) {
  box-shadow: none !important;
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  border-radius: var(--radius-lg);
  margin-top: 4px;
}

.login-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: -8px;
}

.action-link {
  font-size: 13px;
  color: var(--accent-primary);
  text-decoration: none;
}

.action-link:hover {
  text-decoration: underline;
}

.register-link-row {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
  font-size: 14px;
  color: var(--text-secondary);
}

.register-link {
  color: var(--accent-primary);
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.register-link:hover {
  text-decoration: underline;
}

.icp-footer {
  position: fixed;
  z-index: 10;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
  white-space: nowrap;
}

.icp-footer a {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  text-decoration: none;
  transition: color 0.2s ease;
}

.icp-footer a:hover {
  color: rgba(255, 255, 255, 0.9);
  text-decoration: underline;
}

/* === Mobile Responsive === */
@media (max-width: 640px) {
  .login-card {
    width: 100%;
    padding: 32px 24px;
  }

  .login-logo {
    width: 44px;
    height: 44px;
    margin-bottom: 10px;
  }

  .login-logo :deep(.el-icon) {
    font-size: 22px !important;
  }

  .login-title {
    font-size: 20px;
  }

  .login-subtitle {
    font-size: 13px;
  }

  .login-btn {
    height: 42px;
    font-size: 15px;
  }
}
</style>
