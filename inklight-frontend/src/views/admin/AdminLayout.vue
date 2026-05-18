<template>
  <el-container class="admin-container">
    <el-aside width="240px" class="admin-sidebar">
      <div class="admin-sidebar-header">
        <el-icon :size="22"><Setting /></el-icon>
        <span>后台管理</span>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="admin-menu"
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
      </el-menu>
      <div class="admin-sidebar-footer">
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
import { Setting, DataAnalysis, User, Bell, Tools, Document, Notebook, Back } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
</script>

<style scoped>
.admin-container {
  height: 100%;
  background: var(--bg-secondary);
}

.admin-sidebar {
  background: var(--bg-primary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.admin-sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
}

.admin-menu {
  flex: 1;
  border-right: none;
}

.admin-sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
}

.admin-main {
  padding: 24px 32px;
  overflow-y: auto;
}
</style>
