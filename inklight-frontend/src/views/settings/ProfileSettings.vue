<template>
  <div class="settings-page mx-auto py-6" style="max-width:640px">
    <div class="section-bar">
      <div class="section-bar-line"></div>
      <h2 class="section-title">个人设置</h2>
      <span class="section-accent">PROFILE</span>
    </div>

    <div class="flex flex-col gap-5">
      <el-card shadow="never" class="settings-card">
        <template #header>
          <span class="settings-card-title">修改头像</span>
        </template>
        <AvatarPicker
          v-model="avatarStyle"
          :username="authStore.user?.username || ''"
          :email="authStore.user?.email || ''"
        />
        <div class="flex justify-center mt-5">
          <el-button type="primary" :loading="savingAvatar" @click="saveAvatar">保存头像</el-button>
        </div>
      </el-card>

      <el-card shadow="never" class="settings-card">
        <template #header>
          <span class="settings-card-title">修改密码</span>
        </template>
        <el-form :model="passwordForm" label-width="100px" class="max-w-[400px]">
          <el-form-item label="当前邮箱">
            <el-input :model-value="authStore.user?.email" disabled />
          </el-form-item>
          <el-form-item label="验证码" required>
            <div class="flex gap-2_5 w-full">
              <el-input v-model="passwordForm.code" placeholder="6位验证码" maxlength="6" class="flex-1" />
              <el-button type="primary" :disabled="codeCountdown > 0" :loading="sendingCode" @click="sendCode">
                {{ codeCountdown > 0 ? `${codeCountdown}s` : '发送验证码' }}
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="新密码" required>
            <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="至少8位，包含大小写字母和数字" />
          </el-form-item>
          <el-form-item label="确认密码" required>
            <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="再次输入新密码" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingPassword" @click="savePassword">修改密码</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <span class="settings-card-title">基本信息</span>
        </template>
        <el-form :model="profileForm" label-width="80px" class="max-w-[400px]">
          <el-form-item label="邮箱">
            <el-input :model-value="authStore.user?.email" disabled />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="profileForm.username" placeholder="设置用户名" maxlength="30" show-word-limit />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存信息</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <span class="settings-card-title">主题背景</span>
        </template>
        <div class="grid grid-cols-4 gap-3">
          <div
            v-for="preset in themePresets"
            :key="preset.name"
            class="theme-swatch flex flex-col items-center gap-1.5 cursor-pointer rounded-xl border-2 transition-all duration-200"
            :class="{
              'swatch-selected': currentThemeColor === preset.variables['--bg-color'],
              'swatch-idle': currentThemeColor !== preset.variables['--bg-color']
            }"
            @click="selectTheme(preset)"
          >
            <!-- Preview panel: bg + sample text + inner card -->
            <div
              class="swatch-preview"
              :style="{
                backgroundColor: preset.variables['--bg-color'],
                borderColor: preset.variables['--border-color']
              }"
            >
              <!-- Simulated card surface on the background -->
              <div
                class="swatch-card"
                :style="{
                  backgroundColor: preset.isDark ? '#252525' : 'rgba(255,255,255,0.7)',
                  color: preset.variables['--text-primary']
                }"
              >
                <span class="swatch-char">文</span>
              </div>
              <!-- Check mark for selected -->
              <div
                v-if="currentThemeColor === preset.variables['--bg-color']"
                class="swatch-check"
                :style="{ color: preset.isDark ? '#67c23a' : '#0284c7' }"
              >
                <el-icon :size="14"><Check /></el-icon>
              </div>
            </div>
            <span
              class="swatch-label"
              :class="currentThemeColor === preset.variables['--bg-color'] ? 'label-active' : 'label-idle'"
            >{{ preset.label }}</span>
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
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingPassword.value = false
  }
}
</script>

<style scoped>
</style>
