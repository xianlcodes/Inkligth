<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside
      v-if="authStore.isLoggedIn"
      :width="sidebarCollapsed ? '0' : '220px'"
      class="app-sidebar"
      :class="{ collapsed: sidebarCollapsed }"
    >
      <div class="sidebar-header flex items-center gap-3 px-6 py-5">
        <div class="sidebar-logo flex items-center justify-center rounded-md flex-shrink-0"
             style="background: linear-gradient(135deg, #0284c7, #0ea5e9); box-shadow: 0 4px 8px -2px rgba(2,132,199,0.35)">
          <img :src="quillLogo" alt="InkLight" class="sidebar-logo-img" />
        </div>
        <span class="sidebar-logo-text font-bold whitespace-nowrap">InkLight</span>
        <button class="sidebar-toggle-btn flex items-center justify-center w-[30px] h-[30px] border rounded-md ml-auto flex-shrink-0 cursor-pointer"
                @click="toggleSidebar" :title="sidebarCollapsed ? '展开菜单' : '折叠菜单'">
          <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
        </button>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/literature">
          <el-icon><Collection /></el-icon>
          <span>文献库</span>
        </el-menu-item>
        <el-menu-item index="/notes">
          <el-icon><Notebook /></el-icon>
          <span>文献笔记</span>
        </el-menu-item>
        <el-menu-item index="/writing">
          <el-icon><EditPen /></el-icon>
          <span>学术写作</span>
        </el-menu-item>
        <el-menu-item index="/presentation">
          <el-icon><DataAnalysis /></el-icon>
          <span>组会</span>
        </el-menu-item>
        <el-menu-item index="/settings/ai">
          <el-icon><Setting /></el-icon>
          <span>AI 设置</span>
        </el-menu-item>
        <el-menu-item index="/settings/skills">
          <el-icon><Tools /></el-icon>
          <span>技能管理</span>
        </el-menu-item>
        <el-menu-item index="/announcements">
          <el-icon><Bell /></el-icon>
          <span>系统公告</span>
        </el-menu-item>
        <el-menu-item v-if="authStore.user?.is_admin" index="/admin/statistics">
          <el-icon><Management /></el-icon>
          <span>后台管理</span>
        </el-menu-item>
        <el-menu-item index="/tutorials">
          <el-icon><Help /></el-icon>
          <span>使用教程</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-storage" v-if="storageInfo">
        <div class="sidebar-storage-header flex items-center gap-2 text-xs font-medium uppercase tracking-wide mb-2">
          <el-icon :size="14"><FolderOpened /></el-icon>
          <span>存储空间</span>
        </div>
        <div class="sidebar-storage-bar h-[5px] rounded-full overflow-hidden">
          <div
            class="sidebar-storage-fill h-full rounded-full transition-all duration-500"
            :class="{ warning: storageWarning }"
            :style="{ width: storagePercent + '%' }"
          ></div>
        </div>
        <div class="sidebar-storage-text flex items-baseline gap-0_5 mt-1_5">
          <span class="text-sm font-semibold">{{ formatBytes(storageInfo.used_space) }}</span>
          <span class="text-xs">/ {{ formatBytes(storageInfo.total_space) }}</span>
        </div>
        <div class="sidebar-storage-remaining text-xs mt-0_5" :class="{ warning: storageWarning }">
          剩余 {{ formatBytes(storageInfo.remaining_space) }}
        </div>
      </div>
    </el-aside>

    <!-- 侧边栏展开按钮 -->
    <div v-if="authStore.isLoggedIn && sidebarCollapsed" class="sidebar-expand-fab">
      <el-button class="expand-fab-btn" @click="toggleSidebar">
        <el-icon :size="20"><Expand /></el-icon>
      </el-button>
    </div>

    <!-- 右侧主区域 -->
    <el-container class="main-container flex flex-col">
      <!-- 顶部导航 -->
      <el-header v-if="authStore.isLoggedIn" class="app-header flex items-center justify-between h-14 px-6 flex-shrink-0">
        <div class="header-left flex items-center gap-4 flex-1 min-w-0">
          <h2 class="page-brand text-base font-bold flex-shrink-0 m-0">InkLight 研墨</h2>
          <div v-if="showSearchBar" class="header-search relative w-[300px]" ref="searchRef">
            <el-input
              v-model="searchQuery"
              placeholder="搜索本地文献内容..."
              :prefix-icon="Search"
              size="default"
              class="search-input"
              @input="onSearchInput"
              @focus="searchFocused = true"
              clearable
              @clear="clearSearch"
            />
            <div v-if="searchFocused && (searching || searchResults.length > 0 || searchQuery)" class="search-dropdown" @mousedown.prevent>
              <div class="search-dropdown-header flex items-center justify-between px-4 py-2_5 border-b sticky top-0 z-10">
                <span class="text-xs font-semibold uppercase tracking-wider">搜索结果</span>
                <el-button text size="small" @click="clearSearch">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
              <div v-if="searching" class="search-loading flex items-center justify-center gap-2 py-6">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span class="text-sm">搜索中...</span>
              </div>
              <template v-else>
                <el-empty v-if="searchResults.length === 0 && searchQuery" description="未找到相关结果" :image-size="48" />
                <div
                  v-for="item in searchResults"
                  :key="item.id"
                  class="search-result-item px-4 py-3 border-b last:border-b-0 cursor-pointer transition-colors duration-150"
                  @click="goToResult(item)"
                >
                  <div class="result-header flex items-center gap-1_5 mb-1_5">
                    <el-icon><Document /></el-icon>
                    <span class="result-title flex-1 text-sm font-semibold truncate">{{ item.literature_title }}</span>
                    <span class="result-page text-xs px-1_5 py-0_5 rounded-sm flex-shrink-0" v-if="item.page_number">第{{ item.page_number }}页</span>
                    <span class="result-sim text-xs font-semibold flex-shrink-0">{{ (item.similarity * 100).toFixed(0) }}%</span>
                  </div>
                  <p class="result-text text-xs leading-normal m-0 line-clamp-2">{{ item.chunk_text }}</p>
                </div>
              </template>
            </div>
          </div>
        </div>
        <div class="header-right flex items-center gap-4">
          <span class="user-email text-sm font-medium">{{ authStore.user?.username || authStore.user?.email }}</span>
          <CheckInPopover
            :visible="checkInVisible"
            @update:visible="checkInVisible = $event"
            @checked-in="onCheckedIn"
          />
          <el-dropdown trigger="click" @command="handleUserCommand">
            <img
              :src="authStore.avatarUrl"
              alt="头像"
              class="user-avatar-img rounded-full object-cover cursor-pointer"
              @error="onAvatarError"
            />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><UserFilled /></el-icon>
                  个人设置
                </el-dropdown-item>
                <el-dropdown-item command="storage">
                  <el-icon><FolderOpened /></el-icon>
                  个人空间
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 公告栏 -->
      <div v-if="headerAnnouncements.length > 0" class="flex-shrink-0">
        <el-alert
          v-for="ann in headerAnnouncements"
          :key="ann.id"
          :title="ann.title"
          :type="ann.level as any"
          :closable="true"
          show-icon
          class="rounded-none border-b"
          @close="dismissAlert(ann.id)"
        >
          <template #default>
            <span class="alert-content text-sm max-w-[600px] block truncate">{{ ann.content }}</span>
          </template>
        </el-alert>
      </div>

      <!-- 内容区 -->
      <el-main class="app-main flex-1 overflow-auto p-0">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
  <FeedbackButton v-if="authStore.isLoggedIn" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { searchLiterature, type SearchResultItem } from '@/api/search'
