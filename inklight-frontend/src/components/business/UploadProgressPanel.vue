<template>
  <Transition name="slide-up">
    <div v-if="items.length > 0" class="upload-progress-panel">
      <div class="panel-header">
        <span class="panel-title">
          上传队列 ({{ items.length }})
          <span v-if="activeCount > 0" class="active-count">进行中 {{ activeCount }}</span>
        </span>
        <el-button link type="primary" size="small" @click="$emit('clearCompleted')" v-if="hasCompleted">
          清除已完成
        </el-button>
        <el-button link type="primary" size="small" @click="collapsed = !collapsed">
          {{ collapsed ? '展开' : '收起' }}
        </el-button>
      </div>

      <div v-show="!collapsed" class="panel-body">
        <div v-for="item in items" :key="item.id" class="upload-item" :class="'status-' + item.status">
          <div class="item-info">
            <span class="item-icon">
              <el-icon v-if="item.status === 'success'" color="#67c23a"><CircleCheck /></el-icon>
              <el-icon v-else-if="item.status === 'failed'" color="#f56c6c"><CircleClose /></el-icon>
              <el-icon v-else-if="item.status === 'paused'" color="#e6a23c"><VideoPause /></el-icon>
              <el-icon v-else-if="item.status === 'processing'" color="#409eff" class="is-loading"><Loading /></el-icon>
              <el-icon v-else color="#409eff" class="is-loading"><UploadFilled /></el-icon>
            </span>
            <span class="item-name" :title="item.name">{{ item.name }}</span>
          </div>

          <el-progress
            v-if="item.status !== 'failed' && item.status !== 'cancelled'"
            :percentage="item.progress"
            :status="progressStatus(item.status)"
            :stroke-width="6"
            :text-inside="false"
          />

          <div class="item-status-text">
            <span v-if="item.status === 'pending'" class="text-muted">等待上传...</span>
            <span v-else-if="item.status === 'uploading'" class="text-primary">
              上传中 {{ item.chunksDone }}/{{ item.chunksTotal }}
            </span>
            <span v-else-if="item.status === 'merging'" class="text-primary">合并文件中...</span>
            <span v-else-if="item.status === 'processing'" class="text-primary">提取元数据中...</span>
            <span v-else-if="item.status === 'success'" class="text-success">上传成功</span>
            <span v-else-if="item.status === 'failed'" class="text-danger" :title="item.error">
              {{ item.error || '上传失败' }}
            </span>
            <span v-else-if="item.status === 'paused'" class="text-warning">已暂停</span>
            <span v-else-if="item.status === 'cancelled'" class="text-muted">已取消</span>
          </div>

          <div class="item-actions">
            <el-button
              v-if="item.status === 'paused'"
              link
              type="primary"
              size="small"
              @click="$emit('resume', item.id)"
            >
              继续
            </el-button>
            <el-button
              v-if="item.status === 'uploading'"
              link
              type="warning"
              size="small"
              @click="$emit('pause', item.id)"
            >
              暂停
            </el-button>
            <el-button
              v-if="item.status === 'failed'"
              link
              type="primary"
              size="small"
              @click="$emit('retry', item.id)"
            >
              重试
            </el-button>
            <el-button
              v-if="item.status === 'success' || item.status === 'failed' || item.status === 'cancelled' || item.status === 'paused'"
              link
              type="danger"
              size="small"
              @click="$emit('remove', item.id)"
            >
              移除
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { CircleCheck, CircleClose, VideoPause, Loading, UploadFilled } from '@element-plus/icons-vue'
import type { UploadItem, UploadStatus } from '@/composables/useUploadQueue'

const props = defineProps<{
  items: UploadItem[]
}>()

defineEmits<{
  (e: 'pause', id: string): void
  (e: 'resume', id: string): void
  (e: 'retry', id: string): void
  (e: 'remove', id: string): void
  (e: 'clearCompleted'): void
}>()

const collapsed = ref(false)

const activeCount = computed(
  () => props.items.filter((i) => i.status === 'uploading' || i.status === 'merging' || i.status === 'processing').length,
)

const hasCompleted = computed(
  () => props.items.some((i) => i.status === 'success' || i.status === 'failed' || i.status === 'cancelled'),
)

function progressStatus(status: UploadStatus): '' | 'success' | 'exception' | 'warning' {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'paused') return 'warning'
  return ''
}
</script>

<style scoped>
.upload-progress-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 400px;
  max-height: 480px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  z-index: 2000;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  flex-shrink: 0;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
}

.active-count {
  font-weight: 400;
  font-size: 12px;
  color: var(--el-color-primary);
  margin-left: 8px;
}

.panel-body {
  overflow-y: auto;
  max-height: 420px;
  padding: 6px 0;
}

.upload-item {
  padding: 8px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background 0.2s;
}

.upload-item:last-child {
  border-bottom: none;
}

.upload-item:hover {
  background: var(--el-fill-color-lighter);
}

.item-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.item-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.item-name {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-status-text {
  font-size: 12px;
  margin-top: 2px;
  margin-bottom: 4px;
}

.text-muted { color: var(--el-text-color-secondary); }
.text-primary { color: var(--el-color-primary); }
.text-success { color: var(--el-color-success); }
.text-danger { color: var(--el-color-danger); }
.text-warning { color: var(--el-color-warning); }

.item-actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.is-loading {
  animation: rotating 1.5s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
