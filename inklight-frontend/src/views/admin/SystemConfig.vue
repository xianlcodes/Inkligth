<template>
  <div class="admin-page">
    <div class="flex items-center justify-between mb-4">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h2 class="section-title">系统配置</h2>
        <span class="section-accent">CONFIG</span>
      </div>
      <div class="flex gap-2">
        <el-button @click="exportConfigs"><el-icon><Download /></el-icon>导出</el-button>
        <el-button @click="triggerImport"><el-icon><Upload /></el-icon>导入</el-button>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <template #title>
        下面每一项保存后立即生效，无需重启。改错了也不用慌：每项都有「变更历史」可以查看谁在什么时候改过什么。
      </template>
    </el-alert>

    <div v-loading="loading" class="flex flex-col gap-4">
      <!-- ═══════════ ① 平台免费额度 ═══════════ -->
      <el-card shadow="never" class="config-card">
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="card-title">🎁 平台免费额度</h3>
              <p class="card-desc">新用户注册赠送的「文献翻译」用的是什么服务。普通用户不需要做任何配置即可使用。</p>
            </div>
            <el-tag :type="platformEnabled ? 'success' : 'info'" effect="dark">
              {{ platformEnabled ? '已启用' : '未启用' }}
            </el-tag>
          </div>
        </template>

        <el-form label-position="left" label-width="130px" class="max-w-[640px]">
          <el-form-item label="API Key">
            <el-input
              v-model="platformForm.keyInput"
              type="password"
              show-password
              :placeholder="platformKeyMasked || '尚未设置，粘贴免费服务的 Key'"
            />
            <div class="field-tip">Key 加密保存，页面上永远只显示掩码。留空保存 = 保持现状；想更换就粘贴新 Key。</div>
          </el-form-item>
          <el-form-item label="服务地址">
            <el-input v-model="platformForm.baseUrl" placeholder="https://open.bigmodel.cn/api/paas/v4" />
            <div class="field-tip">必须是 OpenAI 兼容接口地址。</div>
          </el-form-item>
          <el-form-item label="免费模型">
            <el-input v-model="platformForm.model" placeholder="glm-4.7-flash" />
            <div class="field-tip warning">⚠ 一定要填免费档模型；填了付费模型会持续消耗你的账户余额。</div>
          </el-form-item>
          <el-form-item label="每用户赠送">
            <el-input-number v-model="platformForm.free" :min="0" :max="99" />
            <span class="field-tip ml-2">篇（新用户注册即送，设为 0 表示不再向新用户赠送）</span>
          </el-form-item>

          <div class="quota-stats text-xs text-slate-500 mb-3">
            全站额度：剩余 <strong>{{ overview?.free_quota_remaining_total ?? '-' }}</strong> 篇 ·
            已使用 <strong>{{ overview?.free_quota_used_total ?? '-' }}</strong> 篇 ·
            自配 Key 用户 <strong>{{ overview?.users_with_own_engine ?? '-' }}</strong> 人
          </div>

          <div class="flex items-center gap-2">
            <el-button type="primary" :loading="savingPlatform" @click="savePlatform">保存平台额度设置</el-button>
            <el-button type="danger" plain @click="disablePlatform">停用免费额度</el-button>
            <a href="/tutorials" target="_blank" class="help-link">免费 Key 申请教程 ↗</a>
          </div>
        </el-form>
      </el-card>

      <!-- ═══════════ ② 供应商预设 ═══════════ -->
      <el-card shadow="never" class="config-card">
        <template #header>
          <div>
            <h3 class="card-title">🏭 供应商预设列表</h3>
            <p class="card-desc">用户在「AI 设置」添加引擎时下拉框里看到的选项。选择后自动填好 API 地址和模型。</p>
          </div>
        </template>

        <el-table :data="presetRows" size="small" class="mb-3">
          <el-table-column label="标识（英文）" min-width="110">
            <template #default="{ row }"><el-input v-model="row.provider" size="small" placeholder="如 deepseek" /></template>
          </el-table-column>
          <el-table-column label="显示名称" min-width="140">
            <template #default="{ row }"><el-input v-model="row.label" size="small" placeholder="如 DeepSeek" /></template>
          </el-table-column>
          <el-table-column label="API 地址" min-width="240">
            <template #default="{ row }"><el-input v-model="row.base_url" size="small" placeholder="https://..." /></template>
          </el-table-column>
          <el-table-column label="默认模型" min-width="150">
            <template #default="{ row }"><el-input v-model="row.model" size="small" placeholder="模型名" /></template>
          </el-table-column>
          <el-table-column label="免费" width="60" align="center">
            <template #default="{ row }"><el-switch v-model="row.free" size="small" /></template>
          </el-table-column>
          <el-table-column label="说明" min-width="160">
            <template #default="{ row }"><el-input v-model="row.note" size="small" placeholder="展示给用户的提示" /></template>
          </el-table-column>
          <el-table-column label="" width="60" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="presetRows.splice($index, 1)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="flex items-center gap-2">
          <el-button size="small" @click="addPresetRow">+ 添加供应商</el-button>
          <el-button size="small" type="primary" :loading="savingPresets" @click="savePresets">保存供应商预设</el-button>
          <span class="text-xs text-slate-500">要求：OpenAI 兼容接口；用户仍可手动输入列表之外的供应商。</span>
        </div>
      </el-card>

      <!-- ═══════════ ③ 召回邮件 ═══════════ -->
      <el-card shadow="never" class="config-card">
        <template #header>
          <div>
            <h3 class="card-title">📨 自动召回邮件</h3>
            <p class="card-desc">帮流失的用户回来看看。使用系统自带的邮件服务发送，每用户每类邮件最多一封，不会骚扰。</p>
          </div>
        </template>
        <div class="flex items-center gap-4">
          <el-switch v-model="recallEnabled" active-text="开启" inactive-text="关闭" />
          <span class="text-sm text-slate-600">
            {{ recallEnabled ? '已开启：每天上午 10 点自动检查并发送' : '已关闭（默认）：不会给任何用户发邮件' }}
          </span>
          <el-button size="small" type="primary" :disabled="recallSaving || recallEnabled === recallEnabledOriginal" @click="saveRecall">
            保存
          </el-button>
        </div>
        <div class="mt-3 text-xs text-slate-500 leading-6">
          会发给两类用户（各限一封）：<br />
          · 注册满 3 天还没有上传过任何文献的用户 → 提醒上传文献，免费额度仍在<br />
          · 30~60 天没有登录的用户 → 介绍平台新变化，邀请回访
        </div>
      </el-card>

      <!-- ═══════════ ④ 其他配置（高级） ═══════════ -->
      <el-card shadow="never" class="config-card">
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="card-title">🔧 其他配置（高级）</h3>
              <p class="card-desc">系统运行依赖的其余配置项。不确定作用的话，保持默认即可。</p>
            </div>
            <div class="flex gap-2">
              <el-button size="small" type="primary" plain @click="openCreateDialog"><el-icon><Plus /></el-icon>新增配置</el-button>
            </div>
          </div>
        </template>

        <div class="flex gap-2 mb-3">
          <el-input v-model="searchQuery" placeholder="搜索配置项..." clearable style="width: 280px" size="small">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>

        <el-empty v-if="otherGroups.length === 0" description="没有其他配置项" :image-size="60" />

        <el-collapse v-else v-model="expandedCategories" class="config-collapse">
          <el-collapse-item v-for="group in otherGroups" :key="group.category" :name="group.category">
            <template #title>
              <div class="flex items-center gap-2_5">
                <span class="text-base font-semibold config-title-text">{{ categoryLabel(group.category) }}</span>
                <el-tag size="small" effect="plain">{{ group.items.length }}</el-tag>
              </div>
            </template>

            <div
              v-for="cfg in group.items"
              :key="cfg.key"
              :class="['border-t first:border-t-0 transition-colors duration-fast', { 'config-editing-row': editingKey === cfg.key }]"
              :style="cfg.is_critical ? { borderLeft: '3px solid #dc2626' } : {}"
            >
              <div
                v-if="editingKey !== cfg.key"
                class="flex items-center justify-between px-5 py-3_5 cursor-pointer gap-3"
                @click="startEdit(cfg)"
              >
                <div class="flex items-center gap-2 flex-wrap min-w-0">
                  <span class="text-sm font-medium config-title-text">{{ cfg.label || cfg.key }}</span>
                  <el-tag v-if="cfg.is_critical" type="danger" size="small" effect="dark">关键</el-tag>
                  <el-tag v-if="cfg.requires_restart" type="warning" size="small" effect="plain">需重启</el-tag>
                </div>
                <div class="flex items-center gap-3 flex-shrink-0">
                  <span class="text-sm config-desc-text truncate" style="max-width:220px">{{ truncate(cfg.value, 40) || '（未设置）' }}</span>
                  <el-button size="small" text type="primary" @click.stop="showHistory(cfg)">历史</el-button>
                </div>
              </div>

              <div v-else class="px-5 py-3_5">
                <div class="flex items-center gap-2 mb-3">
                  <span class="text-base font-semibold config-title-text">{{ cfg.label || cfg.key }}</span>
                  <code class="text-xs config-meta-text">{{ cfg.key }}</code>
                </div>

                <div class="flex flex-col gap-2_5">
                  <el-select v-if="cfg.config_type === 'select'" v-model="editValue" placeholder="选择值">
                    <el-option v-for="opt in selectOptions(cfg)" :key="opt" :label="opt" :value="opt" />
                  </el-select>
                  <el-switch v-else-if="cfg.config_type === 'toggle'" v-model="editToggle" active-text="开启" inactive-text="关闭" />
                  <el-date-picker v-else-if="cfg.config_type === 'date'" v-model="editValue" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
                  <el-input-number v-else-if="cfg.config_type === 'number'" v-model="editNumber" :min="numberRange(cfg.valid_values).min" :max="numberRange(cfg.valid_values).max" />
                  <el-input v-else-if="cfg.config_type === 'textarea'" v-model="editValue" type="textarea" :rows="4" />
                  <el-input v-else v-model="editValue" />

                  <div class="edit-meta" v-if="cfg.description">
                    <div class="meta-row"><strong>说明：</strong>{{ cfg.description }}</div>
                  </div>
                  <div class="edit-meta" v-if="cfg.requires_restart">
                    <div class="meta-row warning">⚠ 修改后需要重启系统才能生效</div>
                  </div>

                  <div class="edit-actions">
                    <el-button size="small" @click="cancelEdit">取消</el-button>
                    <el-button size="small" type="primary" @click="saveConfig(cfg)">保存</el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-card>
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

    <el-dialog v-model="createVisible" title="新增配置（高级）" width="560px">
      <el-form :model="createForm" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="配置键（英文标识）" required>
              <el-input v-model="createForm.key" placeholder="如 app.max_upload_size" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="显示名称">
              <el-input v-model="createForm.label" placeholder="配置项的中文显示名" />
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
              <el-input v-model="createForm.default_value" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="值">
          <el-input v-model="createForm.value" :type="createForm.config_type === 'textarea' ? 'textarea' : 'text'" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="写给接手的人看的说明，讲清楚这项配置是干什么的" />
        </el-form-item>
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
  getStatsOverview, type SystemConfigItem, type ConfigChangeLog, type StatsOverview,
} from '@/api/admin'
import { formatDateCN } from '@/utils/date'

