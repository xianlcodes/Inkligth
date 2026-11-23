<template>
  <section v-if="visible" class="section onboarding-section">
    <el-card class="ob-card" shadow="never">
      <div class="flex items-start justify-between mb-1">
        <h3 class="ob-title">🎉 欢迎来到研墨！完成 3 步，开始高效读文献</h3>
        <el-button link size="small" class="ob-dismiss" @click="dismiss">暂时不再提示</el-button>
      </div>
      <div class="ob-steps">
        <div class="ob-step" :class="{ done: stepUploadDone }">
          <span class="ob-check">{{ stepUploadDone ? '✓' : '1' }}</span>
          <div class="flex-1">
            <div class="ob-step-title">上传第一篇文献</div>
            <div class="ob-step-desc">支持 PDF 等格式，文献会永久保存在你的文献库里</div>
          </div>
          <el-button v-if="!stepUploadDone" type="primary" size="small" @click="$router.push('/literature')">
            去上传
          </el-button>
        </div>

        <div class="ob-step" :class="{ done: stepTranslateDone }">
          <span class="ob-check">{{ stepTranslateDone ? '✓' : '2' }}</span>
          <div class="flex-1">
            <div class="ob-step-title">完成一次文献翻译</div>
            <div class="ob-step-desc">
              你的免费额度还剩
              <strong>{{ authStore.user?.free_translations ?? 0 }}</strong>
              篇（保留原排版的双语对照）
            </div>
          </div>
          <el-button v-if="!stepTranslateDone" size="small" @click="$router.push('/literature')">去翻译</el-button>
        </div>

        <div class="ob-step" :class="{ done: stepKeyDone }">
          <span class="ob-check">{{ stepKeyDone ? '✓' : '3' }}</span>
          <div class="flex-1">
            <div class="ob-step-title">（可选）配置自己的 AI Key，解锁无限量</div>
            <div class="ob-step-desc">
              免费 Key 获取方式见<a href="/tutorials" class="ob-link">使用教程</a>；配置后全文翻译、AI 问答、组会 PPT 全部不限量
            </div>
          </div>
          <el-button v-if="!stepKeyDone" size="small" @click="$router.push('/settings/ai')">去配置</el-button>
        </div>
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getLiteratures } from '@/api/literature'

const DISMISS_KEY = 'onboarding_checklist_dismissed_v1'
const authStore = useAuthStore()
const dismissed = ref(localStorage.getItem(DISMISS_KEY) === '1')
const literatureCount = ref<number | null>(null)

const stepUploadDone = computed(() => (literatureCount.value ?? 0) > 0)
// 消耗过平台额度，或已配置自有引擎，都算完成首次翻译
const stepTranslateDone = computed(
  () => (authStore.user?.free_translations_used ?? 0) > 0 || !!authStore.user?.has_ai_engine,
)
const stepKeyDone = computed(() => !!authStore.user?.has_ai_engine)

// 数据加载完成前不渲染，避免“闪一下就消失”
const ready = ref(false)
const visible = computed(
  () => !dismissed.value && authStore.user != null && !(stepUploadDone.value && stepTranslateDone.value),
)

function dismiss() {
  dismissed.value = true
  localStorage.setItem(DISMISS_KEY, '1')
}

// 监听用户出现：登录瞬间 user 可能尚未加载完（守卫异步拉取），
// 这里等 user 就绪后再查文献数量并亮出卡片，杜绝「闪一下就消失」
watch(
  () => authStore.user?.id,
  async (id) => {
    if (!id) return
    try {
      // 只取 1 条，用 total 判断是否已有文献
      const resp = await getLiteratures({ page: 1, page_size: 1 })
      literatureCount.value = resp.data.total
    } catch {
      literatureCount.value = null
    } finally {
      ready.value = true
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.onboarding-section {
  margin-bottom: 8px;
}

.ob-card {
  border-radius: 12px;
  border: 1px solid var(--el-color-primary-light-7, #d9ecff);
  background: linear-gradient(180deg, var(--el-color-primary-light-9, #f0f7ff) 0%, var(--bg-primary, #fff) 100%);
}

.ob-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
}

.ob-dismiss {
  color: var(--text-secondary, #94a3b8);
}

.ob-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 10px;
}

.ob-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--bg-secondary, #f8fafc);
}

.ob-step.done {
  opacity: 0.62;
}

.ob-check {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
  color: #fff;
  background: var(--el-color-primary, #409eff);
}

.ob-step.done .ob-check {
  background: var(--el-color-success, #67c23a);
}

.ob-step-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary, #1e293b);
}

.ob-step-desc {
  font-size: 12.5px;
  color: var(--text-secondary, #64748b);
  margin-top: 2px;
}

.ob-link {
  color: var(--el-color-primary, #409eff);
  text-decoration: none;
}
</style>
