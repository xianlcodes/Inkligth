<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside
      v-if="showAppLayout"
      :width="sidebarCollapsed ? '0' : '220px'"
      class="app-sidebar"
      :class="{ collapsed: sidebarCollapsed }"
    >
      <div class="sidebar-header flex items-center gap-3 px-6 py-5">
        <div class="sidebar-logo flex items-center justify-center rounded-md flex-shrink-0"
             style="background: linear-gradient(135deg, #2c6b5e, #42856f); box-shadow: 0 4px 8px -2px rgba(44,107,94,0.35)">
          <img :src="quillLogo" alt="InkLight" class="sidebar-logo-img" />
        </div>
        <span class="sidebar-logo-text font-bold whitespace-nowrap">InkLight</span>
        <button class="sidebar-toggle-btn flex items-center justify-center w-[36px] h-[36px] border rounded-lg ml-auto flex-shrink-0 cursor-pointer"
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
          <el-icon><House /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/literature">
          <el-icon><LibraryBig /></el-icon>
          <span>文献库</span>
        </el-menu-item>
        <el-menu-item index="/notes">
          <el-icon><NotebookPen /></el-icon>
          <span>文献笔记</span>
        </el-menu-item>
        <el-menu-item index="/writing">
          <el-icon><PenLine /></el-icon>
          <span>学术写作</span>
        </el-menu-item>
        <el-menu-item index="/presentation">
          <el-icon><ChartLine /></el-icon>
          <span>组会</span>
        </el-menu-item>
        <el-menu-item index="/settings/ai" data-tour="sidebar-ai">
          <el-icon><Settings /></el-icon>
          <span>AI 设置</span>
        </el-menu-item>
        <el-menu-item index="/settings/skills">
          <el-icon><Wrench /></el-icon>
          <span>技能管理</span>
        </el-menu-item>
        <el-menu-item index="/announcements">
          <el-icon><Bell /></el-icon>
          <span>系统公告</span>
        </el-menu-item>
        <el-menu-item v-if="authStore.user?.is_admin" index="/admin/statistics">
          <el-icon><LayoutGrid /></el-icon>
          <span>后台管理</span>
        </el-menu-item>
        <el-menu-item index="/tutorials">
          <el-icon><CircleHelp /></el-icon>
          <span>使用教程</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-qq-group">
        <div class="qq-group-header flex items-center gap-2 text-xs font-medium uppercase tracking-wide">
          <el-icon :size="14"><MessageSquareMore /></el-icon>
          <span>用户交流群</span>
        </div>
        <el-button size="small" text class="qq-join-btn mt-1" @click="qqDialogVisible = true">
          点击加入群聊
          <el-icon :size="12"><ArrowRight /></el-icon>
        </el-button>
      </div>

      <!-- 免费翻译额度：让用户随时看到自己的额度状态 -->
      <div class="sidebar-quota" v-if="authStore.isLoggedIn && authStore.user">
        <div class="sidebar-quota-header flex items-center gap-2 text-xs font-medium uppercase tracking-wide mb-2">
          <el-icon :size="14"><WandSparkles /></el-icon>
          <span>免费翻译额度</span>
        </div>
        <div v-if="authStore.user.has_ai_engine" class="sidebar-quota-text flex items-center gap-1_5">
          <el-icon :size="14" color="#16a34a"><CheckCheck /></el-icon>
          <span class="text-sm font-medium">自有 Key · 无限量</span>
        </div>
        <div v-if="authStore.user.has_ai_engine" class="sidebar-quota-remaining text-xs mt-1">
          免费额度剩余
          <span class="font-semibold">{{ authStore.user.free_translations ?? 0 }}</span> 篇
        </div>
        <div
          v-if="authStore.user.has_ai_engine"
          class="flex items-center gap-2 mt-1_5 mb-1"
        >
          <el-switch
            size="small"
            v-model="preferFreeQuota"
            :disabled="quotaSwitchSaving || (authStore.user.free_translations ?? 0) <= 0"
            @change="togglePreferFree"
          />
          <span class="text-xs">优先用免费额度</span>
        </div>
        <template v-else>
          <div class="sidebar-quota-text flex items-baseline gap-0_5">
            <span class="text-lg font-bold">{{ authStore.user.free_translations ?? 0 }}</span>
            <span class="text-xs">篇可翻译</span>
          </div>
          <div
            class="sidebar-quota-remaining text-xs mt-0_5"
            :class="{ warning: (authStore.user.free_translations ?? 0) <= 0 }"
          >
            {{ (authStore.user?.free_translations ?? 0) > 0 ? '上传文献即可使用' : '额度已用完' }}
          </div>
          <el-button size="small" text type="primary" class="mt-1 quota-go-btn" @click="goQuotaTarget">
            {{ (authStore.user?.free_translations ?? 0) > 0 ? '去翻译文献' : '去配置 AI Key' }}
            <el-icon :size="12"><ArrowRight /></el-icon>
          </el-button>
        </template>
      </div>

      <div class="sidebar-storage" v-if="storageInfo">
        <div class="sidebar-storage-header flex items-center gap-2 text-xs font-medium uppercase tracking-wide mb-2">
          <el-icon :size="14"><FolderOpen /></el-icon>
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


    <!-- 右侧主区域 -->
    <el-container class="main-container flex flex-col">
      <!-- 侧边栏折叠展开按钮 — 固定在左上角 -->
      <button v-if="authStore.isLoggedIn && sidebarCollapsed" class="sidebar-expand-fab" @click="toggleSidebar" title="展开菜单">
        <el-icon :size="22"><PanelLeftOpen /></el-icon>
      </button>
      <!-- 顶部导航 -->
      <el-header v-if="showAppLayout" class="app-header flex items-center justify-between h-14 px-6 flex-shrink-0">
        <div class="header-left flex items-center gap-4 flex-1 min-w-0">
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
                  <el-icon><X /></el-icon>
                </el-button>
              </div>
              <div v-if="searching" class="search-loading flex items-center justify-center gap-2 py-6">
                <el-icon class="is-loading"><LoaderCircle /></el-icon>
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
                    <el-icon><FileText /></el-icon>
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
                  <el-icon><CircleUserRound /></el-icon>
                  个人设置
                </el-dropdown-item>
                <el-dropdown-item command="storage">
                  <el-icon><FolderOpen /></el-icon>
                  个人空间
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><LogOut /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 公告栏：多条垂直轮播 + 长文本跑马灯滚动，点击查看全文 -->
      <div v-if="headerAnnouncements.length > 0" class="flex-shrink-0">
        <el-carousel
          direction="vertical"
          :autoplay="4000"
          :loop="true"
          height="44px"
          arrow="never"
          :indicator-position="headerAnnouncements.length > 1 ? '' : 'none'"
          class="ann-carousel"
        >
          <el-carousel-item v-for="ann in headerAnnouncements" :key="ann.id">
            <el-alert
              :title="ann.title"
              :type="ann.level as any"
              :closable="true"
              show-icon
              class="ann-alert rounded-none"
              @close="dismissAlert(ann.id)"
            >
              <template #default>
                <div class="ann-line">
                  <span
                    class="ann-content text-sm"
                    :class="{ 'ann-marquee': isLongText(ann.content) }"
                    title="点击查看全文"
                    @click="detailAnnouncement = ann"
                  >
                    <span class="ann-inner" :style="marqueeStyle(ann.content)">{{ ann.content }}</span>
                  </span>
                  <span
                    v-if="isLongText(ann.content)"
                    class="ann-more text-xs"
                    @click="detailAnnouncement = ann"
                  >查看全文</span>
                </div>
              </template>
            </el-alert>
          </el-carousel-item>
        </el-carousel>
      </div>

      <!-- 内容区 -->
      <el-main class="app-main flex-1 overflow-auto p-0">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
  <FeedbackButton v-if="showAppLayout" />

  <!-- QQ 群二维码弹窗 -->
  <el-dialog
    v-model="qqDialogVisible"
    title="加入用户交流群"
    width="360px"
    :close-on-click-modal="true"
    center
  >
    <div class="qq-dialog-body">
      <div class="qq-qr-wrapper">
        <img src="/QQ_QR.jpg" alt="QQ群二维码" class="qq-qr-image" />
      </div>
      <p class="qq-dialog-desc">打开 QQ 扫描二维码，加入研墨用户群</p>
      <div class="qq-dialog-number">
        <span>群号：375217209</span>
        <el-button size="small" text type="primary" @click="copyQQGroupNumber">
          <el-icon :size="14"><Copy /></el-icon>
          复制群号
        </el-button>
      </div>
    </div>
  </el-dialog>

  <!-- 公告全文弹窗 -->
  <el-dialog
    v-model="showAnnDetail"
    :title="detailAnnouncement?.title || '公告'"
    width="560px"
  >
    <div class="ann-detail-content">{{ detailAnnouncement?.content }}</div>
    <template #footer>
      <el-button @click="showAnnDetail = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useTutorial } from '@/composables/useTutorial'
