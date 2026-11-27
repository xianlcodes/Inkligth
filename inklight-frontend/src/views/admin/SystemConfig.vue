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

        <div class="preset-table-wrap">
          <el-table :data="presetRows" size="small" class="mb-3">
            <el-table-column label="标识" width="100">
              <template #default="{ row }"><el-input v-model="row.provider" size="small" placeholder="英文标识" /></template>
            </el-table-column>
            <el-table-column label="显示名称" width="130">
              <template #default="{ row }"><el-input v-model="row.label" size="small" placeholder="显示名" /></template>
            </el-table-column>
            <el-table-column label="API 地址" min-width="220">
              <template #default="{ row }"><el-input v-model="row.base_url" size="small" placeholder="https://..." /></template>
            </el-table-column>
            <el-table-column label="默认模型" width="150">
              <template #default="{ row }"><el-input v-model="row.model" size="small" placeholder="模型名" /></template>
            </el-table-column>
            <el-table-column label="免费" width="72" align="center">
              <template #default="{ row }"><el-switch v-model="row.free" size="small" /></template>
            </el-table-column>
            <el-table-column label="说明" min-width="150">
              <template #default="{ row }"><el-input v-model="row.note" size="small" placeholder="给用户的提示" /></template>
            </el-table-column>
            <el-table-column label="操作" width="72" align="center" fixed="right">
              <template #default="{ $index }">
                <el-button link type="danger" size="small" @click="presetRows.splice($index, 1)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

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
            <h3 class="card-title">📨 召回邮件</h3>
            <p class="card-desc">帮流失的用户回来看看。使用系统内置邮件服务发送（与注册验证码同一通道），无需任何额外配置。邮件每天上午 10 点发送，每用户每类最多一封。</p>
          </div>
        </template>

        <!-- 自动规则开关 -->
        <div class="recall-rule-row">
          <el-switch v-model="recallEnabled" active-text="开启" inactive-text="关闭" />
          <span class="text-sm text-slate-600">
            {{ recallEnabled ? '自动召回已开启：每天上午 10 点按下面规则检查并发送' : '自动召回已关闭（默认）：不会自动给用户发邮件' }}
          </span>
          <el-button size="small" type="primary" :disabled="recallSaving || recallEnabled === recallEnabledOriginal" @click="saveRecall">
            保存开关
          </el-button>
        </div>
        <div class="recall-rule-desc text-xs text-slate-500 leading-6">
          自动规则会发给两类用户（各限一封）：<br />
          · 注册满 3 天还从未登录过的用户 → 提醒上传文献，免费额度仍在<br />
          · 最近一次登录在 30~60 天前的用户 → 介绍平台新变化，邀请回访
        </div>

        <el-divider class="my-4" />

        <!-- 手动发送 -->
        <div class="recall-manual-row flex items-center gap-3">
          <span class="text-sm font-semibold">手动发送：</span>
          <el-radio-group v-model="sendType" size="small">
            <el-radio-button value="no_upload_3d">给「未使用」的用户</el-radio-button>
            <el-radio-button value="inactive_30d">给「长期未登录」的用户</el-radio-button>
          </el-radio-group>
          <el-button size="small" type="primary" plain @click="openSendDialog">选择用户并发送</el-button>
          <span class="text-xs text-slate-500">不勾选自动开关也能用；使用的正文见下方「邮件内容」</span>
        </div>

        <el-divider class="my-4" />

        <!-- 邮件内容编辑 -->
        <div class="mb-2 text-sm font-semibold">邮件内容（可直接修改文字；保存后立即生效）</div>
        <el-tabs v-model="activeTemplateTab">
          <el-tab-pane label="未上传提醒" name="no_upload_3d">
            <el-input v-model="recallTemplates.no_upload_3d.subject" class="mb-2" placeholder="邮件标题">
              <template #prepend>标题</template>
            </el-input>
            <el-input
              v-model="recallTemplates.no_upload_3d.body"
              type="textarea"
              :rows="8"
              placeholder="邮件正文（HTML）"
            />
            <div class="flex gap-2 mt-2">
              <el-button size="small" type="primary" @click="saveRecallTemplate('no_upload_3d')">保存这封邮件</el-button>
              <el-button size="small" @click="resetRecallTemplate('no_upload_3d')">恢复默认文案</el-button>
              <span class="text-xs text-slate-500 self-center">正文支持 HTML；会发给「注册满 3 天从未登录」的用户</span>
            </div>
          </el-tab-pane>
          <el-tab-pane label="长期未登录" name="inactive_30d">
            <el-input v-model="recallTemplates.inactive_30d.subject" class="mb-2" placeholder="邮件标题">
              <template #prepend>标题</template>
            </el-input>
            <el-input
              v-model="recallTemplates.inactive_30d.body"
              type="textarea"
              :rows="8"
              placeholder="邮件正文（HTML）"
            />
            <div class="flex gap-2 mt-2">
              <el-button size="small" type="primary" @click="saveRecallTemplate('inactive_30d')">保存这封邮件</el-button>
              <el-button size="small" @click="resetRecallTemplate('inactive_30d')">恢复默认文案</el-button>
              <span class="text-xs text-slate-500 self-center">正文支持 HTML；会发给「30~60 天未登录」的用户</span>
            </div>
          </el-tab-pane>
        </el-tabs>
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
        <el-alert
          v-if="duplicateKeyWarning"
          type="warning"
          :closable="false"
          show-icon
          class="mb-3"
        >
          <template #title>
            已存在同标识的配置项「{{ duplicateKeyWarning.label || duplicateKeyWarning.key }}」，保存将覆盖它当前的值。
          </template>
        </el-alert>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="这项配置叫什么（显示名称）">
              <el-input v-model="createForm.label" placeholder="例如：单日上传文件上限" />
              <div class="field-tip">会显示在配置列表里，用一句中文说清它的用途</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="配置标识（英文，程序使用）">
              <el-input v-model="createForm.key" placeholder="例如 app.max_upload_size" />
              <div class="field-tip">小写英文和点，创建后不要再改——改了等于新配置</div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="它属于哪个功能分组">
              <el-select v-model="createForm.category">
                <el-option v-for="c in categories" :key="c.value" :label="c.label" :value="c.value" />
              </el-select>
              <div class="field-tip">决定它显示在哪个折叠分组里</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="值的样式">
              <el-select v-model="createForm.config_type">
                <el-option label="一行文字" value="text" />
                <el-option label="下拉选择" value="select" />
                <el-option label="开 / 关" value="toggle" />
                <el-option label="数字" value="number" />
                <el-option label="日期时间" value="date" />
                <el-option label="多行长文本" value="textarea" />
              </el-select>
              <div class="field-tip">决定编辑时出现什么样的输入框</div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="当前的值（保存后立即生效）">
          <el-input
            v-model="createForm.value"
            :type="createForm.config_type === 'textarea' ? 'textarea' : 'text'"
            :rows="createForm.config_type === 'textarea' ? 3 : undefined"
          />
        </el-form-item>

        <el-form-item label="说明（写给以后接手的人）">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="讲清楚：这项配置控制什么？改成不同值会有什么效果？" />
        </el-form-item>

        <el-collapse class="mt-1">
          <el-collapse-item title="高级选项（一般不用动）">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="默认值（删除配置后回到这个值）">
                  <el-input v-model="createForm.default_value" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="显示顺序">
                  <el-input-number v-model="createForm.sort_order" :min="0" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="可选值（下拉类型用，JSON 数组）">
              <el-input v-model="createForm.valid_values" placeholder='["option1","option2"]' />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="标记为「关键配置」">
                  <el-switch v-model="createForm.is_critical" />
                  <div class="field-tip">修改时会多一步确认，列表里标红边</div>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="需要重启才生效">
                  <el-switch v-model="createForm.requires_restart" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-collapse-item>
        </el-collapse>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 召回邮件：选择用户并发送 -->
    <el-dialog v-model="sendDialogVisible" title="发送召回邮件" width="680px">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        class="mb-3"
      >
        <template #title>
          将把「{{ sendType === 'no_upload_3d' ? '未上传提醒' : '长期未登录' }}」邮件发送给勾选的用户（每用户此类型最多发过一次，已收过的不会重复发送）。
        </template>
      </el-alert>
      <el-input v-model="userSearch" placeholder="搜索邮箱/用户名..." clearable size="small" class="mb-2" @input="loadSendUsers">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-table
        ref="sendUserTableRef"
        :data="sendUserRows"
        v-loading="sendUsersLoading"
        size="small"
        max-height="320"
        row-key="id"
        @selection-change="onSendSelectionChange"
      >
        <el-table-column type="selection" width="42" reserve-selection />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="last_login_at" label="最近登录" width="150">
          <template #default="{ row }">{{ row.last_login_at ? formatDate(row.last_login_at) : '从未登录' }}</template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="sendUserPage"
        :page-size="20"
        :total="sendUserTotal"
        layout="prev, pager, next"
        size="small"
        class="mt-2 justify-end"
        @current-change="loadSendUsers"
      />
      <div class="text-xs text-slate-500 mt-2">已勾选 {{ sendSelection.length }} 人</div>
      <template #footer>
        <el-button @click="sendDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="sendingRecall"
          :disabled="sendSelection.length === 0"
          @click="confirmSendRecall"
        >
          发送给选中的 {{ sendSelection.length }} 人
        </el-button>
      </template>
    </el-dialog>

    <input ref="importRef" type="file" accept=".json" style="display:none" @change="handleImport" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Download, Upload } from 'lucide-vue-next'
