<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside
      v-if="authStore.isLoggedIn"
      :width="sidebarCollapsed ? '0' : '240px'"
      class="app-sidebar"
      :class="{ collapsed: sidebarCollapsed }"
    >
      <div class="sidebar-header">
        <div class="sidebar-logo">
          <el-icon :size="22" class="logo-icon"><Reading /></el-icon>
        </div>
        <span class="logo-text">ScholarFocus</span>
        <button class="sidebar-toggle-btn" @click="toggleSidebar" :title="sidebarCollapsed ? '展开菜单' : '折叠菜单'">
          <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
        </button>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/literature">
          <el-icon><Collection /></el-icon>
          <span>文献库</span>
        </el-menu-item>
        <el-menu-item index="/notes">
          <el-icon><Notebook /></el-icon>
          <span>文献笔记</span>
        </el-menu-item>
        <el-menu-item index="/presentation">
          <el-icon><DataAnalysis /></el-icon>
          <span>组会</span>
        </el-menu-item>
        <el-menu-item index="/calendar">
          <el-icon><Calendar /></el-icon>
          <span>阅读日历</span>
        </el-menu-item>
        <el-menu-item index="/settings/ai">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
        <el-menu-item index="/announcements">
          <el-icon><Bell /></el-icon>
          <span>系统公告</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <el-button text class="logout-btn" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </el-button>
      </div>
    </el-aside>

    <!-- 侧边栏展开按钮（折叠时显示） -->
    <div v-if="authStore.isLoggedIn && sidebarCollapsed" class="sidebar-expand-fab">
      <el-button class="expand-fab-btn" @click="toggleSidebar">
        <el-icon :size="20"><Expand /></el-icon>
      </el-button>
    </div>

    <!-- 右侧主区域 -->
    <el-container class="main-container">
      <!-- 顶部导航 -->
      <el-header v-if="authStore.isLoggedIn" class="app-header">
        <div class="header-left">
          <h2 class="page-brand">InkLight 研墨</h2>
          <div class="header-search" ref="searchRef">
            <el-input
              v-model="searchQuery"
              placeholder="搜索文献内容..."
              :prefix-icon="Search"
              size="default"
              class="search-input"
              @input="onSearchInput"
              @focus="searchFocused = true"
              clearable
              @clear="clearSearch"
            />
            <div v-if="searchFocused && (searching || searchResults.length > 0 || searchQuery)" class="search-dropdown" @mousedown.prevent>
              <div class="search-dropdown-header">
                <span class="search-dropdown-title">搜索结果</span>
                <el-button text size="small" @click="clearSearch">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
              <div v-if="searching" class="search-loading">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>搜索中...</span>
              </div>
              <template v-else>
                <el-empty v-if="searchResults.length === 0 && searchQuery" description="未找到相关结果" :image-size="48" />
                <div
                  v-for="item in searchResults"
                  :key="item.id"
                  class="search-result-item"
                  @click="goToResult(item)"
                >
                  <div class="result-header">
                    <el-icon><Document /></el-icon>
                    <span class="result-title">{{ item.literature_title }}</span>
                    <span class="result-page" v-if="item.page_number">第{{ item.page_number }}页</span>
                    <span class="result-sim">{{ (item.similarity * 100).toFixed(0) }}%</span>
                  </div>
                  <p class="result-text">{{ item.chunk_text }}</p>
                </div>
              </template>
            </div>
          </div>
        </div>
        <div class="header-right">
          <span v-if="backendOnline" class="status-badge online">
            <span class="status-dot"></span>
            后端已连接
          </span>
          <span v-else class="status-badge offline">
            <span class="status-dot"></span>
            后端未连接
          </span>
          <div class="header-divider"></div>
          <span class="user-email">{{ authStore.user?.email }}</span>
          <el-avatar :size="34" :icon="UserFilled" class="user-avatar" />
        </div>
      </el-header>

      <!-- 公告栏 -->
      <div v-if="headerAnnouncements.length > 0" class="announcement-bar">
        <el-alert
          v-for="ann in headerAnnouncements"
          :key="ann.id"
          :title="ann.title"
          :type="ann.level as any"
          :closable="true"
          show-icon
          class="announcement-alert"
          @close="dismissAlert(ann.id)"
        >
          <template #default>
            <span class="alert-content">{{ ann.content }}</span>
          </template>
        </el-alert>
      </div>

      <!-- 内容区 -->
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { searchLiterature, type SearchResultItem } from '@/api/search'
import { getActiveAnnouncements, type Announcement } from '@/api/announcement'
import {
  Reading,
  Collection,
  Notebook,
  DataAnalysis,
  Setting,
  SwitchButton,
  UserFilled,
  Search,
  Document,
  Loading,
  Close,
  Calendar,
  Bell,
  Fold,
  Expand,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const backendOnline = ref(false)

const searchQuery = ref('')
const searchResults = ref<SearchResultItem[]>([])
const searching = ref(false)
const searchFocused = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | null = null

const sidebarCollapsed = ref(localStorage.getItem('sidebar_collapsed') === '1')

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebar_collapsed', sidebarCollapsed.value ? '1' : '0')
}

