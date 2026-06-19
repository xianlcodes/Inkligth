<template>
  <div class="skills-page">
    <div class="skills-header flex items-center justify-between mb-4">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h2 class="section-title">技能与钩子管理</h2>
        <span class="section-accent">SKILLS</span>
      </div>
      <div class="flex gap-2">
        <el-button @click="activeTab = 'skills'">技能列表</el-button>
        <el-button @click="activeTab = 'hooks'">钩子列表</el-button>
        <el-button type="primary" @click="openCreateDialog">
          {{ activeTab === 'skills' ? '添加技能' : '添加钩子' }}
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="rounded-lg p-2 skills-tabs">
      <!-- ── Skills Tab ── -->
      <el-tab-pane label="技能 (Skills)" name="skills">
        <div class="px-4 py-3 mb-4 rounded-lg text-sm leading-relaxed" style="background:var(--bg-tertiary);border:1px solid var(--border-light);color:var(--text-secondary)">
          <p class="m-0"><strong>技能</strong> 是一段提示词模板，保存在数据库中。AI 对话时，启用的技能会被注入到 system prompt 里，用来定制 AI 的行为方式——比如让 AI 按学术写作风格回答，或按特定标准评审论文。</p>
          <div class="flex items-center gap-1 mt-2 pt-2" style="border-top:1px solid var(--border-light);color:var(--accent-primary)">
            <el-icon :size="14"><QuestionFilled /></el-icon>
            <span>不知道怎么用？</span>
            <el-button link type="primary" @click="$router.push('/tutorials')">查看使用教程</el-button>
          </div>
        </div>

        <div v-loading="skillsLoading" style="min-height:200px">
          <!-- Filter bar -->
          <div class="flex items-center gap-2 mb-4 py-3">
            <el-select v-model="skillFilter.layer" placeholder="层级过滤" clearable size="small" style="width:140px" @change="debouncedLoadSkills">
              <el-option label="全部层级" value="" />
              <el-option label="Soul" value="soul" />
              <el-option label="Agents" value="agents" />
              <el-option label="Identity" value="identity" />
            </el-select>
            <el-select v-model="skillFilter.category" placeholder="分类过滤" clearable size="small" style="width:140px" @change="debouncedLoadSkills">
              <el-option label="全部分类" value="" />
              <el-option label="通用" value="general" />
              <el-option label="社会科学" value="social-science" />
              <el-option label="理工" value="science-engineering" />
              <el-option label="人文" value="humanities" />
            </el-select>
            <el-input
              v-model="skillFilter.topic"
              placeholder="按主题搜索..."
              size="small"
              prefix-icon="Search"
              clearable
              style="width:200px"
              @input="debouncedLoadSkills"
            />
            <el-button size="small" text @click="loadSkillPresets">
              <el-icon><Collection /></el-icon>
              预设模板
            </el-button>
          </div>

          <el-empty v-if="skills.length === 0" description="暂无技能，点击上方添加" />

          <div v-else class="flex flex-col gap-2">
            <div v-for="skill in skills" :key="skill.id" class="skill-card">
              <div class="flex items-center justify-between mb-1_5">
                <div class="flex items-center gap-2">
                  <span class="text-base font-semibold skill-name-text">{{ skill.name }}</span>
                  <el-tag :type="layerTagType(skill.layer)" size="small">{{ skill.layer }}</el-tag>
                  <el-tag v-if="skill.match_topic" size="small" effect="plain">{{ skill.match_topic }}</el-tag>
                  <el-tag v-if="skill.category && skill.category !== 'general'" size="small" type="success" effect="plain">{{ categoryLabel(skill.category) }}</el-tag>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                  <el-switch
                    :model-value="skill.is_active"
                    size="small"
                    @change="handleToggleSkill(skill)"
                  />
                  <el-button text size="small" @click="openEditSkillDialog(skill)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button text size="small" type="danger" @click="handleDeleteSkill(skill)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              <p class="text-sm skill-desc-text m-0 mb-1 leading-normal">{{ skill.description }}</p>
              <p class="text-xs skill-meta-text m-0">优先级: {{ skill.priority }} · 更新于 {{ formatDateShort(skill.updated_at) }}</p>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ── Hooks Tab ── -->
      <el-tab-pane label="钩子 (Hooks)" name="hooks">
        <div class="px-4 py-3 mb-4 warm-bg-amber rounded-lg text-sm skill-desc-text leading-relaxed">
          <p class="m-0"><strong>钩子</strong> 是 AI 操作的生命周期拦截器——在特定时机自动执行。比如：AI 对话前检查频率（限流）、对话后记录日志、出错时触发通知。钩子能让系统更安全可控。</p>
        </div>

        <div v-loading="hooksLoading" style="min-height:200px">
          <el-empty v-if="hooks.length === 0" description="暂无钩子，点击上方添加" />

          <div v-else class="flex flex-col gap-2">
            <div v-for="hook in hooks" :key="hook.id" class="hook-card">
              <div class="flex items-center justify-between mb-1_5">
                <div class="flex items-center gap-2">
                  <span class="text-base font-semibold skill-name-text">{{ hook.name }}</span>
                  <el-tag size="small">{{ hook.hook_point }}</el-tag>
                  <el-tag type="warning" size="small" effect="plain">{{ hook.action_type }}</el-tag>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                  <el-switch
                    :model-value="hook.is_active"
                    size="small"
                    @change="handleToggleHook(hook)"
                  />
                  <el-button text size="small" @click="openEditHookDialog(hook)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button text size="small" type="danger" @click="handleDeleteHook(hook)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              <p class="text-sm skill-desc-text m-0 mb-1 leading-normal">{{ hook.description }}</p>
              <p class="text-xs skill-meta-text m-0">优先级: {{ hook.priority }} · {{ hook.hook_point }} · 更新于 {{ formatDateShort(hook.updated_at) }}</p>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ── Skill 编辑对话框 ── -->
    <el-dialog
      v-model="skillDialogVisible"
      :title="isEditingSkill ? '编辑技能' : '添加技能'"
      width="600px"
    >
      <el-form :model="skillForm" label-width="90px">
        <!-- 层级说明 -->
        <div class="px-3 py-2 mb-4 warm-bg-sky rounded-md text-sm skill-desc-text leading-relaxed">
          <p class="m-0 font-medium mb-1">技能按层级注入（从上到下）：</p>
          <ul class="m-0 pl-4 space-y-0_5">
            <li><strong>Soul（核心身份）</strong>：定义 AI 的根本身份，比如"你是一个论文评审专家"</li>
            <li><strong>Agents（行为规则）</strong>：定义 AI 的行为准则，比如写作风格、评价标准</li>
            <li><strong>Identity（角色设定）</strong>：定义特定场景下的角色扮演，比如"作为一名中文学术助手"</li>
          </ul>
        </div>

        <el-form-item label="名称" required>
          <el-input v-model="skillForm.name" :disabled="isEditingSkill" placeholder="技能名称（小写英文字母，如 academic_writing）" @input="skillForm.name = skillForm.name.replace(/[^a-z_]/g, '')" />
        </el-form-item>
        <el-form-item label="描述" required>
          <el-input v-model="skillForm.description" type="textarea" :rows="2" placeholder="描述技能用途" />
        </el-form-item>
        <el-form-item label="层级" required>
          <el-select v-model="skillForm.layer" style="width:100%">
            <el-option label="Soul — 核心身份，定义 AI 的根身份" value="soul" />
            <el-option label="Agents — 行为规则，定义回答风格和标准" value="agents" />
            <el-option label="Identity — 角色设定，特定场景的角色扮演" value="identity" />
          </el-select>
        </el-form-item>
        <el-form-item label="匹配主题">
          <el-input v-model="skillForm.match_topic" placeholder="例如: paper_review（留空则用于所有对话）" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="skillForm.category" style="width:100%">
            <el-option label="通用 — 适用于所有学科" value="general" />
            <el-option label="社会科学" value="social-science" />
            <el-option label="理工" value="science-engineering" />
            <el-option label="人文" value="humanities" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="skillForm.priority" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input
            v-model="skillForm.content"
            type="textarea"
            :rows="10"
            placeholder="技能提示词内容..."
          />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="skillForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="skillDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="skillSaving" @click="handleSaveSkill">保存</el-button>
      </template>
    </el-dialog>

    <!-- ── Hook 编辑对话框 ── -->
    <el-dialog
      v-model="hookDialogVisible"
      :title="isEditingHook ? '编辑钩子' : '添加钩子'"
      width="560px"
    >
      <el-form :model="hookForm" label-width="100px">
        <!-- 触发点说明 -->
        <div class="px-3 py-2 mb-4 bg-amber-50 border border-amber-100 rounded-md text-sm text-slate-700 leading-relaxed">
          <p class="m-0 font-medium mb-1">钩子在 AI 对话的不同阶段自动执行：</p>
          <ul class="m-0 pl-4 space-y-0_5">
            <li><strong>pre_tool_use（使用前）</strong>：在调用 AI 之前执行，可用于频率限制、权限检查</li>
            <li><strong>post_tool_use（使用后）</strong>：AI 返回结果后执行，通常用于记录日志、统计用量</li>
            <li><strong>on_error（错误时）</strong>：AI 调用失败时触发，用于错误通知、降级处理</li>
          </ul>
        </div>

        <el-form-item label="名称" required>
          <el-input v-model="hookForm.name" :disabled="isEditingHook" placeholder="钩子名称（小写英文字母）" @input="hookForm.name = hookForm.name.replace(/[^a-z_]/g, '')" />
        </el-form-item>
        <el-form-item label="描述" required>
          <el-input v-model="hookForm.description" type="textarea" :rows="2" placeholder="描述钩子行为" />
        </el-form-item>
        <el-form-item label="触发点" required>
          <el-select v-model="hookForm.hook_point" style="width:100%">
            <el-option label="pre_tool_use — 调用 AI 之前（限流/检查）" value="pre_tool_use" />
            <el-option label="post_tool_use — AI 返回之后（日志/统计）" value="post_tool_use" />
            <el-option label="on_error — AI 出错时（通知/降级）" value="on_error" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作类型" required>
          <el-select v-model="hookForm.action_type" style="width:100%">
            <el-option label="Log - 记录日志" value="log" />
            <el-option label="Throttle - 限流" value="throttle" />
            <el-option label="Filter - 过滤" value="filter" />
            <el-option label="Custom - 自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="hookForm.priority" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="hookForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="hookDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="hookSaving" @click="handleSaveHook">保存</el-button>
      </template>
    </el-dialog>

    <!-- ── 预设模板对话框 ── -->
    <el-dialog v-model="presetDialogVisible" title="技能预设模板" width="480px">
      <div v-loading="presetsLoading" class="overflow-y-auto preset-list-wrapper" style="max-height:400px">
        <el-empty v-if="presets.length === 0" description="暂无可用预设" />
        <div
          v-for="preset in presets"
          :key="preset.name"
          class="flex items-center justify-between py-3 preset-item"
        >
          <div class="flex flex-col gap-1">
            <span class="font-semibold text-sm preset-name-text">{{ preset.label_cn }}</span>
            <span class="text-xs preset-meta-text">{{ preset.name }}</span>
            <span class="text-xs preset-desc-text">{{ preset.desc_cn }}</span>
            <el-tag size="small">{{ preset.layer }}</el-tag>
            <el-tag v-if="preset.category && preset.category !== 'general'" size="small" type="success" effect="plain">{{ categoryLabel(preset.category) }}</el-tag>
          </div>
          <el-button size="small" type="primary" @click="handleInstallPreset(preset.name)">
            安装
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Delete, Collection, QuestionFilled } from '@element-plus/icons-vue'
import { formatDateShort } from '@/utils/time'
import {
  getSkills,
  createSkill,
  updateSkill,
  deleteSkill,
  toggleSkill,
  getHooks,
  createHook,
  updateHook,
  deleteHook,
  toggleHook,
  getSkillPresets,
  installPresetSkill,
  type Skill,
  type SkillCreateParams,
  type SkillUpdateParams,
  type Hook,
  type HookCreateParams,
} from '@/api/skills'

