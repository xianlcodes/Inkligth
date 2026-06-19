<template>
  <div class="admin-page">
    <div class="flex items-center justify-between mb-4">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h2 class="section-title">系统配置</h2>
        <span class="section-accent">CONFIG</span>
      </div>
      <div class="flex gap-2">
        <el-button @click="exportConfigs">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button @click="triggerImport">
          <el-icon><Upload /></el-icon>
          导入
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新增配置
        </el-button>
      </div>
    </div>

    <div class="flex gap-2_5 mb-5">
      <el-input
        v-model="searchQuery"
        placeholder="搜索配置项..."
        clearable
        style="width:320px"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button @click="expandAll">
        {{ allExpanded ? '全部折叠' : '全部展开' }}
      </el-button>
    </div>

    <div v-loading="loading">
      <el-empty v-if="filteredGroups.length === 0 && !loading" description="暂无配置项" />

      <el-collapse v-model="expandedCategories" v-else class="config-collapse">
        <el-collapse-item
          v-for="group in filteredGroups"
          :key="group.category"
          :name="group.category"
        >
          <template #title>
            <div class="flex items-center gap-2_5">
              <span class="text-base font-semibold config-title-text">{{ categoryLabel(group.category) }}</span>
              <el-tag size="small" effect="plain">{{ group.items.length }}</el-tag>
            </div>
          </template>

          <div class="flex flex-col gap-0">
            <div
              v-for="cfg in group.items"
              :key="cfg.key"
              :class="['border-t first:border-t-0 transition-colors duration-fast', { 'config-editing-row': editingKey === cfg.key }]"
              :style="cfg.is_critical ? { borderLeft: '3px solid #dc2626' } : {}"
            >
              <div class="flex items-center justify-between px-5 py-3_5 cursor-pointer gap-3" @click="startEdit(cfg)" v-if="editingKey !== cfg.key">
                <div class="flex items-center gap-2 flex-wrap min-w-0">
                  <el-tag :type="typeTagType(cfg.config_type)" size="small">
                    {{ typeLabel(cfg.config_type) }}
                  </el-tag>
                  <span class="text-sm font-medium config-title-text">{{ cfg.label || cfg.key }}</span>
                  <code class="text-xs config-meta-text config-key-badge">({{ cfg.key }})</code>
                  <el-tag v-if="cfg.is_critical" type="danger" size="small" effect="dark">关键</el-tag>
                  <el-tag v-if="cfg.requires_restart" type="warning" size="small" effect="plain">需重启</el-tag>
                </div>
                <div class="flex items-center gap-3 flex-shrink-0">
                  <span class="text-sm config-desc-text truncate" style="max-width:200px">{{ truncate(cfg.value, 40) || '（未设置）' }}</span>
                  <el-button size="small" text type="primary" @click.stop="showHistory(cfg)">历史</el-button>
                </div>
              </div>

              <div v-else class="px-5 py-3_5">
                <div class="flex items-center gap-2 mb-3">
                  <span class="text-base font-semibold config-title-text">{{ cfg.label || cfg.key }}</span>
                  <code class="text-xs config-meta-text">{{ cfg.key }}</code>
                </div>

                <div class="flex flex-col gap-2_5">
                  <div class="edit-field">
                    <label class="block text-sm config-label-text mb-1">值</label>
                    <el-select
                      v-if="cfg.config_type === 'select'"
                      v-model="editValue"
                      placeholder="选择值"
                    >
                      <el-option
                        v-for="opt in selectOptions(cfg)"
                        :key="opt"
                        :label="opt"
                        :value="opt"
                      />
                    </el-select>
                    <el-switch
                      v-else-if="cfg.config_type === 'toggle'"
                      v-model="editToggle"
                      active-text="开启"
                      inactive-text="关闭"
                    />
                    <el-date-picker
                      v-else-if="cfg.config_type === 'date'"
                      v-model="editValue"
                      type="datetime"
                      value-format="YYYY-MM-DDTHH:mm:ss"
                    />
                    <el-input-number
                      v-else-if="cfg.config_type === 'number'"
                      v-model="editNumber"
                      :min="numberRange(cfg.valid_values).min"
                      :max="numberRange(cfg.valid_values).max"
                    />
                    <el-input
                      v-else-if="cfg.config_type === 'textarea'"
                      v-model="editValue"
                      type="textarea"
                      :rows="4"
                    />
                    <el-input
                      v-else
                      v-model="editValue"
                    />
                  </div>

                  <div class="edit-meta" v-if="cfg.description">
                    <div class="meta-row"><strong>说明：</strong>{{ cfg.description }}</div>
                  </div>
                  <div class="edit-meta" v-if="cfg.default_value != null">
                    <div class="meta-row"><strong>默认值：</strong><code>{{ cfg.default_value }}</code></div>
                  </div>
                  <div class="edit-meta" v-if="cfg.valid_values && cfg.config_type !== 'select' && cfg.config_type !== 'number'">
                    <div class="meta-row"><strong>合法值：</strong>{{ cfg.valid_values }}</div>
                  </div>
                  <div class="edit-meta" v-if="cfg.example">
                    <div class="meta-row"><strong>示例：</strong><code>{{ cfg.example }}</code></div>
                  </div>
                  <div class="edit-meta" v-if="cfg.requires_restart">
                    <div class="meta-row warning">⚠ 修改此配置后需要重启系统才能生效</div>
                  </div>

                  <div class="edit-actions">
                    <el-button size="small" @click="cancelEdit">取消</el-button>
                    <el-button
                      size="small"
                      type="primary"
                      :disabled="cfg.is_critical && editValue === cfg.value"
                      @click="saveConfig(cfg)"
                    >
                      保存
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <el-dialog v-model="historyVisible" title="配置变更历史" width="640px">
      <el-table :data="historyLogs" v-loading="historyLoading" size="small" max-height="400">
        <el-table-column prop="changed_at" label="时间" width="160">
          <template #default="{ row }">{{ formatDate(row.changed_at) }}</template>
        </el-table-column>
        <el-table-column prop="changed_by" label="修改人" width="160" />
        <el-table-column label="旧值" min-width="140">
          <template #default="{ row }">{{ row.old_value || '（空）' }}</template>
        </el-table-column>
        <el-table-column label="新值" min-width="140">
          <template #default="{ row }">{{ row.new_value || '（空）' }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!historyLoading && historyLogs.length === 0" description="暂无变更记录" :image-size="50" />
    </el-dialog>

    <el-dialog v-model="createVisible" title="新增配置" width="560px">
      <el-form :model="createForm" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="配置键" required>
              <el-input v-model="createForm.key" placeholder="e.g. app.max_upload_size" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="显示名称">
              <el-input v-model="createForm.label" placeholder="配置项显示名称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="分类">
              <el-select v-model="createForm.category">
                <el-option v-for="c in categories" :key="c.value" :label="c.label" :value="c.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="类型">
              <el-select v-model="createForm.config_type">
                <el-option label="文本" value="text" />
                <el-option label="下拉选择" value="select" />
                <el-option label="开关" value="toggle" />
                <el-option label="数字" value="number" />
                <el-option label="日期" value="date" />
                <el-option label="长文本" value="textarea" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="默认值">
              <el-input v-model="createForm.default_value" placeholder="默认值" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="值">
          <el-input v-model="createForm.value" :type="createForm.config_type === 'textarea' ? 'textarea' : 'text'" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="配置项的作用说明" />
        </el-form-item>
        <el-form-item label="合法值 / 选项（JSON数组或范围如 1-100）">
          <el-input v-model="createForm.valid_values" placeholder='["option1","option2"] 或 1-100' />
        </el-form-item>
        <el-form-item label="示例值">
          <el-input v-model="createForm.example" placeholder="示例值" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="关键配置">
              <el-switch v-model="createForm.is_critical" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="需重启">
              <el-switch v-model="createForm.requires_restart" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="排序">
              <el-input-number v-model="createForm.sort_order" :min="0" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <input ref="importRef" type="file" accept=".json" style="display:none" @change="handleImport" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Download, Upload } from '@element-plus/icons-vue'