import { getActiveAnnouncements, getPublicAnnouncements, type Announcement } from '@/api/announcement'
import { getStorage } from '@/api/storage'
import { applyTheme, findThemeByColor } from '@/utils/themes'
import quillLogo from '@/assets/quill.png'
import CheckInPopover from '@/components/CheckInPopover.vue'
import FeedbackButton from '@/components/business/FeedbackButton.vue'
import {
  HomeFilled,
  Reading,
  Collection,
  Notebook,
  EditPen,
  DataAnalysis,
  Setting,
  SwitchButton,
  UserFilled,
  Search,
  Document,
  Loading,
  Close,
  Bell,
  Fold,
  Expand,
  FolderOpened,
  Management,
  Help,
  Tools,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const searchQuery = ref('')
const searchResults = ref<SearchResultItem[]>([])
const searching = ref(false)
const searchFocused = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | null = null

const showSearchBar = computed(() => {
  const path = route.path
  return path.startsWith('/dashboard') || path.startsWith('/literature')
})

const sidebarCollapsed = ref(localStorage.getItem('sidebar_collapsed') === '1')
const checkInVisible = ref(false)

const storageInfo = ref<{ total_space: number; used_space: number; remaining_space: number } | null>(null)

const storagePercent = computed(() => {
  if (!storageInfo.value || storageInfo.value.total_space <= 0) return 0
  return Math.round((storageInfo.value.used_space / storageInfo.value.total_space) * 100)
})

const storageWarning = computed(() => {
  if (!storageInfo.value || storageInfo.value.total_space <= 0) return false
  return storageInfo.value.remaining_space / storageInfo.value.total_space < 0.1
})

function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0.00 MB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

async function fetchStorageInfo() {
  try {
    const data = await getStorage()
    storageInfo.value = data
  } catch {
    storageInfo.value = null
  }
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebar_collapsed', sidebarCollapsed.value ? '1' : '0')
}

const headerAnnouncements = ref<Announcement[]>([])
const dismissedIds = ref<Set<string>>(new Set(JSON.parse(localStorage.getItem('dismissedAnnouncements') || '[]')))

async function loadHeaderAnnouncements() {
  try {
    const fetcher = authStore.isLoggedIn ? getActiveAnnouncements : getPublicAnnouncements
    const resp = await fetcher()
    headerAnnouncements.value = (resp.data.items || [])
      .filter(a => !dismissedIds.value.has(a.id))
      .slice(0, 3)
  } catch {
    headerAnnouncements.value = []
  }
}

function dismissAlert(id: string) {
  dismissedIds.value.add(id)
  localStorage.setItem('dismissedAnnouncements', JSON.stringify([...dismissedIds.value]))
  headerAnnouncements.value = headerAnnouncements.value.filter(a => a.id !== id)
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(() => doSearch(), 400)
}

async function doSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const resp = await searchLiterature(searchQuery.value.trim(), 8)
    searchResults.value = resp.data.data.items
  } catch {
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  searchFocused.value = false
}