// ── Tab ──
const activeTab = ref<'skills' | 'hooks'>('skills')
const router = useRouter()

// ── Skills ──
const skills = ref<Skill[]>([])
const skillsLoading = ref(false)
const skillFilter = reactive({ layer: '', topic: '', category: '' })
let searchTimer: ReturnType<typeof setTimeout> | null = null

function debouncedLoadSkills() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadSkills(), 300)
}

async function loadSkills() {
  skillsLoading.value = true
  try {
    const params: Record<string, any> = {}
    if (skillFilter.layer) params.layer = skillFilter.layer
    if (skillFilter.topic) params.topic = skillFilter.topic
    if (skillFilter.category) params.category = skillFilter.category
    const res = await getSkills(params)
    skills.value = res.items
  } catch {
    skills.value = []
  } finally {
    skillsLoading.value = false
  }
}

// ── Hooks ──
const hooks = ref<Hook[]>([])
const hooksLoading = ref(false)

async function loadHooks() {
  hooksLoading.value = true
  try {
    const res = await getHooks()
    hooks.value = res.items
  } catch {
    hooks.value = []
  } finally {
    hooksLoading.value = false
  }
}

// ── Skill Dialog ──
const skillDialogVisible = ref(false)
const isEditingSkill = ref(false)
const editingSkillId = ref<string | null>(null)
const skillSaving = ref(false)
const skillForm = reactive<SkillCreateParams>({
  name: '',
  description: '',
  layer: 'agents',
  content: '',
  is_active: true,
  match_topic: null,
  category: 'general',
  priority: 50,
})