import { searchLiterature, type SearchResultItem } from '@/api/search'
import { getActiveAnnouncements, getPublicAnnouncements, type Announcement } from '@/api/announcement'
import { getStorage } from '@/api/storage'
import { applyTheme, findThemeByColor } from '@/utils/themes'
import quillLogo from '@/assets/quill.png'
import CheckInPopover from '@/components/CheckInPopover.vue'
import FeedbackButton from '@/components/business/FeedbackButton.vue'
import { House, BookOpen, LibraryBig, NotebookPen, PenLine, ChartLine, Settings, LogOut, CircleUserRound, Search, FileText, LoaderCircle, X, Bell, PanelLeftClose, PanelLeftOpen, FolderOpen, LayoutGrid, CircleHelp, Wrench, MessageSquareMore, Copy, ArrowRight, WandSparkles, CheckCheck } from 'lucide-vue-next'

const route = useRoute()

const router = useRouter()
const authStore = useAuthStore()
// 登录/注册等认证页始终全屏显示（不挂侧边栏）。
// 若按 isLoggedIn 判断，登录成功的瞬间侧边栏就会出现，而路由还停在
// /login，会看到「侧边栏 + 登录页」的割裂画面。
const AUTH_PAGE_PATHS = ['/login', '/register', '/forgot-password']
const isAuthPage = computed(
  () => AUTH_PAGE_PATHS.includes(route.path) || !!route.meta.guestOnly,
)
const showAppLayout = computed(() => authStore.isLoggedIn && !isAuthPage.value)

