<template>
  <div class="login-page">
    <!-- 左侧：品牌视觉 + 动画角色 -->
    <div class="left-panel">
      <div class="left-top">
        <div class="brand-mark">
          <img :src="quillLogo" alt="InkLight" class="brand-img" />
        </div>
        <span class="brand-name">InkLight</span>
      </div>

      <div class="characters-area">
        <AnimatedCharacters
          :is-typing="isTyping"
          :show-password="showPassword"
          :password-length="passwordValue.length"
        />
      </div>

      <div class="typewriter-wrapper">
        <TypewriterHeader />
      </div>

      <div class="decor-blur-1" />
      <div class="decor-blur-2" />
      <div class="decor-grid" />
    </div>

    <!-- 右侧：登录表单 -->
    <div class="right-panel">
      <div class="right-decor-blur-1" />
      <div class="right-decor-blur-2" />
      <div class="right-decor-blur-3" />
      <div class="right-decor-grid" />

      <div class="form-wrapper">
        <div class="mobile-logo">
          <div class="mobile-logo-icon">
            <img :src="quillLogo" alt="InkLight" class="mobile-brand-img" />
          </div>
          <span>InkLight 研墨</span>
        </div>

        <div class="form-card">
          <div class="form-header">
            <div class="form-greeting">欢迎回来</div>
            <h1 class="form-title">登录到工作台</h1>
            <p class="form-subtitle">研墨文献 · 智能研读 · 高效写作</p>
          </div>

          <el-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="rules"
            class="login-form"
            hide-required-asterisk
            @keyup.enter="handleLogin"
          >
            <div class="field-label">邮箱</div>
            <el-form-item prop="email">
              <el-input
                v-model="loginForm.email"
                placeholder="输入您的邮箱"
                :prefix-icon="Message"
                size="large"
                @focus="isTyping = true"
                @blur="isTyping = false"
              />
            </el-form-item>

            <div class="field-label">密码</div>
            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="输入您的密码"
                :prefix-icon="Lock"
                size="large"
                @input="onPasswordInput"
                @focus="isTyping = true"
                @blur="isTyping = false"
              >
                <template #suffix>
                  <span class="eye-toggle" @click="showPassword = !showPassword">
                    <el-icon v-if="showPassword"><View /></el-icon>
                    <el-icon v-else><Hide /></el-icon>
                  </span>
                </template>
              </el-input>
            </el-form-item>

            <div v-if="errorMsg" class="error-box">
              <el-icon><WarningFilled /></el-icon>
              <span>{{ errorMsg }}</span>
            </div>

            <el-form-item style="margin-bottom: 0">
              <el-button
                type="primary"
                :loading="loading"
                class="submit-btn"
                @click="handleLogin"
              >
                {{ loading ? '登录中...' : '登录' }}
              </el-button>
            </el-form-item>
          </el-form>

          <div class="divider">
            <span>或</span>
          </div>

          <div class="signup-row">
            <span class="signup-primary">还没有账号？<router-link to="/register" class="signup-link">立即注册</router-link></span>
            <router-link to="/forgot-password" class="forgot-link">忘记密码</router-link>
          </div>
        </div>

        <div class="feature-badges">
          <div class="feature-badge">
            <span class="feature-dot" style="background: var(--accent-primary)"></span>
            AI 文献分析
          </div>
          <div class="feature-badge">
            <span class="feature-dot" style="background: var(--mint-500, #10b981)"></span>
            智能翻译
          </div>
          <div class="feature-badge">
            <span class="feature-dot" style="background: var(--amber-500, #f59e0b)"></span>
            学术写作
          </div>
        </div>
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
import { Message, Lock, View, Hide, WarningFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import AnimatedCharacters from '@/components/business/AnimatedCharacters.vue'
import TypewriterHeader from '@/components/business/TypewriterHeader.vue'
import quillLogo from '@/assets/quill.png'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const loginFormRef = ref()
const isTyping = ref(false)
const showPassword = ref(false)
const passwordValue = ref('')
const errorMsg = ref('')

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

function onPasswordInput(val: string) {
  passwordValue.value = val
}

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.login(loginForm.email, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || '邮箱或密码错误，请重新输入'
    ElMessage.error(errorMsg.value)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  position: relative;
}


/* ═══════════════════════════════════════════════════════════════
   左侧面板
   ═══════════════════════════════════════════════════════════════ */

.left-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px;
  background: linear-gradient(to right, #0f172a 0%, #162d50 25%, #1a5a70 50%, #5a7a75 78%, #9aaca0 100%);
  overflow: hidden;
}

@media (max-width: 1024px) {
  .left-panel {
    display: none;
  }
}

.left-top {
  position: absolute;
  top: 48px;
  left: 48px;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  backdrop-filter: blur(8px);
}

.brand-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.mobile-brand-img {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.brand-name {
  font-family: 'Cinzel', 'Georgia', serif;
  color: #ffffff;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 2.5px;
  text-transform: uppercase;
}

.typewriter-wrapper {
  position: absolute;
  left: 0;
  right: 0;
  top: 100px;
  z-index: 25;
  display: flex;
  justify-content: center;
  pointer-events: none;
}

.characters-area {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
}

.left-footer {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 24px;
}

.left-footer a {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
  text-decoration: none;
  transition: color 0.2s;
}

.left-footer a:hover {
  color: rgba(255, 255, 255, 0.85);
}

.decor-blur-1 {
  position: absolute;
  top: 15%;
  right: 10%;
  width: 300px;
  height: 300px;
  background: rgba(56, 189, 248, 0.2);
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: 0;
}

.decor-blur-2 {
  position: absolute;
  bottom: 10%;
  left: 5%;
  width: 400px;
  height: 400px;
  background: rgba(2, 132, 199, 0.25);
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
  z-index: 0;
}

.decor-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 1;
}

/* ═══════════════════════════════════════════════════════════════
   右侧面板
   ═══════════════════════════════════════════════════════════════ */

.right-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: linear-gradient(to right, #9aaca0 0%, #b8bdb2 18%, #d5cec2 38%, #ede8df 65%, #f5f1eb 100%);
  position: relative;
  overflow: hidden;
}

.right-decor-blur-1 {
  position: absolute;
  top: 8%;
  left: -8%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(90,117,112,0.1) 0%, rgba(2,132,199,0.04) 40%, transparent 70%);
  border-radius: 50%;
  filter: blur(70px);
  pointer-events: none;
  z-index: 0;
}