function resetSkillForm() {
  skillForm.name = ''
  skillForm.description = ''
  skillForm.layer = 'agents'
  skillForm.content = ''
  skillForm.is_active = true
  skillForm.match_topic = null
  skillForm.category = 'general'
  skillForm.priority = 50
}

function openCreateDialog() {
  if (activeTab.value === 'skills') {
    isEditingSkill.value = false
    editingSkillId.value = null
    resetSkillForm()
    skillDialogVisible.value = true
  } else {
    isEditingHook.value = false
    editingHookId.value = null
    resetHookForm()
    hookDialogVisible.value = true
  }
}

function openEditSkillDialog(skill: Skill) {
  isEditingSkill.value = true
  editingSkillId.value = skill.id
  skillForm.name = skill.name
  skillForm.description = skill.description
  skillForm.layer = skill.layer
  skillForm.content = skill.content
  skillForm.is_active = skill.is_active
  skillForm.match_topic = skill.match_topic
  skillForm.category = skill.category || 'general'
  skillForm.priority = skill.priority
  skillDialogVisible.value = true
}

async function handleSaveSkill() {
  if (!skillForm.name || !skillForm.description || !skillForm.content) {
    ElMessage.warning('请填写完整信息')
    return
  }
  skillSaving.value = true
  try {
    if (isEditingSkill.value && editingSkillId.value) {
      const updateData: SkillUpdateParams = {
        description: skillForm.description,
        layer: skillForm.layer,
        content: skillForm.content,
        is_active: skillForm.is_active,
        match_topic: skillForm.match_topic,
        category: skillForm.category,
        priority: skillForm.priority,
      }
      await updateSkill(editingSkillId.value, updateData)
      ElMessage.success('更新成功')
    } else {
      await createSkill({ ...skillForm })
      ElMessage.success('添加成功')
    }
    skillDialogVisible.value = false
    await loadSkills()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    skillSaving.value = false
  }
}