const tutorial = useTutorial()
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

// QQ 群
const qqDialogVisible = ref(false)
const qqCopyText = ref('复制')

function copyQQGroupNumber() {
  navigator.clipboard.writeText('375217209').then(() => {
    qqCopyText.value = '已复制'
    setTimeout(() => { qqCopyText.value = '复制' }, 2000)
  }).catch(() => {
    // fallback
    const ta = document.createElement('textarea')
    ta.value = '375217209'
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    qqCopyText.value = '已复制'
    setTimeout(() => { qqCopyText.value = '复制' }, 2000)
  })
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

function goQuotaTarget() {
  router.push((authStore.user?.free_translations ?? 0) > 0 ? '/literature' : '/settings/ai')
}

// 翻译通道偏好（自有 Key 用户可切换：优先消耗免费额度，省自己的余额）
const preferFreeQuota = computed({
  get: () => !!authStore.user?.prefer_free_quota,
  set: (v: boolean) => { void togglePreferFree(v) },
})
const quotaSwitchSaving = ref(false)

async function togglePreferFree(v: boolean | string | number) {
  const prefer = v === true
  quotaSwitchSaving.value = true
  try {
    await authStore.setQuotaPreference(prefer)
    ElMessage.success(prefer ? '翻译时将优先使用免费额度，用完自动切回你的 Key' : '已恢复为优先使用你的 Key')
  } catch (e: any) {
    const raw = e.response?.data?.detail
    ElMessage.error(typeof raw === 'string' ? raw : raw?.message || '切换失败')
  } finally {
    quotaSwitchSaving.value = false
  }
}

function dismissAlert(id: string) {
  dismissedIds.value.add(id)
  localStorage.setItem('dismissedAnnouncements', JSON.stringify([...dismissedIds.value]))
  headerAnnouncements.value = headerAnnouncements.value.filter(a => a.id !== id)
}

// ── 公告滚动/全文弹窗 ──
const detailAnnouncement = ref<Announcement | null>(null)
const showAnnDetail = computed({
  get: () => detailAnnouncement.value !== null,
  set: (v: boolean) => { if (!v) detailAnnouncement.value = null },
})

/** 超过 50 字视为长通知：跑马灯滚动 + 提供「查看全文」 */
function isLongText(text?: string): boolean {
  return (text?.length ?? 0) > 50
}

/** 跑马灯时长随文本长度变化（8~40 秒），保证长文本也能完整读完 */
function marqueeStyle(text: string): Record<string, string> {
  const seconds = Math.max(8, Math.min(40, Math.round((text.length || 0) * 0.3)))
  return { animationDuration: `${seconds}s` }
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
    try {
      await authStore.fetchUser()
    } catch {
      authStore.logout()
      router.push('/login')
      loadHeaderAnnouncements()
      return
    }
  }

  if (authStore.isLoggedIn) {
    fetchStorageInfo()
    if (!tutorial.isDone()) {
      setTimeout(() => tutorial.start(), 600)
    }
  }

  loadHeaderAnnouncements()
})