import {
  getSystemConfigs, createSystemConfig, updateSystemConfig, deleteSystemConfig, getConfigChangeHistory,
  getStatsOverview, getAdminUsers, sendRecallEmails,
  type SystemConfigItem, type ConfigChangeLog, type StatsOverview, type AdminUser,
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
// 两封召回邮件的可编辑内容（subject/body + 后台保存的默认值，用于「恢复默认文案」）
const recallTemplates = ref({
  no_upload_3d: { subject: '', body: '', subjectDefault: '', bodyDefault: '' },
  inactive_30d: { subject: '', body: '', subjectDefault: '', bodyDefault: '' },
})
const activeTemplateTab = ref('no_upload_3d')

// 手动发送
const sendDialogVisible = ref(false)
const sendType = ref<'no_upload_3d' | 'inactive_30d'>('no_upload_3d')
const sendUserRows = ref<AdminUser[]>([])
const sendUserTotal = ref(0)
const sendUserPage = ref(1)
const sendUserSearch = ref('')
const sendSelection = ref<AdminUser[]>([])
const sendUsersLoading = ref(false)
const sendingRecall = ref(false)
const sendUserTableRef = ref()

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

const duplicateKeyWarning = computed(() =>
  createForm.value.key.trim()
    ? configs.value.find((c) => c.key === createForm.value.key.trim()) || null
    : null,
)

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

// ── 召回邮件内容编辑 ──
const TEMPLATE_CONFIG_KEYS: Record<string, { subject: string; body: string }> = {
  no_upload_3d: { subject: 'recall_no_upload_subject', body: 'recall_no_upload_body' },
  inactive_30d: { subject: 'recall_inactive_subject', body: 'recall_inactive_body' },
}

function syncRecallTemplates() {
  for (const [type, keys] of Object.entries(TEMPLATE_CONFIG_KEYS)) {
    const subjectCfg = findByKey(keys.subject)
    const bodyCfg = findByKey(keys.body)
    recallTemplates.value[type as 'no_upload_3d' | 'inactive_30d'].subject =
      subjectCfg?.value || subjectCfg?.default_value || ''
    recallTemplates.value[type as 'no_upload_3d' | 'inactive_30d'].body =
      bodyCfg?.value || bodyCfg?.default_value || ''
    recallTemplates.value[type as 'no_upload_3d' | 'inactive_30d'].subjectDefault =
      subjectCfg?.default_value || ''
    recallTemplates.value[type as 'no_upload_3d' | 'inactive_30d'].bodyDefault =
      bodyCfg?.default_value || ''
  }
}

async function saveRecallTemplate(type: 'no_upload_3d' | 'inactive_30d') {
  const t = recallTemplates.value[type]
  const keys = TEMPLATE_CONFIG_KEYS[type]
  try {
    await updateSystemConfig(keys.subject, { value: t.subject })
    await updateSystemConfig(keys.body, { value: t.body })
    ElMessage.success('邮件内容已保存，下次发送时使用新内容')
    await loadConfigs()
  } catch (e: any) {
    const raw = e.response?.data?.detail
    ElMessage.error(typeof raw === 'string' ? raw : raw?.message || '保存失败')
  }
}

function resetRecallTemplate(type: 'no_upload_3d' | 'inactive_30d') {
  const t = recallTemplates.value[type]
  if (!t.subjectDefault && !t.bodyDefault) {
    ElMessage.warning('暂无默认文案可恢复')
    return
  }
  t.subject = t.subjectDefault
  t.body = t.bodyDefault
  ElMessage.success('已恢复为默认文案，记得点「保存这封邮件」才会生效')
}

// ── 手动发送 ──
function openSendDialog() {
  sendType.value = 'no_upload_3d'
  sendSelection.value = []
  sendUserSearch.value = ''
  sendUserPage.value = 1
  sendDialogVisible.value = true
  loadSendUsers()
}

async function loadSendUsers() {
  sendUsersLoading.value = true
  try {
    const resp = await getAdminUsers({
      skip: (sendUserPage.value - 1) * 20,
      limit: 20,
      search: sendUserSearch.value || undefined,
    })
    sendUserRows.value = resp.data.items
    sendUserTotal.value = resp.data.total
  } catch {
    sendUserRows.value = []
    sendUserTotal.value = 0
  } finally {
    sendUsersLoading.value = false
  }
}

function onSendSelectionChange(rows: AdminUser[]) {
  sendSelection.value = rows
}

async function confirmSendRecall() {
  const userIds = sendSelection.value.map((u) => u.id)
  sendingRecall.value = true
  try {
    const resp = await sendRecallEmails({ recall_type: sendType.value, user_ids: userIds })
    const { sent, failed } = resp.data
    if (failed === 0) {
      ElMessage.success(`已发送 ${sent} 封召回邮件`)
    } else {
      ElMessage.warning(`发送完成：成功 ${sent} 封，失败 ${failed} 封（详情见日志）`)
    }
    sendDialogVisible.value = false
    sendUserTableRef.value?.clearSelection?.()
    sendSelection.value = []
  } catch (e: any) {
    const raw = e.response?.data?.detail
    ElMessage.error(typeof raw === 'string' ? raw : raw?.message || '发送失败')
  } finally {
    sendingRecall.value = false
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
    // 召回邮件模板（subject/body + 默认值，供「恢复默认文案」）
    syncRecallTemplates()
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

.preset-table-wrap {
  overflow-x: auto;
  padding-bottom: 4px;
}

/* 强制表格保持最小宽度：容器不够宽时出现横向滚动条，而不是挤压列 */
.preset-table-wrap :deep(.el-table) {
  min-width: 1020px;
}

.preset-table-wrap :deep(.el-table__inner-wrapper) {
  min-width: 1020px;
}

/* 列头不换行（之前「免费」「操作」被挤成竖排文字） */
.preset-table-wrap :deep(.el-table th.el-table__cell .cell) {
  white-space: nowrap;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #1f2a24);
  margin: 0;
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary, #63756c);
  margin: 4px 0 0;
}

.field-tip {
  font-size: 12px;
  color: var(--text-secondary, #8fa096);
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
  color: var(--text-primary, #1f2a24);
}

.config-meta-text {
  color: var(--text-secondary, #8fa096);
}

.config-desc-text {
  color: var(--text-secondary, #63756c);
}

.config-label-text {
  color: var(--text-primary, #46544c);
}

.config-editing-row {
  background: var(--bg-secondary, #faf7f2);
}

.edit-meta {
  font-size: 12.5px;
  color: var(--text-secondary, #63756c);
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
