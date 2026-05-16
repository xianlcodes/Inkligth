<template>
  <el-popover
    :visible="visible"
    placement="bottom-end"
    :width="340"
    trigger="manual"
    @update:visible="$emit('update:visible', $event)"
  >
    <template #reference>
      <span class="check-in-trigger" @click="$emit('update:visible', !visible)">
        <el-icon :size="18"><Calendar /></el-icon>
        <span class="check-in-text">签到</span>
      </span>
    </template>

    <div class="check-in-popover">
      <div class="check-in-header">
        <h3>每日签到</h3>
        <span v-if="status?.checked_in_today" class="checked-badge">今日已签到</span>
      </div>

      <div class="streak-info">
        <div class="streak-days">
          <span class="streak-num">{{ status?.streak_days || 0 }}</span>
          <span class="streak-label">连续签到天数</span>
        </div>
        <div v-if="!status?.checked_in_today && status?.today_reward" class="today-reward">
          今日签到可得 <strong>{{ formatBytes(status.today_reward) }}</strong>
        </div>
      </div>

      <el-button
        type="primary"
        :disabled="status?.checked_in_today"
        :loading="checkingIn"
        class="check-in-btn"
        @click="handleCheckIn"
      >
        {{ status?.checked_in_today ? '今日已签到' : '立即签到' }}
      </el-button>

      <div class="month-calendar">
        <div class="calendar-title">本月签到日历</div>
        <div class="calendar-grid">
          <span
            v-for="day in calendarDays"
            :key="day.date"
            class="calendar-day"
            :class="{
              'is-checked': day.checked,
              'is-today': day.isToday,
              'is-future': day.isFuture,
            }"
          >
            {{ day.day }}
          </span>
        </div>
      </div>

      <div class="reward-rules">
        <div class="rules-title">奖励规则</div>
        <div class="rule-item">连续 3 天：+10MB</div>
        <div class="rule-item">连续 7 天：+20MB</div>
        <div class="rule-item">连续 30 天：+100MB</div>
        <div class="rule-item">连续 90 天：+500MB</div>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Calendar } from '@element-plus/icons-vue'
import { doCheckIn, getCheckInStatus, type CheckInStatus } from '@/api/checkIn'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'checked-in'): void
}>()

const status = ref<CheckInStatus | null>(null)
const checkingIn = ref(false)

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return (bytes / (1024 * 1024)).toFixed(0) + 'MB'
  }
  return (bytes / 1024).toFixed(0) + 'KB'
}

const calendarDays = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const today = now.getDate()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const checkedSet = new Set(
    (status.value?.checked_dates || []).map((d: string) => {
      const date = new Date(d)
      return date.getDate()
    })
  )

  return Array.from({ length: daysInMonth }, (_, i) => {
    const day = i + 1
    return {
      day,
      date: `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
      checked: checkedSet.has(day),
      isToday: day === today,
      isFuture: day > today,
    }
  })
})

async function fetchStatus() {
  try {
    status.value = await getCheckInStatus()
  } catch {
    // ignore
  }
}

async function handleCheckIn() {
  if (status.value?.checked_in_today) return
  checkingIn.value = true
  try {
    const result = await doCheckIn()
    ElMessage.success(`签到成功！连续 ${result.streak_days} 天，获得 ${formatBytes(result.reward_bytes)} 空间`)
    await fetchStatus()
    emit('checked-in')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '签到失败')
  } finally {
    checkingIn.value = false
  }
}

watch(() => props.visible, (val) => {
  if (val) {
    fetchStatus()
  }
})
</script>

<style scoped>
.check-in-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 4px 10px;
  border-radius: 6px;
  transition: all 0.2s;
}

.check-in-trigger:hover {
  color: var(--el-color-primary);
  background: var(--bg-hover);
}

.check-in-text {
  font-size: 13px;
}

.check-in-popover {
  padding: 4px 0;
}

.check-in-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.check-in-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.checked-badge {
  font-size: 12px;
  color: #67c23a;
  background: #f0f9eb;
  padding: 2px 8px;
  border-radius: 4px;
}

.streak-info {
  text-align: center;
  margin-bottom: 16px;
}

.streak-days {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.streak-num {
  font-size: 36px;
  font-weight: 700;
  color: var(--el-color-primary);
  line-height: 1.2;
}

.streak-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.today-reward {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.today-reward strong {
  color: var(--el-color-primary);
}

.check-in-btn {
  width: 100%;
  margin-bottom: 16px;
}

.month-calendar {
  margin-bottom: 16px;
}

.calendar-title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.calendar-day {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 12px;
  border-radius: 4px;
  color: var(--text-secondary);
}

.calendar-day.is-checked {
  background: #67c23a;
  color: #fff;
}

.calendar-day.is-today:not(.is-checked) {
  border: 1px solid var(--el-color-primary);
  color: var(--el-color-primary);
  font-weight: 600;
}

.calendar-day.is-future {
  color: var(--text-muted);
}

.reward-rules {
  border-top: 1px solid var(--border-light);
  padding-top: 12px;
}

.rules-title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.rule-item {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.8;
}
</style>