// 跨页面恢复新手指引
watch(() => route.path, () => {
  tutorial.onRouteChanged()
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
/* ═══════════════════════════════════════════════════════════════
   InkLight — Global Layout
   Reading-first design: dark sidebar, warm paper content
   ═══════════════════════════════════════════════════════════════ */

.app-container {
  height: 100%;
  background: var(--bg-primary);
}

/* ── Sidebar — dark warm charcoal, reading-app feel ── */
.app-sidebar {
  background: #f8f5ef !important;
  border-right: 1px solid #e7e1d4;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width var(--transition-slow);
  overflow: hidden;
  flex-shrink: 0;
  z-index: 100;
}

.app-sidebar.collapsed {
  border-right: none;
  overflow: hidden;
}

/* ── Sidebar expand FAB ── */
.sidebar-expand-fab {
  position: fixed;
  left: 12px;
  top: 14px;
  z-index: 9999;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #d8d0c0;
  box-shadow: 0 4px 16px rgba(0,0,0,0.35);
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8f8778;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s, color 0.15s;
}

.sidebar-expand-fab:hover {
  color: #2c6b5e;
  border-color: rgba(56,189,248,0.4);
  box-shadow: 0 4px 20px rgba(44,107,94,0.35);
  transform: scale(1.08);
}

.sidebar-header {
  border-bottom: 1px solid #e7e1d4;
  background: #f1ece2;
}

.sidebar-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 20px;
  right: 20px;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(44,107,94,0.2) 50%, transparent 100%);
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
  color: #3d3a33;
  letter-spacing: -0.3px;
  font-size: 20px;
  font-weight: 700;
}

.sidebar-toggle-btn {
  border-color: #d8d0c0;
  background: rgba(255,255,255,0.06);
  color: #8f8778;
  transition: all var(--transition-fast);
}

.sidebar-toggle-btn:hover {
  color: #2c6b5e;
  border-color: rgba(56,189,248,0.3);
  background: rgba(44,107,94,0.10);
}

/* ── Sidebar menu — Element Plus overrides ── */
.sidebar-menu {
  flex: 1;
  border-right: none;
  padding: 10px 8px;
}

.sidebar-menu :deep(.el-menu) {
  background: transparent !important;
  border-right: none !important;
}

.sidebar-menu :deep(.el-menu-item) {
  border-radius: var(--radius-md);
  margin-bottom: 2px;
  height: 42px;
  line-height: 42px;
  color: #5c564c !important;
  font-size: 14px;
  font-weight: 500;
  position: relative;
  transition: all var(--transition-fast);
  background: transparent !important;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255,255,255,0.05) !important;
  color: #2c6b5e !important;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: rgba(44,107,94,0.10) !important;
  color: #2c6b5e !important;
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
  background: linear-gradient(180deg, #2c6b5e, #42856f);
  border-radius: 0 3px 3px 0;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  color: inherit !important;
  font-size: 18px;
  margin-right: 8px;
  opacity: 0.6;
}

.sidebar-menu :deep(.el-menu-item.is-active .el-icon) {
  opacity: 1;
}

/* ── Sidebar storage ── */
.sidebar-storage {
  padding: 12px 16px;
  border-top: 1px solid #e7e1d4;
  background: #f8f5ef;
  flex-shrink: 0;
}

.sidebar-storage-header {
  color: #8f8778;
}