function goToResult(item: SearchResultItem) {
  clearSearch()
  const query: Record<string, string> = {}
  if (item.page_number) query.page = String(item.page_number)
  if (item.chunk_index !== undefined) query.chunk = String(item.chunk_index)
  router.push({ path: `/read/${item.literature_id}`, query })
}

onMounted(async () => {
  if (authStore.isLoggedIn && !authStore.user) {
    authStore.fetchUser().catch(() => {
      authStore.logout()
      router.push('/login')
    })
  }

  if (authStore.isLoggedIn) {
    fetchStorageInfo()
  }

  loadHeaderAnnouncements()
})

watch(() => authStore.isLoggedIn, (loggedIn) => {
  loadHeaderAnnouncements()
  if (loggedIn) {
    fetchStorageInfo()
  }
})

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

function handleUserCommand(command: string) {
  if (command === 'profile') {
    router.push('/settings/profile')
  } else if (command === 'storage') {
    router.push('/task/storage')
  } else if (command === 'logout') {
    handleLogout()
  }
}

function onAvatarError(e: Event) {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

function onCheckedIn() {
  checkInVisible.value = false
}

watchEffect(() => {
  const color = authStore.user?.theme_color
  const preset = findThemeByColor(color)
  applyTheme(preset)
})
</script>

<style scoped>
.app-container {
  height: 100%;
  background: var(--bg-secondary);
}

.app-sidebar {
  background: var(--bg-primary) !important;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width var(--transition-slow);
  overflow: hidden;
  flex-shrink: 0;
  z-index: 100;
}

.app-sidebar.collapsed { border-right: none; }

.sidebar-header {
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-tertiary);
}

