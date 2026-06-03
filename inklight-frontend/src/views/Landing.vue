<template>
  <div class="landing-page">
    <!-- 导航栏 -->
    <header class="landing-header">
      <div class="header-inner">
        <div class="header-logo" @click="router.push('/')">
          <span class="logo-name">研墨</span>
          <span class="logo-en">InkLight</span>
        </div>
        <nav class="header-nav">
          <el-button text @click="router.push('/login')">登录</el-button>
          <el-button type="primary" @click="router.push('/register')">注册</el-button>
        </nav>
      </div>
    </header>

    <!-- Hero 区域 -->
    <section class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">AI 驱动的专业文献阅读平台</h1>
        <p class="hero-subtitle">
          面向学术研究者的文献管理与阅读工具<br class="mobile-break" />
          集成 AI 翻译、智能分析、笔记管理、组会汇报等功能
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" class="hero-btn-primary" @click="router.push('/register')">
            免费开始使用
          </el-button>
          <el-button size="large" class="hero-btn-secondary" @click="router.push('/login')">
            我已有账号
          </el-button>
        </div>
      </div>
    </section>

    <!-- 功能特性 -->
    <section class="features-section">
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">📄</div>
          <h3 class="feature-title">文献管理</h3>
          <p class="feature-desc">上传和管理 PDF 文献，自动提取标题、作者、摘要、DOI 等元数据，支持文件夹分类和标签管理。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🌐</div>
          <h3 class="feature-title">AI 翻译</h3>
          <p class="feature-desc">段落级和全文翻译，支持流式输出，无需手动复制粘贴到外部翻译工具，翻译结果实时展示。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📝</div>
          <h3 class="feature-title">笔记与高亮</h3>
          <p class="feature-desc">在 PDF 上直接高亮标注和记笔记，支持创新点、方法、问题等多种分类，方便复习整理。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🤖</div>
          <h3 class="feature-title">AI 智能分析</h3>
          <p class="feature-desc">自动生成结构化摘要、识别创新点、提取方法步骤，辅助快速理解论文核心内容，提升阅读效率。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3 class="feature-title">组会汇报</h3>
          <p class="feature-desc">一键生成 PPT 汇报大纲，追踪文献阅读进度，记录阅读时间和页数，轻松准备组会分享。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📈</div>
          <h3 class="feature-title">阅读统计</h3>
          <p class="feature-desc">可视化阅读日历和统计，追踪每周每月阅读量，培养持续阅读习惯，让学术进步可见。</p>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="landing-footer">
      <div class="footer-links">
        <router-link to="/terms-of-service">用户协议</router-link>
        <router-link to="/privacy-policy">隐私政策</router-link>
      </div>
      <p class="footer-copyright">&copy; 2026 InkLight 研墨 — 专业文献阅读平台</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  // 如果已登录，直接跳转到文献库
  if (authStore.isLoggedIn) {
    router.replace('/literature')
  }
})
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}

/* 导航栏 */
.landing-header {
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.logo-name {
  font-size: 20px;
  font-weight: 700;
  color: #0d9488;
}

.logo-en {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 400;
}

.header-nav {
  display: flex;
  gap: 8px;
}

/* Hero */
.hero-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  background: linear-gradient(180deg, #ffffff 0%, #f0fdfa 50%, #f8fafc 100%);
}

.hero-content {
  max-width: 720px;
  text-align: center;
}

.hero-title {
  font-size: 42px;
  font-weight: 800;
  color: #1e293b;
  margin: 0 0 16px;
  letter-spacing: -1px;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 18px;
  color: #64748b;
  line-height: 1.7;
  margin: 0 0 40px;
}

.mobile-break {
  display: none;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.hero-btn-primary {
  padding: 14px 32px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
}

.hero-btn-secondary {
  padding: 14px 32px;
  font-size: 16px;
  border-radius: 12px;
  border-color: #e2e8f0;
  color: #475569;
}

/* 特性卡片 */
.features-section {
  padding: 60px 24px 80px;
  background: #f8fafc;
}

.features-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.feature-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 32px;
  text-align: left;
  transition: all 0.2s ease;
}

.feature-card:hover {
  border-color: #0d9488;
  box-shadow: 0 4px 20px rgba(13, 148, 136, 0.08);
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 32px;
  margin-bottom: 16px;
}

.feature-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 8px;
}

.feature-desc {
  font-size: 14px;
  color: #64748b;
  line-height: 1.7;
  margin: 0;
}

/* 页脚 */
.landing-footer {
  text-align: center;
  padding: 32px 24px;
  border-top: 1px solid #e2e8f0;
}

.footer-links {
  margin-bottom: 8px;
}

.footer-links a {
  font-size: 13px;
  color: #94a3b8;
  text-decoration: none;
  margin: 0 12px;
}

.footer-links a:hover {
  color: #0d9488;
}

.footer-copyright {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .hero-title {
    font-size: 28px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .mobile-break {
    display: inline;
  }

  .features-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .feature-card {
    padding: 24px;
  }

  .hero-section {
    padding: 48px 20px;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