import {
  getSystemConfigs, createSystemConfig, updateSystemConfig, deleteSystemConfig, getConfigChangeHistory,
  type SystemConfigItem, type ConfigChangeLog,
} from '@/api/admin'
import { formatDateCN } from '@/utils/date'

const loading = ref(false)
const configs = ref<SystemConfigItem[]>([])
const searchQuery = ref('')
const allExpanded = ref(false)
const expandedCategories = ref<string[]>([])
const editingKey = ref('')
const editValue = ref('')
const editNumber = ref(0)
const editToggle = ref(false)

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyLogs = ref<ConfigChangeLog[]>([])
const historyKey = ref('')

const createVisible = ref(false)
const createLoading = ref(false)
const createForm = ref({
  key: '', label: '', category: 'general', config_type: 'text',
  value: '', description: '', default_value: '', valid_values: '',
  example: '', is_critical: false, requires_restart: false, sort_order: 0,
})

const importRef = ref<HTMLInputElement | null>(null)

const categories = [
  { value: 'general', label: '通用设置' },
  { value: 'security', label: '安全设置' },
  { value: 'notification', label: '通知配置' },
  { value: 'storage', label: '存储配置' },
  { value: 'ai', label: 'AI 引擎' },
  { value: 'display', label: '显示设置' },
  { value: 'limits', label: '限制参数' },
]

const categoryLabelMap = Object.fromEntries(categories.map(c => [c.value, c.label]))

function categoryLabel(val: string) { return categoryLabelMap[val] || val }

const typeLabelMap: Record<string, string> = {
  text: '文本', select: '选择', toggle: '开关', number: '数字', date: '日期', textarea: '长文本',
}
function typeLabel(val: string) { return typeLabelMap[val] || val }

const typeTagTypeMap: Record<string, string> = {
  text: '', select: 'success', toggle: 'warning', number: 'info', date: 'danger', textarea: '',
}
function typeTagType(val: string) { return typeTagTypeMap[val] || '' }

const groupedConfigs = computed(() => {
  const map: Record<string, SystemConfigItem[]> = {}
  for (const cfg of configs.value) {
    const cat = cfg.category || 'general'
    if (!map[cat]) map[cat] = []
    map[cat].push(cfg)
  }
  return map
})

