<template>
  <div class="px-4 py-4">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold text-slate-800 m-0">AI 引擎配置</h2>
      <div class="flex gap-2">
        <el-button type="primary" @click="openCreateDialog">添加引擎</el-button>
      </div>
    </div>

    <el-skeleton v-if="store.loading" :rows="3" animated />

    <el-empty v-else-if="store.engines.length === 0" description="暂无引擎配置，请点击右上角添加" />

    <div v-else class="grid gap-4" style="grid-template-columns:repeat(auto-fill,minmax(360px,1fr))">
      <el-card v-for="engine in store.engines" :key="engine.id" class="rounded-lg" shadow="hover">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <span class="font-semibold text-base">{{ engine.provider }}</span>
            <el-tag v-if="engine.is_default" type="success" size="small">默认</el-tag>
          </div>
          <div class="flex items-center gap-1">
            <el-button v-if="!engine.is_default" link type="primary" size="small" @click="handleSetDefault(engine.id)">
              设为默认
            </el-button>
            <el-button link type="primary" size="small" @click="openEditDialog(engine)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(engine.id)">删除</el-button>
          </div>
        </div>

        <div>
          <p class="text-sm text-slate-500 my-1"><strong class="text-slate-700">模型：</strong>{{ engine.default_model }}</p>
          <p class="text-sm text-slate-500 my-1"><strong class="text-slate-700">API 地址：</strong>{{ engine.api_base }}</p>
          <p class="text-sm text-slate-500 my-1"><strong class="text-slate-700">Key：</strong>{{ engine.api_key_mask }}</p>
          <p v-if="engine.fallback_models" class="text-sm text-slate-500 my-1"><strong class="text-slate-700">备用模型：</strong>{{ engine.fallback_models }}</p>
          <p class="text-sm text-slate-500 my-1">
            <strong class="text-slate-700">代理：</strong>
            <el-tag :type="engine.proxy_enabled ? 'warning' : 'info'" size="small">
              {{ engine.proxy_enabled ? '已开启' : '未开启' }}
            </el-tag>
          </p>
        </div>
      </el-card>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑引擎' : '添加引擎'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="供应商" prop="provider">
          <el-select v-model="form.provider" filterable allow-create placeholder="请选择或输入供应商" @change="onProviderChange">
            <el-option label="OpenAI" value="openai" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="Qwen (通义千问)" value="qwen" />
            <el-option label="GLM (智谱)" value="glm" />
          </el-select>
        </el-form-item>

        <el-form-item label="API 地址" prop="api_base">
          <el-input v-model="form.api_base" :placeholder="apiBasePlaceholder" />
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <div v-if="isEdit && editingKeyMask" class="text-xs text-slate-400 mb-1">当前 Key: {{ editingKeyMask }}</div>
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="isEdit ? '留空则不修改' : 'sk-...'"
          />
        </el-form-item>

        <el-form-item label="默认模型" prop="default_model">
          <el-input v-model="form.default_model" :placeholder="modelPlaceholder" />
        </el-form-item>

        <el-form-item label="备用模型">
          <el-input v-model="form.fallback_models" placeholder="多个模型用逗号分隔，可选" />
        </el-form-item>

        <el-form-item label="启用代理">
          <el-switch v-model="form.proxy_enabled" />
          <span class="text-xs text-slate-400 ml-2">通过服务器代理访问 AI 服务（如 OpenAI 需要）</span>
        </el-form-item>

        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>

        <el-form-item>
          <el-button :loading="testing" @click="handleTest">测试连接</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </el-form-item>

        <div class="flex items-center gap-1 px-3 py-2 mt-2 bg-sky-50 border border-sky-100 rounded-md text-sm text-sky-700 tutorial-hint">
          <el-icon :size="14"><QuestionFilled /></el-icon>
          <span>添加有问题？</span>
          <el-button link type="primary" @click="$router.push('/tutorials')">可以看教程</el-button>
        </div>

        <div v-if="testResult" class="mt-3">
          <el-alert :title="testResult.message" :type="testResult.success ? 'success' : 'error'" :closable="false" />
          <div v-if="testResult.models.length > 0" class="mt-2">
            <p>可用模型：</p>
            <el-tag v-for="m in testResult.models.slice(0, 10)" :key="m" size="small" class="mr-1_5 mb-1_5">{{ m }}</el-tag>
            <span v-if="testResult.models.length > 10">等共 {{ testResult.models.length }} 个模型</span>
          </div>
        </div>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAiEngineStore } from '@/stores/aiEngine'
import type { AIEngine, AIEngineTestResult } from '@/api/aiEngine'