.sidebar-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 20px;
  right: 20px;
  height: 1px;
  background: var(--gradient-primary);
  opacity: 0.2;
}

.sidebar-logo {
  width: 44px;
  height: 44px;
}

.sidebar-logo-img {
  width: 28px;
  height: 28px;
  object-fit: contain;
  filter: brightness(0) invert(1);
}

.sidebar-logo-text {
  color: var(--text-primary);
  letter-spacing: -0.5px;
  font-size: 20px;
}

.sidebar-toggle-btn {
  border-color: var(--border-color);
  background: var(--bg-primary);
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.sidebar-toggle-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
  background: var(--sky-50);
}

.sidebar-expand-fab {
  position: fixed;
  left: 8px;
  top: 12px;
  z-index: 1000;
  animation: fadeIn var(--transition-slow) ease;
}

.expand-fab-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-md);
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: all var(--transition-base);
}

.expand-fab-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
  box-shadow: var(--shadow-lg);
  transform: scale(1.05);
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  padding: 12px 8px;
}

.sidebar-menu :deep(.el-menu-item) {
  border-radius: var(--radius-md);
  margin-bottom: 2px;
  height: 44px;
  line-height: 44px;
  color: var(--text-secondary);
  font-size: 14px;
  position: relative;
  transition: all var(--transition-fast);
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--bg-hover);
  color: var(--accent-primary);
  font-weight: 600;
}

.sidebar-menu :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--gradient-primary);
  border-radius: 0 2px 2px 0;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  color: inherit;
  font-size: 18px;
  margin-right: 8px;
}

.sidebar-storage {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  flex-shrink: 0;
}

.sidebar-storage-header {
  color: var(--text-tertiary);
}

.sidebar-storage-header .el-icon { color: var(--text-muted); }

.sidebar-storage-bar {
  background: var(--bg-tertiary);
  height: 5px;
  margin: 0 4px;
}

.sidebar-storage-fill {
  background: var(--gradient-primary);
  transition: width 0.6s ease, background 0.3s;
}

.sidebar-storage-fill.warning {
  background: linear-gradient(90deg, var(--rose-500), var(--rose-400));
}

.sidebar-storage-text {
  color: var(--text-primary);
}

.sidebar-storage-remaining { color: var(--text-muted); }
.sidebar-storage-remaining.warning { color: var(--rose-600); font-weight: 500; }

.app-header {
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.page-brand {
  letter-spacing: var(--tracking-tight);
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  box-shadow: none;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: var(--border-color);
  background: var(--bg-hover);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.1) !important;
  background: var(--bg-primary);
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-dropdown);
  max-height: 420px;
  overflow-y: auto;
  z-index: 2000;
  animation: fadeInUp 0.2s ease;
}

.search-dropdown-header {
  background: var(--bg-primary);
}

.search-loading { color: var(--text-muted); }

.search-result-item { border-color: var(--border-color); }
.search-result-item:hover { background: var(--sky-50); }

.result-title { color: var(--text-primary); }
.result-page { color: var(--text-muted); background: var(--bg-tertiary); }
.result-sim { color: var(--accent-primary); }
.result-text { color: var(--text-secondary); }

.user-email { color: var(--text-secondary); }

.user-avatar-img {
  width: 34px;
  height: 34px;
  border: 2px solid var(--sky-100);
  transition: border-color 0.2s ease;
}

.user-avatar-img:hover { border-color: var(--accent-primary); }

.app-main { background: var(--bg-secondary); }

.alert-content { color: var(--text-secondary); }
</style>