.right-decor-blur-2 {
  position: absolute;
  bottom: 5%;
  right: 8%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(16,185,129,0.06) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: 0;
}

.right-decor-blur-3 {
  position: absolute;
  top: 40%;
  right: 15%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(245,158,11,0.05) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(50px);
  pointer-events: none;
  z-index: 0;
}

.right-decor-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(42,35,30,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(42,35,30,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
  z-index: 0;
}

.form-wrapper {
  width: 100%;
  max-width: 400px;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 20px;
}

.mobile-logo {
  display: none;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 36px;
}

@media (max-width: 1024px) {
  .mobile-logo {
    display: flex;
  }
}

.mobile-logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(2,132,199,0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ─── Form Card ─── */

.form-card {
  width: 100%;
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(221,214,200,0.25);
  border-radius: 16px;
  padding: 36px 32px 28px;
  box-shadow:
    0 1px 3px rgba(42,35,30,0.04),
    0 8px 32px rgba(42,35,30,0.06);
  transition: box-shadow 0.3s;
}

.form-card:hover {
  box-shadow:
    0 1px 3px rgba(42,35,30,0.04),
    0 12px 40px rgba(42,35,30,0.08);
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.form-greeting {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.form-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  line-height: 1.3;
}

.form-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.6;
}

/* ─── Form fields ─── */

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
  letter-spacing: 0.2px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.el-input__wrapper) {
  height: 48px;
  background: rgba(255,255,255,0.7) !important;
  border: 1px solid rgba(221,214,200,0.3) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
  padding-left: 12px;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary) !important;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary) !important;
  box-shadow: 0 0 0 3px rgba(2,132,199,0.08) !important;
  background: rgba(255,255,255,0.9) !important;
}