const filteredGroups = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const result: { category: string; items: SystemConfigItem[] }[] = []
  for (const [cat, items] of Object.entries(groupedConfigs.value)) {
    if (!q) { result.push({ category: cat, items }); continue }
    const filtered = items.filter(cfg =>
      cfg.key.toLowerCase().includes(q) ||
      (cfg.label || '').toLowerCase().includes(q) ||
      (cfg.description || '').toLowerCase().includes(q),
    )
    if (filtered.length) result.push({ category: cat, items: filtered })
  }
  return result
})

function truncate(s: string | null, n: number): string {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '...' : s
}

function selectOptions(cfg: SystemConfigItem): string[] {
  try {
    if (cfg.valid_values) return JSON.parse(cfg.valid_values)
  } catch { /* fall through */ }
  return []
}

function numberRange(raw: string | null): { min: number | undefined; max: number | undefined } {
  if (!raw) return { min: undefined, max: undefined }
  const m = raw.match(/^(\d+)-(\d+)$/)
  if (m) return { min: Number(m[1]), max: Number(m[2]) }
  return { min: undefined, max: undefined }
}

function startEdit(cfg: SystemConfigItem) {
  editingKey.value = cfg.key
  if (cfg.config_type === 'toggle') {
    editToggle.value = cfg.value === 'true' || cfg.value === '1'
  } else if (cfg.config_type === 'number') {
    editNumber.value = Number(cfg.value) || 0
    editValue.value = ''
  } else {
    editValue.value = cfg.value || ''
  }
}

function cancelEdit() {
  editingKey.value = ''
  editValue.value = ''
}

async function saveConfig(cfg: SystemConfigItem) {
  let value: string | null
  if (cfg.config_type === 'toggle') {
    value = editToggle.value ? 'true' : 'false'
  } else if (cfg.config_type === 'number') {
    value = String(editNumber.value)
  } else {
    value = editValue.value
  }

  const oldVal = cfg.value
  if (cfg.is_critical && value !== oldVal) {
    const confirmed = await ElMessageBox.confirm(
      `即将修改关键配置「${cfg.label || cfg.key}」，是否确认？`,
      '关键配置修改确认',
      { confirmButtonText: '确认修改', cancelButtonText: '取消', type: 'warning' },
    ).catch(() => false)
    if (!confirmed) return
  }

  try {
    await updateSystemConfig(cfg.key, { value })
    ElMessage.success('配置已更新')
    editingKey.value = ''
    loadConfigs()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function showHistory(cfg: SystemConfigItem) {
  historyKey.value = cfg.key
  historyVisible.value = true
  historyLoading.value = true
  try {
    const resp = await getConfigChangeHistory(cfg.key)
    historyLogs.value = resp.data.items
  } catch {
    historyLogs.value = []
  } finally { historyLoading.value = false }
}

function openCreateDialog() {
  createForm.value = {
    key: '', label: '', category: 'general', config_type: 'text',
    value: '', description: '', default_value: '', valid_values: '',
    example: '', is_critical: false, requires_restart: false, sort_order: 0,
  }
  createVisible.value = true
}

async function handleCreate() {
  if (!createForm.value.key.trim()) { ElMessage.warning('请输入配置键'); return }
  createLoading.value = true
  try {
    await createSystemConfig(createForm.value)
    ElMessage.success('配置已创建')
    createVisible.value = false
    loadConfigs()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally { createLoading.value = false }
}

function expandAll() {
  if (allExpanded.value) {
    expandedCategories.value = []
    allExpanded.value = false
  } else {
    expandedCategories.value = filteredGroups.value.map(g => g.category)
    allExpanded.value = true
  }
}

function exportConfigs() {
  const data = JSON.stringify(configs.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `system_config_export_${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('配置已导出')
}

function triggerImport() {
  importRef.value?.click()
}

async function handleImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const items = JSON.parse(text) as SystemConfigItem[]
    let count = 0
    for (const item of items) {
      try {
        await updateSystemConfig(item.key, { value: item.value, label: item.label, description: item.description })
        count++
      } catch { /* skip failed */ }
    }
    ElMessage.success(`已导入 ${count}/${items.length} 项配置`)
    loadConfigs()
  } catch {
    ElMessage.error('导入失败：JSON 格式不正确')
  } finally {
    input.value = ''
  }
}

const formatDate = formatDateCN

async function loadConfigs() {
  loading.value = true
  try {
    const resp = await getSystemConfigs()
    configs.value = resp.data.items
  } catch { configs.value = [] }
  finally { loading.value = false }
}

onMounted(() => { loadConfigs() })
</script>

<style scoped>
.admin-page {
  max-width: 1200px;
}

.section-bar {
  display: flex;
  align-items: center;
  gap: 14px;
}

.section-bar-line {
  width: 4px;
  height: 22px;
  border-radius: 3px;
  background: linear-gradient(180deg, var(--accent-primary) 0%, var(--sky-400) 100%);
  flex-shrink: 0;
}

.section-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.3px;
}
</style>
