<template>
  <div class="profile-settings">
    <div class="page-header">
      <h2 class="page-title">个人设置</h2>
    </div>

    <div class="settings-content">
      <el-card class="settings-card" shadow="never">
        <template #header>
          <span class="card-title">修改头像</span>
        </template>
        <AvatarPicker
          v-model="avatarStyle"
          :username="authStore.user?.username || ''"
          :email="authStore.user?.email || ''"
        />
        <div class="avatar-actions">
          <el-button type="primary" :loading="savingAvatar" @click="saveAvatar">
            保存头像
          </el-button>
        </div>
      </el-card>

      <el-card class="settings-card" shadow="never">
        <template #header>
          <span class="card-title">修改密码</span>
        </template>
        <el-form :model="passwordForm" label-width="100px" class="profile-form">
          <el-form-item label="当前邮箱">
            <el-input :model-value="authStore.user?.email" disabled />
          </el-form-item>
          <el-form-item label="验证码" required>
            <div class="code-row">
              <el-input
                v-model="passwordForm.code"
                placeholder="6位验证码"
                maxlength="6"
                class="code-input"
              />
              <el-button
                type="primary"
                :disabled="codeCountdown > 0"
                :loading="sendingCode"
                @click="sendCode"
              >
                {{ codeCountdown > 0 ? `${codeCountdown}s` : '发送验证码' }}
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="新密码" required>
            <el-input
              v-model="passwordForm.newPassword"
              type="password"
              show-password
              placeholder="至少8位，包含大小写字母和数字"
            />
          </el-form-item>
          <el-form-item label="确认密码" required>
            <el-input
              v-model="passwordForm.confirmPassword"
              type="password"
              show-password
              placeholder="再次输入新密码"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingPassword" @click="savePassword">
              修改密码
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="settings-card" shadow="never">
        <template #header>
          <span class="card-title">基本信息</span>
        </template>
        <el-form :model="profileForm" label-width="80px" class="profile-form">
          <el-form-item label="邮箱">
            <el-input :model-value="authStore.user?.email" disabled />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="profileForm.username" placeholder="设置用户名" maxlength="30" show-word-limit />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingProfile" @click="saveProfile">
              保存信息
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    <el-card class="settings-card" shadow="never">
        <template #header>
          <span class="card-title">主题背景</span>
        </template>
        <div class="theme-preset-grid">
          <div
            v-for="preset in themePresets"
            :key="preset.name"
            class="theme-preset-item"
            :class="{ active: currentThemeColor === preset.variables['--bg-color'] }"
            @click="selectTheme(preset)"
          >
            <div
              class="theme-preset-swatch"
              :style="{ backgroundColor: preset.variables['--bg-color'] }"
            >
              <el-icon v-if="currentThemeColor === preset.variables['--bg-color']" class="theme-preset-check">
                <Check />
              </el-icon>
            </div>
            <span class="theme-preset-name">{{ preset.label }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'
import AvatarPicker from '@/components/business/AvatarPicker.vue'
import { themePresets, DEFAULT_THEME_COLOR, type ThemePreset } from '@/utils/themes'

const authStore = useAuthStore()

const currentThemeColor = computed(() => authStore.user?.theme_color || DEFAULT_THEME_COLOR)

async function selectTheme(preset: ThemePreset) {
  if (currentThemeColor.value === preset.variables['--bg-color']) return
  try {
    await authStore.updateProfile({ theme_color: preset.variables['--bg-color'] })
    ElMessage.success(`已切换至「${preset.label}」`)
  } catch {
    ElMessage.error('保存失败')
  }
}

const avatarStyle = ref<string | null>(null)
const savingAvatar = ref(false)
const savingProfile = ref(false)
const savingPassword = ref(false)
const sendingCode = ref(false)
const codeCountdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const profileForm = ref({
  username: '',
})

const passwordForm = ref({
  code: '',
  newPassword: '',
  confirmPassword: '',
})

onMounted(() => {
  avatarStyle.value = authStore.user?.avatar_style || null
  profileForm.value.username = authStore.user?.username || ''
})

async function saveAvatar() {
  savingAvatar.value = true
  try {
    await authStore.updateProfile({ avatar_style: avatarStyle.value || undefined })
    ElMessage.success('头像已更新')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingAvatar.value = false
  }
}

async function saveProfile() {
  savingProfile.value = true
  try {
    await authStore.updateProfile({ username: profileForm.value.username || undefined })
    ElMessage.success('信息已更新')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingProfile.value = false
  }
}

async function sendCode() {
  sendingCode.value = true
  try {
    await apiClient.post('/users/me/send-password-change-code')
    ElMessage.success('验证码已发送至您的邮箱')
    codeCountdown.value = 60
    countdownTimer = setInterval(() => {
      codeCountdown.value--
      if (codeCountdown.value <= 0 && countdownTimer) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    sendingCode.value = false
  }
}

async function savePassword() {
  if (!passwordForm.value.code) {
    ElMessage.warning('请输入验证码')
    return
  }
  if (!passwordForm.value.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  if (passwordForm.value.newPassword.length < 8) {
    ElMessage.warning('密码至少8位')
    return
  }

  savingPassword.value = true
  try {
    await apiClient.post('/users/me/change-password', {
      code: passwordForm.value.code,
      new_password: passwordForm.value.newPassword,
    })
    ElMessage.success('密码修改成功，请重新登录')
    passwordForm.value = { code: '', newPassword: '', confirmPassword: '' }
    setTimeout(() => {
      authStore.logout()
      window.location.href = '/login'
    }, 1500)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    savingPassword.value = false
  }
}
</script>

<style scoped>
.profile-settings {
  max-width: 640px;
  margin: 0 auto;
  padding: 24px 0;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-card {
  border-radius: var(--radius-lg);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.avatar-actions {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.profile-form {
  max-width: 400px;
}

.code-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.code-input {
  flex: 1;
}

.theme-preset-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.theme-preset-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 12px 8px;
  border-radius: var(--radius-lg);
  border: 2px solid transparent;
  transition: all 0.2s;
}

.theme-preset-item:hover {
  background: var(--bg-tertiary);
  border-color: var(--border-color);
}

.theme-preset-item.active {
  border-color: var(--accent-primary);
  background: var(--teal-50);
}

.theme-preset-swatch {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.theme-preset-check {
  font-size: 22px;
  color: var(--accent-primary);
}

.theme-preset-name {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.theme-preset-item.active .theme-preset-name {
  color: var(--accent-primary);
  font-weight: 600;
}
</style>