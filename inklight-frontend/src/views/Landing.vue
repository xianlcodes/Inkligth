<template>
  <div class="min-h-screen bg-white flex flex-col">
    <!-- 导航栏 -->
    <header class="sticky top-0 z-100 bg-white border-b border-slate-200">
      <div class="flex items-center justify-between h-16 px-6" style="max-width:1200px;margin:0 auto">
        <div class="flex items-center gap-2 cursor-pointer" @click="router.push('/')">
          <span class="text-xl font-bold text-sky-600">研墨</span>
          <span class="text-xs text-slate-400 font-normal">InkLight</span>
        </div>
        <nav class="flex gap-2">
          <el-button text @click="router.push('/login')">登录</el-button>
          <el-button type="primary" @click="router.push('/register')">注册</el-button>
        </nav>
      </div>
    </header>

    <!-- Hero 区域 -->
    <section class="flex-1 flex items-center justify-center px-6 py-20" style="background:linear-gradient(180deg,#ffffff 0%,#f0f9ff 50%,#f8fafc 100%)">
      <div class="max-w-[720px] text-center">
        <h1 class="text-[42px] font-extrabold text-slate-900 m-0 mb-4 tracking-tight leading-tight">
          AI 驱动的专业文献阅读平台
        </h1>
        <p class="text-lg text-slate-400 leading-relaxed m-0 mb-10">
          面向学术研究者的文献管理与阅读工具<span class="hidden md:inline"><br /></span>
          集成 AI 翻译、智能分析、笔记管理、组会汇报等功能
        </p>
        <div class="flex gap-4 justify-center flex-wrap">
          <el-button type="primary" size="large" class="!px-8 !py-3_5 !text-base !font-semibold !rounded-xl" @click="router.push('/register')">
            免费开始使用
          </el-button>
          <el-button size="large" class="!px-8 !py-3_5 !text-base !rounded-xl !border-slate-200 !text-slate-600" @click="router.push('/login')">
            我已有账号
          </el-button>
        </div>
      </div>
    </section>

    <!-- 功能特性 -->
    <section class="px-6 py-[60px] pb-20 bg-slate-50">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" style="max-width:1200px;margin:0 auto">
        <div v-for="feature in features" :key="feature.title" class="feature-card">
          <div class="text-[32px] mb-4">{{ feature.icon }}</div>
          <h3 class="text-base font-semibold text-slate-900 m-0 mb-2">{{ feature.title }}</h3>
          <p class="text-sm text-slate-400 leading-relaxed m-0">{{ feature.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="text-center py-8 px-6 border-t border-slate-200">
      <div class="mb-2">
        <router-link to="/terms-of-service" class="text-xs text-slate-400 no-underline mx-3 hover:text-sky-600">用户协议</router-link>
        <router-link to="/privacy-policy" class="text-xs text-slate-400 no-underline mx-3 hover:text-sky-600">隐私政策</router-link>
      </div>
      <p class="text-xs text-slate-400 m-0">&copy; 2026 InkLight 研墨 — 专业文献阅读平台</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const features = [
  { icon: '📄', title: '文献管理', desc: '上传和管理 PDF 文献，自动提取标题、作者、摘要、DOI 等元数据，支持文件夹分类和标签管理。' },
  { icon: '🌐', title: 'AI 翻译', desc: '段落级和全文翻译，支持流式输出，无需手动复制粘贴到外部翻译工具，翻译结果实时展示。' },
  { icon: '📝', title: '笔记与高亮', desc: '在 PDF 上直接高亮标注和记笔记，支持创新点、方法、问题等多种分类，方便复习整理。' },
  { icon: '🤖', title: 'AI 智能分析', desc: '自动生成结构化摘要、识别创新点、提取方法步骤，辅助快速理解论文核心内容，提升阅读效率。' },
  { icon: '📊', title: '组会汇报', desc: '一键生成 PPT 汇报大纲，追踪文献阅读进度，记录阅读时间和页数，轻松准备组会分享。' },
  { icon: '📈', title: '阅读统计', desc: '可视化阅读日历和统计，追踪每周每月阅读量，培养持续阅读习惯，让学术进步可见。' },
]

onMounted(() => {
  if (authStore.isLoggedIn) {
    router.replace('/dashboard')
  }
})
</script>

<style scoped>
.feature-card {
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 32px;
  text-align: left;
  transition: all var(--transition-base);
}
.feature-card:hover {
  border-color: var(--sky-300);
  box-shadow: 0 4px 20px rgba(2, 132, 199, 0.08);
  transform: translateY(-2px);
}
</style>