.login-form :deep(.el-input__inner) {
  background: transparent !important;
  font-size: 14px !important;
  color: var(--text-primary) !important;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #c0c4cc !important;
}

.login-form :deep(.el-input__prefix) {
  margin-right: 8px;
}

.login-form :deep(.el-input__prefix-inner) {
  color: #b0b7c3;
  font-size: 15px;
}

.login-form :deep(.el-form-item__error) {
  font-size: 13px;
  margin-top: 4px;
  color: var(--rose-500);
}

/* ─── Password eye toggle ─── */

.eye-toggle {
  color: #9ca3af;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  transition: color 0.2s;
  padding: 0 4px;
}

.eye-toggle:hover {
  color: var(--text-secondary);
}

/* ─── Error box ─── */

.error-box {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--rose-600);
  background: var(--rose-50);
  border: 1px solid var(--rose-100);
  border-radius: 8px;
  margin-bottom: 16px;
}

/* ─── Submit button ─── */

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  background: var(--accent-primary) !important;
  border-color: var(--accent-primary) !important;
  letter-spacing: 0.5px;
}

.submit-btn:hover {
  background: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
  transform: translateY(-1px);
}

.submit-btn:active {
  opacity: 0.85;
  transform: scale(0.98);
}

/* ─── Divider ─── */

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0 0;
  font-size: 13px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(221,214,200,0.4);
}

.divider span {
  color: var(--text-muted);
  white-space: nowrap;
}

/* ─── Signup ─── */

.signup-row {
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 28px;
}

.signup-primary {
  display: block;
  line-height: 1.6;
}

.signup-link {
  color: var(--accent-primary);
  font-weight: 500;
  text-decoration: none;
}

.signup-link:hover {
  text-decoration: underline;
  color: var(--accent-hover);
}

.forgot-link {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  text-decoration: underline;
  text-underline-offset: 3px;
  text-decoration-color: rgba(42, 35, 30, 0.18);
  transition: color 0.2s, text-decoration-color 0.2s;
}

.forgot-link:hover {
  color: var(--accent-primary);
  text-decoration-color: var(--accent-primary);
}

/* ─── Feature Badges ─── */

.feature-badges {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
  justify-content: center;
}

.feature-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  background: rgba(255,255,255,0.35);
  border: 1px solid rgba(221,214,200,0.2);
  backdrop-filter: blur(4px);
  letter-spacing: 0.3px;
}

.feature-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ─── ICP footer ─── */

.icp-footer {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  text-align: center;
  white-space: nowrap;
  z-index: 10;
  pointer-events: none;
}

.icp-footer a {
  pointer-events: auto;
  display: inline-block;
  font-size: 12px;
  color: rgba(42, 35, 30, 0.3);
  text-decoration: none;
  transition: color 0.2s ease;
}

.icp-footer a:hover {
  color: rgba(42, 35, 30, 0.6);
  text-decoration: underline;
}


/* ═══════════════════════════════════════════════════════════════
   移动端响应
   ═══════════════════════════════════════════════════════════════ */

@media (max-width: 1024px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .right-panel {
    min-height: 100vh;
  }

  .form-title {
    font-size: 22px;
  }

  .form-card {
    padding: 28px 24px 24px;
  }

  .icp-footer {
    bottom: 16px;
  }
}

@media (max-width: 480px) {
  .right-panel {
    padding: 24px 16px;
  }

  .form-wrapper {
    max-width: 100%;
  }

  .form-card {
    padding: 24px 20px 20px;
    border-radius: 12px;
  }

  .form-header {
    margin-bottom: 24px;
  }

  .submit-btn {
    height: 44px;
    font-size: 14px;
  }

  .feature-badges {
    gap: 8px;
  }

  .feature-badge {
    padding: 4px 10px;
    font-size: 10px;
  }
}
</style>
