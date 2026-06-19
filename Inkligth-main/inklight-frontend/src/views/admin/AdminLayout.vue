<template>
  <el-container class="h-full" style="background:var(--bg-secondary)">
    <el-aside width="240px" class="flex flex-col border-r" style="background:var(--bg-primary);border-color:var(--border-color)">
      <div class="flex items-center gap-2_5 px-5 py-5 text-lg font-bold text-slate-800 border-b" style="border-color:var(--border-color)">
        <el-icon :size="22"><Setting /></el-icon>
        <span>后台管理</span>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="flex-1 border-r-0"
      >
        <el-menu-item index="/admin/statistics">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据统计</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/notifications">
          <el-icon><Bell /></el-icon>
          <span>通知管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/config">
          <el-icon><Tools /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        <el-menu-item index="/admin/logs">
          <el-icon><Document /></el-icon>
          <span>操作日志</span>
        </el-menu-item>
        <el-menu-item index="/admin/tutorials">
          <el-icon><Notebook /></el-icon>
          <span>使用教程管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/feedback">
          <el-icon><ChatDotRound /></el-icon>
          <span>用户反馈</span>
        </el-menu-item>
      </el-menu>
      <div class="px-4 py-3 border-t" style="border-color:var(--border-color)">
        <el-button text @click="router.push('/')">
          <el-icon><Back /></el-icon>
          <span>返回前台</span>
        </el-button>
      </div>
    </el-aside>
    <el-main class="admin-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { Setting, DataAnalysis, User, Bell, Tools, Document, Notebook, ChatDotRound, Back } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
</script>

<style scoped>
.admin-main {
  padding: 24px 32px;
  overflow-y: auto;
}
</style>