// ── 已知配置键 → 专属卡片；其余进「其他配置」 ──
const PLATFORM_KEYS = ['platform_ai_key', 'platform_ai_base_url', 'platform_ai_model', 'platform_free_translations']
const PRESETS_KEY = 'provider_presets'
const RECALL_KEY = 'recall_emails_enabled'
const PLATFORM_LABEL = 'platform'

const loading = ref(false)
const configs = ref<SystemConfigItem[]>([])
const overview = ref<StatsOverview | null>(null)
const searchQuery = ref('')
const expandedCategories = ref<string[]>([])
const editingKey = ref('')
const editValue = ref('')
const editNumber = ref(0)
const editToggle = ref(false)
const savingPlatform = ref(false)
const savingPresets = ref(false)
const recallSaving = ref(false)

const platformForm = ref({ keyInput: '', baseUrl: '', model: '', free: 1 })
const platformKeyMasked = ref('')
const presetRows = ref<{ provider: string; label: string; base_url: string; model: string; free: boolean; note: string }[]>([])
const recallEnabled = ref(false)
const recallEnabledOriginal = ref(false)

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyLogs = ref<ConfigChangeLog[]>([])

const createVisible = ref(false)
const createLoading = ref(false)
const createForm = ref({
  key: '', label: '', category: 'general', config_type: 'text',
  value: '', description: '', default_value: '', is_critical: false, requires_restart: false, sort_order: 0,
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
  { value: 'platform', label: '平台免费额度' },
]
const categoryLabelMap = Object.fromEntries(categories.map(c => [c.value, c.label]))
function categoryLabel(val: string) { return categoryLabelMap[val] || val }

function findByKey(key: string): SystemConfigItem | undefined {
  return configs.value.find(c => c.key === key)
}

const platformEnabled = computed(() => {
  const cfg = findByKey('platform_ai_key')
  return !!(cfg && cfg.value)
})

const otherGroups = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const map: Record<string, SystemConfigItem[]> = {}
  for (const cfg of configs.value) {
    // 专属卡片已覆盖的键不进「其他」
    if (PLATFORM_KEYS.includes(cfg.key) || cfg.key === PRESETS_KEY || cfg.key === RECALL_KEY) continue
    const cat = cfg.category || 'general'
    if (!map[cat]) map[cat] = []
    map[cat].push(cfg)
  }
  const result: { category: string; items: SystemConfigItem[] }[] = []
  for (const [cat, items] of Object.entries(map)) {
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
  try {
    await updateSystemConfig(cfg.key, { value })
    ElMessage.success('已保存，立即生效')
    editingKey.value = ''
    await loadConfigs()
  } catch (e: any) {
    const raw = e.response?.data?.detail
    ElMessage.error(typeof raw === 'string' ? raw : raw?.message || '保存失败')
  }
}

async function showHistory(cfg: SystemConfigItem) {
  historyVisible.value = true
  historyLoading.value = true
  try {
    const resp = await getConfigChangeHistory(cfg.key)
    historyLogs.value = resp.data.items
  } catch {
    historyLogs.value = []
  } finally { historyLoading.value = false }
}

// ── ① 平台免费额度 ──
function syncPlatformForm() {
  const keyCfg = findByKey('platform_ai_key')
  platformKeyMasked.value = keyCfg?.value || ''
  platformForm.value.keyInput = '' // 掩码不回填输入框，留空=保持现状
  platformForm.value.baseUrl = findByKey('platform_ai_base_url')?.value || ''
  platformForm.value.model = findByKey('platform_ai_model')?.value || ''
  platformForm.value.free = Number(findByKey('platform_free_translations')?.value ?? 1) || 0
}

async function savePlatform() {
  if (!platformForm.value.baseUrl.trim()) { ElMessage.warning('服务地址不能为空'); return }
  if (!platformForm.value.model.trim()) { ElMessage.warning('免费模型不能为空'); return }

  const keyChanged = platformForm.value.keyInput.trim() !== ''
  if (keyChanged) {
    const confirmed = await ElMessageBox.confirm(
      '即将更换平台免费额度使用的 API Key，所有使用免费额度的翻译会立即切换到新 Key。是否继续？',
      '更换 Key 确认',
      { confirmButtonText: '确认更换', cancelButtonText: '取消', type: 'warning' },
    ).catch(() => false)
    if (!confirmed) return
  }

  savingPlatform.value = true
  try {
    if (keyChanged) {
      await updateSystemConfig('platform_ai_key', { value: platformForm.value.keyInput.trim() })
    }
    await updateSystemConfig('platform_ai_base_url', { value: platformForm.value.baseUrl.trim() })
    await updateSystemConfig('platform_ai_model', { value: platformForm.value.model.trim() })
    await updateSystemConfig('platform_free_translations', { value: String(platformForm.value.free) })
    ElMessage.success('平台免费额度设置已保存，立即生效')
    await loadConfigs()
  } catch (e: any) {
    const raw = e.response?.data?.detail
    ElMessage.error(typeof raw === 'string' ? raw : raw?.message || '保存失败')
  } finally {
    savingPlatform.value = false
  }
}

async function disablePlatform() {
  const confirmed = await ElMessageBox.confirm(
    '停用后，未配置自己 Key 的用户将无法使用翻译功能（免费额度不再可用）。已配置自己 Key 的用户不受影响。确定停用吗？',
    '停用免费额度',
    { confirmButtonText: '停用', cancelButtonText: '取消', type: 'warning' },
  ).catch(() => false)
  if (!confirmed) return
  try {
    await deleteSystemConfig('platform_ai_key')
    ElMessage.success('已停用（如 .env 中也配置过 DEFAULT_AI_KEY，需同步清除才会完全停用）')
    await loadConfigs()
  } catch (e: any) {
    const raw = e.response?.data?.detail
    ElMessage.error(typeof raw === 'string' ? raw : raw?.message || '操作失败')
  }
}

// ── ② 供应商预设 ──
function addPresetRow() {
  presetRows.value.push({ provider: '', label: '', base_url: '', model: '', free: false, note: '' })
}

async function savePresets() {
  for (const [i, row] of presetRows.value.entries()) {
    if (!row.provider.trim() || !row.label.trim() || !row.base_url.trim() || !row.model.trim()) {
      ElMessage.warning(`第 ${i + 1} 行信息不完整（标识/名称/地址/模型都要填）`)
      return
    }
  }
  savingPresets.value = true
  try {
    await updateSystemConfig(PRESETS_KEY, { value: JSON.stringify(presetRows.value, null, 2) })
    ElMessage.success('供应商预设已保存，用户端立即生效')
    await loadConfigs()
  } catch (e: any) {
    const raw = e.response?.data?.detail
    ElMessage.error(typeof raw === 'string' ? raw : raw?.message || '保存失败')
  } finally {
    savingPresets.value = false
  }
}

// ── ③ 召回邮件 ──
async function saveRecall() {
  recallSaving.value = true
  try {
    await updateSystemConfig(RECALL_KEY, { value: recallEnabled.value ? 'true' : 'false' })
    recallEnabledOriginal.value = recallEnabled.value
    ElMessage.success(recallEnabled.value ? '召回邮件已开启' : '召回邮件已关闭')
  } catch (e: any) {
    const raw = e.response?.data?.detail
    ElMessage.error(typeof raw === 'string' ? raw : raw?.message || '保存失败')
  } finally {
    recallSaving.value = false
  }
}

// ── 通用：创建/导出/导入 ──
function openCreateDialog() {
  createForm.value = {
    key: '', label: '', category: 'general', config_type: 'text',
    value: '', description: '', default_value: '', is_critical: false, requires_restart: false, sort_order: 0,
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
    await loadConfigs()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally { createLoading.value = false }
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
    await loadConfigs()
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
    syncPlatformForm()
    // 召回开关
    const recall = findByKey(RECALL_KEY)
    recallEnabled.value = recall?.value === 'true' || recall?.value === '1'
    recallEnabledOriginal.value = recallEnabled.value
    // 供应商预设行
    const presetCfg = findByKey(PRESETS_KEY)
    try {
      const parsed = JSON.parse(presetCfg?.value || '[]')
      presetRows.value = Array.isArray(parsed)
        ? parsed.map((p: any) => ({
            provider: p.provider || '', label: p.label || '', base_url: p.base_url || '',
            model: p.model || '', free: !!p.free, note: p.note || '',
          }))
        : []
    } catch {
      presetRows.value = []
    }
  } catch {
    configs.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadConfigs()
  try {
    const resp = await getStatsOverview()
    overview.value = resp.data
  } catch {
    overview.value = null
  }
})
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

.config-card {
  border-radius: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  margin: 0;
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary, #64748b);
  margin: 4px 0 0;
}

.field-tip {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.5;
  margin-top: 2px;
  width: 100%;
}

.field-tip.warning {
  color: #d97706;
}

.help-link {
  font-size: 13px;
  color: var(--el-color-primary, #409eff);
  text-decoration: none;
}

.quota-stats strong {
  color: var(--text-primary, #334155);
}

.config-collapse {
  border: none;
}

.config-title-text {
  color: var(--text-primary, #1e293b);
}

.config-meta-text {
  color: var(--text-secondary, #94a3b8);
}

.config-desc-text {
  color: var(--text-secondary, #64748b);
}

.config-label-text {
  color: var(--text-primary, #475569);
}

.config-editing-row {
  background: var(--bg-secondary, #f8fafc);
}

.edit-meta {
  font-size: 12.5px;
  color: var(--text-secondary, #64748b);
}

.meta-row.warning {
  color: #d97706;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