async function handleToggleSkill(skill: Skill) {
  try {
    await toggleSkill(skill.id)
    skill.is_active = !skill.is_active
  } catch {
    ElMessage.error('切换失败')
  }
}

async function handleDeleteSkill(skill: Skill) {
  try {
    await ElMessageBox.confirm(`确定删除技能「${skill.name}」？`, '确认删除', { type: 'warning' })
    await deleteSkill(skill.id)
    ElMessage.success('已删除')
    await loadSkills()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// ── Hook Dialog ──
const hookDialogVisible = ref(false)
const isEditingHook = ref(false)
const editingHookId = ref<string | null>(null)
const hookSaving = ref(false)
const hookForm = reactive<HookCreateParams>({
  name: '',
  description: '',
  hook_point: 'pre_tool_use',
  action_type: 'log',
  priority: 50,
  is_active: true,
})

function resetHookForm() {
  hookForm.name = ''
  hookForm.description = ''
  hookForm.hook_point = 'pre_tool_use'
  hookForm.action_type = 'log'
  hookForm.priority = 50
  hookForm.is_active = true
}

function openEditHookDialog(hook: Hook) {
  isEditingHook.value = true
  editingHookId.value = hook.id
  hookForm.name = hook.name
  hookForm.description = hook.description
  hookForm.hook_point = hook.hook_point
  hookForm.action_type = hook.action_type
  hookForm.priority = hook.priority
  hookForm.is_active = hook.is_active
  hookDialogVisible.value = true
}

async function handleSaveHook() {
  if (!hookForm.name || !hookForm.description) {
    ElMessage.warning('请填写完整信息')
    return
  }
  hookSaving.value = true
  try {
    if (isEditingHook.value && editingHookId.value) {
      await updateHook(editingHookId.value, { ...hookForm })
      ElMessage.success('更新成功')
    } else {
      await createHook({ ...hookForm })
      ElMessage.success('添加成功')
    }
    hookDialogVisible.value = false
    await loadHooks()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    hookSaving.value = false
  }
}

async function handleToggleHook(hook: Hook) {
  try {
    await toggleHook(hook.id)
    hook.is_active = !hook.is_active
  } catch {
    ElMessage.error('切换失败')
  }
}

async function handleDeleteHook(hook: Hook) {
  try {
    await ElMessageBox.confirm(`确定删除钩子「${hook.name}」？`, '确认删除', { type: 'warning' })
    await deleteHook(hook.id)
    ElMessage.success('已删除')
    await loadHooks()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// ── Presets ──
const presetDialogVisible = ref(false)
const presetsLoading = ref(false)
const presets = ref<Awaited<ReturnType<typeof getSkillPresets>>['presets']>([])

async function loadSkillPresets() {
  presetDialogVisible.value = true
  presetsLoading.value = true
  try {
    const res = await getSkillPresets()
    presets.value = res.presets
  } catch {
    presets.value = []
    ElMessage.error('加载预设失败')
  } finally {
    presetsLoading.value = false
  }
}

async function handleInstallPreset(name: string) {
  try {
    await installPresetSkill(name)
    ElMessage.success(`预设「${name}」已安装`)
    await loadSkills()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '安装失败')
  }
}

// ── Helpers ──
function layerTagType(layer: string): 'primary' | 'warning' | 'info' {
  const map: Record<string, 'primary' | 'warning' | 'info'> = {
    soul: 'primary',
    agents: 'warning',
    identity: 'info',
  }
  return map[layer] || 'info'
}

function categoryLabel(category: string): string {
  const map: Record<string, string> = {
    'general': '通用',
    'social-science': '社会科学',
    'science-engineering': '理工',
    'humanities': '人文',
  }
  return map[category] || category
}

// ── Lifecycle ──
onMounted(() => {
  loadSkills()
  loadHooks()
})

watch(activeTab, () => {
  if (activeTab.value === 'skills') loadSkills()
  if (activeTab.value === 'hooks') loadHooks()
})
</script>

<style scoped>
.skills-page {
  padding: 28px 32px 40px;
}

.skills-header {
  margin-bottom: 28px;
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
  letter-spacing: -0.01em;
}

.section-accent {
  margin-left: 4px;
  font-size: 10px;
  font-weight: 600;
  color: var(--sky-300);
  letter-spacing: 0.12em;
}

.preset-list-wrapper > div:last-child {
  border-bottom: none;
}

/* ── Skill Card Styles ── */
.skill-card,
.hook-card {
  padding: 16px 20px;
  border: 1px solid rgba(221,214,200,0.3);
  border-radius: 8px;
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(4px);
  transition: all 0.2s;
}

.skill-card:hover,
.hook-card:hover {
  border-color: rgba(2,132,199,0.25);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.skill-name-text {
  color: var(--text-primary);
}

.skill-desc-text {
  color: var(--text-secondary);
}

.skill-meta-text {
  color: var(--text-muted);
}

/* ── Tabs Background ── */
.skills-tabs {
  background: rgba(255,255,255,0.35);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(221,214,200,0.2);
}

/* ── Info Panels ── */
.warm-bg-amber {
  background: rgba(255,251,235,0.5);
  border: 1px solid rgba(254,243,199,0.4);
}

.warm-bg-sky {
  background: rgba(240,249,255,0.5);
  border: 1px solid rgba(186,230,253,0.3);
}

/* ── Presets ── */
.preset-item {
  border-bottom: 1px solid rgba(221,214,200,0.2);
}

.preset-item:last-child {
  border-bottom: none;
}

.preset-name-text {
  color: var(--text-primary);
}

.preset-meta-text {
  color: var(--text-muted);
}

.preset-desc-text {
  color: var(--text-secondary);
}
</style>