const headerAnnouncements = ref<Announcement[]>([])
const dismissedIds = ref<Set<string>>(new Set(JSON.parse(localStorage.getItem('dismissedAnnouncements') || '[]')))

async function loadHeaderAnnouncements() {
  try {
    const resp = await getActiveAnnouncements()
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
  router.push({ path: `/literature/${item.literature_id}`, query })
}

onMounted(async () => {
  try {
    const res = await axios.get('/api/v1/health')
    if (res.data.status === 'ok') {
      backendOnline.value = true
    }
  } catch (e) {
    console.warn('后端未连接，请确保后端服务已启动')
  }

  if (authStore.isLoggedIn && !authStore.user) {
    authStore.fetchUser().catch(() => {
      authStore.logout()
      router.push('/login')
    })
  }

  loadHeaderAnnouncements()
})

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  background: var(--bg-secondary);
}

.app-sidebar {
  background: var(--bg-primary) !important;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width 0.3s ease;
  overflow: hidden;
  flex-shrink: 0;
}

.app-sidebar.collapsed {
  border-right: none;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-muted);
  cursor: pointer;
  margin-left: auto;
  flex-shrink: 0;
  transition: all 0.15s;
}

.sidebar-toggle-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
  background: var(--teal-50);
}

.sidebar-expand-fab {
  position: fixed;
  left: 8px;
  top: 12px;
  z-index: 1000;
}

.expand-fab-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.expand-fab-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.sidebar-logo {
  width: 36px;
  height: 36px;
  background: var(--accent-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 6px -1px rgba(13, 148, 136, 0.3);
}

.logo-icon {
  color: #ffffff;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.sidebar-menu {
  border-right: none;
  padding: 12px 8px;
  flex: 1;
}

.sidebar-menu :deep(.el-menu-item) {
  border-radius: var(--radius-md);
  margin-bottom: 2px;
  height: 44px;
  line-height: 44px;
  color: var(--text-secondary);
  font-size: 14px;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--teal-50);
  color: var(--teal-700);
  font-weight: 600;
  border-right: 3px solid var(--accent-primary);
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  color: inherit;
  font-size: 18px;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
}

.logout-btn {
  width: 100%;
  justify-content: flex-start;
  color: var(--text-secondary);
  height: 40px;
  font-size: 14px;
}

.logout-btn:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.main-container {
  flex-direction: column;
}

.announcement-bar {
  padding: 0;
  flex-shrink: 0;
}

.announcement-alert {
  border-radius: 0;
  border-bottom: 1px solid var(--border-color);
}

.announcement-alert :deep(.el-alert__content) {
  padding: 6px 0;
}

.alert-content {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  max-width: 600px;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 24px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.page-brand {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.header-search {
  position: relative;
  max-width: 400px;
  flex: 1;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  box-shadow: none;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: var(--border-color);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 1px var(--accent-primary);
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
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  max-height: 420px;
  overflow-y: auto;
  z-index: 2000;
}

.search-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  background: var(--bg-primary);
  z-index: 1;
}

.search-dropdown-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.search-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}

.search-result-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.15s;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-item:hover {
  background: var(--teal-50);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.result-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-page {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.result-sim {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-primary);
  flex-shrink: 0;
}

.result-text {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 20px;
}

.status-badge.online {
  color: var(--teal-700);
  background: var(--teal-50);
}

.status-badge.offline {
  color: var(--slate-500);
  background: var(--slate-100);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-badge.online .status-dot {
  background: var(--teal-500);
}

.status-badge.offline .status-dot {
  background: var(--slate-400);
}

.header-divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
}

.user-email {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.user-avatar {
  border: 2px solid var(--teal-100);
}

.app-main {
  padding: 0;
  background: var(--bg-secondary);
  overflow: auto;
  flex: 1;
}
</style>