.sidebar-storage-header .el-icon { color: #a29a8a; }

.sidebar-storage-bar {
  background: rgba(255,255,255,0.06);
  height: 5px;
  margin: 0 4px;
}

.sidebar-storage-fill {
  background: linear-gradient(90deg, #2c6b5e, #42856f);
  transition: width 0.6s ease, background 0.3s;
}

.sidebar-storage-fill.warning {
  background: linear-gradient(90deg, var(--rose-500), var(--rose-400));
}

.sidebar-storage-text {
  color: #55504a;
}

.sidebar-storage-remaining { color: #8f8778; }
.sidebar-storage-remaining.warning { color: #c26a52; font-weight: 500; }

/* ── Sidebar 免费翻译额度 ── */
.sidebar-quota {
  padding: 12px 16px;
  border-top: 1px solid #e7e1d4;
  background: #f8f5ef;
  flex-shrink: 0;
}

.sidebar-quota-header {
  color: #8f8778;
}

.sidebar-quota-header .el-icon { color: #a29a8a; }

.sidebar-quota-text {
  color: #55504a;
}

.sidebar-quota-text .text-lg { color: #2c6b5e; }

.sidebar-quota-remaining { color: #8f8778; }
.sidebar-quota-remaining.warning { color: #c26a52; font-weight: 500; }

.quota-go-btn {
  padding-left: 0 !important;
  color: #2c6b5e !important;
}

/* ── Sidebar QQ group ── */
.sidebar-qq-group {
  padding: 10px 16px;
  border-top: 1px solid #e7e1d4;
  background: #f8f5ef;
  flex-shrink: 0;
}

.sidebar-qq-group .qq-group-header {
  color: #8f8778;
}

.sidebar-qq-group .qq-group-header .el-icon {
  color: #2c6b5e;
}

.sidebar-qq-group .qq-join-btn {
  color: #2c6b5e;
  padding: 1px 0;
  font-size: 12px;
  height: auto;
  transition: color var(--transition-fast);
}

.sidebar-qq-group .qq-join-btn:hover {
  color: #2c6b5e;
}

.sidebar-qq-group .qq-join-btn .el-icon {
  font-size: 12px;
}

.sidebar-qq-group .qq-join-btn .el-icon {
  font-size: 12px;
}

/* ── QQ dialog ── */
.qq-dialog-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.qq-qr-wrapper {
  width: 220px;
  height: 220px;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  padding: 8px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
  margin-bottom: 16px;
}

.qq-qr-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;
}

.qq-dialog-desc {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin: 0 0 12px 0;
}

.qq-dialog-number {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #1f2937);
}

/* ── Header — translucent glass ── */
.app-header {
  position: relative;
  z-index: 1001;
  background: var(--bg-overlay);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  box-shadow: 0 1px 4px rgba(0,0,0,0.02);
}

.page-brand {
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #2c6b5e, #42856f);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-size: 17px;
}

/* ── Search ── */
.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  background: var(--bg-overlay);
  box-shadow: none;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: var(--border-color);
  background: var(--bg-overlay-hover);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.1) !important;
  background: var(--bg-overlay-heavy);
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: var(--bg-overlay-heavy);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 28px -8px rgba(0,0,0,0.08);
  max-height: 420px;
  overflow-y: auto;
  z-index: 9999;
  animation: fadeInUp 0.2s ease;
}

.search-dropdown-header {
  background: transparent;
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
  border: 2px solid rgba(44,107,94,0.15);
  transition: border-color 0.2s ease;
}

.user-avatar-img:hover { border-color: var(--accent-primary); }

/* ── Main content area ── */
.app-main {
  background:
    radial-gradient(ellipse at 70% 0%, rgba(2, 132, 199, 0.03) 0%, transparent 55%),
    radial-gradient(ellipse at 30% 100%, rgba(16, 185, 129, 0.02) 0%, transparent 45%),
    var(--bg-primary);
}

.alert-content { color: var(--text-secondary); }

/* ─── 公告栏：轮播 + 长文本跑马灯 ─── */
.ann-carousel {
  border-bottom: 1px solid var(--border-color, #e2e8f0);
}

.ann-alert {
  height: 44px;
  border-radius: 0;
  display: flex;
  align-items: center;
}

.ann-alert :deep(.el-alert__content) {
  flex: 1;
  min-width: 0;
  padding: 6px 10px 6px 0;
}

.ann-line {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.ann-content {
  flex: 1;
  display: block;
  overflow: hidden;
  white-space: nowrap;
  cursor: pointer;
  color: var(--text-secondary);
}

.ann-marquee {
  position: relative;
}

.ann-marquee .ann-inner {
  display: inline-block;
  white-space: nowrap;
  padding-left: 100%;
  animation: ann-scroll linear infinite;
  will-change: transform;
}

.ann-alert:hover .ann-inner {
  animation-play-state: paused;
}

@keyframes ann-scroll {
  from { transform: translateX(0); }
  to { transform: translateX(-100%); }
}

.ann-more {
  flex-shrink: 0;
  padding: 0 !important;
}

.ann-detail-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  color: var(--text-primary, #1e293b);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