const store = useAiEngineStore()
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<string | null>(null)
const editingKeyMask = ref('')
const testing = ref(false)
const saving = ref(false)
const testResult = ref<AIEngineTestResult | null>(null)

const providerDefaults: Record<string, { apiBase: string; model: string }> = {
  openai: { apiBase: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  deepseek: { apiBase: 'https://api.deepseek.com', model: 'deepseek-v4-flash' },
  qwen: { apiBase: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  glm: { apiBase: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4.7-flash' },
}

const apiBasePlaceholder = computed(() => {
  const key = form.provider?.toLowerCase()
  return providerDefaults[key]?.apiBase || 'https://api.example.com/v1'
})

const modelPlaceholder = computed(() => {
  const key = form.provider?.toLowerCase()
  return providerDefaults[key]?.model || 'model-name'
})

const formRef = ref<FormInstance>()
const form = reactive({
  provider: '',
  api_base: '',
  api_key: '',
  default_model: '',
  fallback_models: '',
  is_default: false,
  proxy_enabled: false,
})

const rules: FormRules = {
  provider: [{ required: true, message: '请选择供应商', trigger: 'change' }],
  api_base: [{ required: true, message: '请输入 API 地址', trigger: 'blur' }],
  api_key: [{
    validator: (_rule, value, callback) => {
      if (!isEdit.value && !value) {
        callback(new Error('请输入 API Key'))
      } else {
        callback()
      }
    },
    trigger: 'blur',
  }],
  default_model: [{ required: true, message: '请输入默认模型', trigger: 'blur' }],
}

onMounted(() => {
  store.loadEngines()
})

function resetForm() {
  form.provider = ''
  form.api_base = ''
  form.api_key = ''
  form.default_model = ''
  form.fallback_models = ''
  form.is_default = false
  form.proxy_enabled = false
  testResult.value = null
}

function onProviderChange(value: string) {
  const key = value?.toLowerCase()
  const defaults = providerDefaults[key]
  if (defaults && !isEdit.value) {
    form.api_base = defaults.apiBase
    form.default_model = defaults.model
  }
}

function openCreateDialog() {
  isEdit.value = false
  editingId.value = null
  editingKeyMask.value = ''
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(engine: AIEngine) {
  isEdit.value = true
  editingId.value = engine.id
  editingKeyMask.value = engine.api_key_mask
  form.provider = engine.provider
  form.api_base = engine.api_base
  form.api_key = ''
  form.default_model = engine.default_model
  form.fallback_models = engine.fallback_models || ''
  form.is_default = engine.is_default
  form.proxy_enabled = engine.proxy_enabled
  testResult.value = null
  dialogVisible.value = true
}

async function handleTest() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  testing.value = true
  testResult.value = null
  try {
    if (isEdit.value && editingId.value) {
      const res = await store.testConnection(editingId.value)
      testResult.value = res
    } else {
      ElMessage.info('请先保存引擎后再测试连接')
    }
  } catch (e: any) {
    testResult.value = {
      success: false,
      message: e?.response?.data?.detail || '测试失败',
      models: [],
    }
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      provider: form.provider,
      api_base: form.api_base,
      api_key: form.api_key,
      default_model: form.default_model,
      fallback_models: form.fallback_models || undefined,
      is_default: form.is_default,
      proxy_enabled: form.proxy_enabled,
    }

    if (isEdit.value && editingId.value) {
      const updatePayload: Record<string, any> = {}
      if (form.provider) updatePayload.provider = form.provider
      if (form.api_base) updatePayload.api_base = form.api_base
      if (form.api_key) updatePayload.api_key = form.api_key
      if (form.default_model) updatePayload.default_model = form.default_model
      if (form.fallback_models !== undefined) updatePayload.fallback_models = form.fallback_models || null
      if (form.is_default !== undefined) updatePayload.is_default = form.is_default
      if (form.proxy_enabled !== undefined) updatePayload.proxy_enabled = form.proxy_enabled
      await store.editEngine(editingId.value, updatePayload)
      ElMessage.success('更新成功')
    } else {
      await store.addEngine(payload)
      ElMessage.success('添加成功')
    }

    dialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSetDefault(engineId: string) {
  try {
    await store.setAsDefault(engineId)
    ElMessage.success('已设为默认引擎')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '设置失败')
  }
}

async function handleDelete(engineId: string) {
  try {
    await ElMessageBox.confirm('确定要删除该引擎配置吗？', '提示', { type: 'warning' })
    await store.removeEngine(engineId)
    ElMessage.success('删除成功')
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '删除失败')
    }
  }
}
</script>

<style scoped>
.tutorial-hint .el-icon {
  color: var(--accent-primary);
}
</style>
