<template>
  <div class="il-wrapper">
    <div class="il-container">

        <!-- ═══ Header ═══ -->
        <header class="il-header">
          <a href="/" class="il-logo" aria-label="研墨 InkLight 首页">
            <span class="il-logo-icon">研</span>
            <span class="il-logo-text">研墨</span>
            <span class="il-logo-lang">InkLight</span>
          </a>
          <nav class="il-nav">
            <a href="/login" class="il-nav-link">登录</a>
            <a href="/register" class="il-btn il-btn-primary">注册</a>
          </nav>
        </header>

        <!-- ═══ Hero ═══ -->
        <section class="il-hero">
          <div class="il-hero-badge">AI 驱动的学术文献平台</div>
          <h1>让文献阅读，<br/><span class="il-highlight">回归学术本身</span></h1>
          <p class="il-hero-sub">
            研墨面向学术研究者，提供文献管理、AI 翻译、智能分析与笔记协作<br/>
            — 将宝贵精力还给思考，而非工具切换
          </p>
          <div class="il-hero-actions">
            <a href="/register" class="il-btn il-btn-primary il-btn-lg">免费开始使用</a>
            <a href="/login" class="il-btn il-btn-ghost il-btn-lg">已有账号？登录</a>
          </div>
          <div class="il-metrics">
            <div class="il-metric">
              <div class="il-metric-value">PDF</div>
              <div class="il-metric-label">文献格式支持</div>
            </div>
            <div class="il-metric">
              <div class="il-metric-value">AI</div>
              <div class="il-metric-label">智能翻译与分析</div>
            </div>
            <div class="il-metric">
              <div class="il-metric-value">笔记</div>
              <div class="il-metric-label">标注与知识管理</div>
            </div>
            <div class="il-metric">
              <div class="il-metric-value">汇报</div>
              <div class="il-metric-label">组会大纲一键生成</div>
            </div>
          </div>
        </section>

        <!-- ═══ Features ═══ -->
        <section class="il-features">
          <div class="il-features-heading">
            <h2>围绕研究者的真实工作流设计</h2>
            <p>从读文献到做汇报，每个环节都经过精心打磨</p>
          </div>

          <!-- Feature 1 -->
          <div class="il-feature-row">
            <div class="il-feature-content">
              <span class="il-feature-number">01 — 文献管理</span>
              <h3>导入文献，元数据自动提取</h3>
              <p class="il-feature-desc">
                上传 PDF 后自动识别标题、作者、摘要、DOI 等信息，支持文件夹分类和标签管理。无需手动整理，文献库即刻井井有条。
              </p>
              <p class="il-feature-desc">
                批量导入、拖拽上传，与你的研究流程无缝衔接。
              </p>
              <div class="il-feature-tags">
                <span class="il-feature-tag">批量导入</span>
                <span class="il-feature-tag">DOI 识别</span>
                <span class="il-feature-tag">分类管理</span>
              </div>
            </div>
            <div class="il-feature-visual">
              <div class="il-visual-box">
                <div class="il-visual-list">
                  <div class="il-visual-list-header">
                    <span class="vlh-title">我的文献</span>
                    <span class="vlh-btn">+ 导入</span>
                  </div>
                  <div class="il-visual-paper-item">
                    <div class="vpi-title"><span class="vpi-dot"></span> Attention Is All You Need</div>
                    <div class="vpi-meta">
                      <span>Vaswani et al.</span>
                      <span>2017</span>
                    </div>
                    <div class="vpi-tags">
                      <span>NLP</span>
                      <span>Transformer</span>
                    </div>
                  </div>
                  <div class="il-visual-paper-item">
                    <div class="vpi-title"><span class="vpi-dot"></span> Deep Learning</div>
                    <div class="vpi-meta">
                      <span>Goodfellow et al.</span>
                      <span>2016</span>
                    </div>
                    <div class="vpi-tags">
                      <span>深度学习</span>
                      <span>综述</span>
                    </div>
                  </div>
                  <div class="il-visual-paper-item">
                    <div class="vpi-title"><span class="vpi-dot"></span> BERT: Pre-training of Deep...</div>
                    <div class="vpi-meta">
                      <span>Devlin et al.</span>
                      <span>2019</span>
                    </div>
                    <div class="vpi-tags">
                      <span>NLP</span>
                      <span>预训练</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Feature 2 -->
          <div class="il-feature-row">
            <div class="il-feature-content">
              <span class="il-feature-number">02 — 阅读与翻译</span>
              <h3>边读边译，沉浸式阅读体验</h3>
              <p class="il-feature-desc">
                段落级 AI 翻译，支持流式输出，原文与译文并排对照。无需离开阅读器，即可跨越语言障碍。
              </p>
              <p class="il-feature-desc">
                自定义翻译引擎，适配不同学科术语习惯。
              </p>
              <div class="il-feature-tags">
                <span class="il-feature-tag">流式翻译</span>
                <span class="il-feature-tag">原文对照</span>
                <span class="il-feature-tag">多引擎</span>
              </div>
            </div>
            <div class="il-feature-visual">
              <div class="il-visual-box">
                <div class="il-visual-trans">
                  <div class="vt-tabs">
                    <span class="active">双语对照</span>
                    <span>原文</span>
                    <span>译文</span>
                  </div>
                  <div class="vt-body">
                    <div class="vt-col">
                      <span class="vt-col-label">EN</span>
                      <div class="vt-line long"></div>
                      <div class="vt-line medium"></div>
                      <div class="vt-line long"></div>
                      <div class="vt-line short"></div>
                      <div class="vt-line medium"></div>
                      <div class="vt-line long" style="margin-top:6px"></div>
                      <div class="vt-line medium"></div>
                      <div class="vt-line short"></div>
                    </div>
                    <div class="vt-col">
                      <span class="vt-col-label">中</span>
                      <div class="vt-line accent long"></div>
                      <div class="vt-line accent medium"></div>
                      <div class="vt-line accent long"></div>
                      <div class="vt-line accent short"></div>
                      <div class="vt-line accent medium"></div>
                      <div class="vt-line accent long" style="margin-top:6px"></div>
                      <div class="vt-line accent medium"></div>
                      <div class="vt-line accent short"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Feature 3 -->
          <div class="il-feature-row">
            <div class="il-feature-content">
              <span class="il-feature-number">03 — 智能分析</span>
              <h3>AI 提炼核心，快速掌握论文全貌</h3>
              <p class="il-feature-desc">
                自动生成结构化摘要，识别创新点、研究方法与关键结论。在精读之前，先用 AI 预览判断相关性。
              </p>
              <p class="il-feature-desc">
                支持多轮追问式对话，深入理解论文细节。
              </p>
              <div class="il-feature-tags">
                <span class="il-feature-tag">结构化摘要</span>
                <span class="il-feature-tag">创新点识别</span>
                <span class="il-feature-tag">追问对话</span>
              </div>
            </div>
            <div class="il-feature-visual">
              <div class="il-visual-box">
                <div class="il-visual-analysis">
                  <div class="va-header">AI 智能摘要</div>
                  <div class="va-section">
                    <div class="va-label">创新点</div>
                    <div class="va-bullet">提出 Transformer 纯注意力架构</div>
                    <div class="va-bullet">取消递归与卷积，实现并行训练</div>
                  </div>
                  <div class="va-section">
                    <div class="va-label">方法</div>
                    <div class="va-bullet">多头自注意力机制 (Multi-Head Attention)</div>
                    <div class="va-bullet">Positional Encoding 引入序列位置信息</div>
                  </div>
                  <div class="va-conclusion">机器翻译 WMT 2014 英德/英法任务达到 SOTA</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Feature 4 -->
          <div class="il-feature-row">
            <div class="il-feature-content">
              <span class="il-feature-number">04 — 笔记与汇报</span>
              <h3>从笔记到组会，一键生成汇报大纲</h3>
              <p class="il-feature-desc">
                在 PDF 上直接高亮标注、记录笔记，支持分类管理。阅读进度与笔记内容自动关联，复习时一目了然。
              </p>
              <p class="il-feature-desc">
                基于文献笔记一键生成组会 PPT 大纲，节省准备时间。
              </p>
              <div class="il-feature-tags">
                <span class="il-feature-tag">PDF 标注</span>
                <span class="il-feature-tag">分类笔记</span>
                <span class="il-feature-tag">汇报大纲</span>
              </div>
            </div>
            <div class="il-feature-visual">
              <div class="il-visual-box">
                <div class="il-visual-notes">
                  <div class="vn-tabs">
                    <span class="active">笔记</span>
                    <span>标签</span>
                    <span>汇报大纲</span>
                  </div>
                  <div class="il-visual-note-card">
                    <div class="vn-title"><span class="vn-icon"></span> 关键贡献</div>
                    <div class="vn-line long"></div>
                    <div class="vn-line medium"></div>
                  </div>
                  <div class="il-visual-note-card">
                    <div class="vn-title"><span class="vn-icon"></span> 实验设置</div>
                    <div class="vn-line medium"></div>
                    <div class="vn-line short"></div>
                  </div>
                  <div class="il-visual-note-card is-outline">
                    <div class="vn-title"><span class="vn-icon"></span> 组会汇报大纲</div>
                    <div class="vn-outline-item"><span class="vn-num">1</span> 研究背景与动机</div>
                    <div class="vn-outline-item"><span class="vn-num">2</span> 方法设计</div>
                    <div class="vn-outline-item"><span class="vn-num">3</span> 实验结果分析</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- ═══ CTA ═══ -->
        <section class="il-cta">
          <h2>准备开始你的高效研究了吗？</h2>
          <p>注册即用，按需配置 AI 引擎。让研墨成为你学术道路上的得力助手。</p>
          <div class="il-cta-actions">
            <a href="/register" class="il-btn il-btn-primary il-btn-lg">免费开始使用</a>
            <a href="/login" class="il-btn il-btn-ghost il-btn-lg">登录</a>
          </div>
        </section>

        <!-- ═══ Footer ═══ -->
        <footer class="il-footer">
          <div class="il-footer-inner">
            <p class="il-footer-copy">&copy; 2026 InkLight 研墨 — 专业文献阅读平台</p>
            <nav class="il-footer-links">
              <a href="/terms-of-service">用户协议</a>
              <a href="/privacy-policy">隐私政策</a>
            </nav>
          </div>
        </footer>

      </div>
      </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  if (authStore.isLoggedIn) {
    router.replace('/dashboard')
  }
})
</script>

<style>
/* ══════════════════════════════════════════════
         InkLight — 研墨 Landing Fallback
         Scholarly ink-and-paper design language
         ══════════════════════════════════════════════ */

      /* ── Reset ── */
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

      html { scroll-behavior: smooth; }

      /* ── Full-width wrapper with paper background and grain ── */
      .il-wrapper {
        background: #faf7f2;
        min-height: 100vh;
        position: relative;
      }

      /* Paper grain texture overlay */
      .il-wrapper::after {
        content: '';
        position: fixed;
        inset: 0;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.5'/%3E%3C/svg%3E");
        background-repeat: repeat;
        background-size: 256px 256px;
        opacity: 0.4;
        pointer-events: none;
        z-index: 0;
        mix-blend-mode: multiply;
      }

      .il-wrapper > * {
        position: relative;
        z-index: 1;
      }

      /* ── Container ── */
      .il-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 28px;
        position: relative;
      }

      /* ════════════════
         Header
         ════════════════ */
      .il-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 24px 0;
        position: relative;
      }

      .il-header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, #d4cdc4 30%, #d4cdc4 70%, transparent 100%);
      }

      .il-logo {
        display: flex;
        align-items: baseline;
        gap: 6px;
        text-decoration: none;
      }

      .il-logo-icon {
        font-family: 'Noto Serif SC', serif;
        font-size: 26px;
        font-weight: 900;
        color: #2c2420;
        line-height: 1;
      }

      .il-logo-text {
        font-family: 'Noto Serif SC', serif;
        font-size: 20px;
        font-weight: 700;
        color: #2c2420;
        letter-spacing: 0.06em;
      }

      .il-logo-lang {
        font-size: 13px;
        font-weight: 500;
        color: #9a8c80;
        margin-left: 4px;
        letter-spacing: 0.03em;
      }

      .il-nav {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .il-nav a {
        text-decoration: none;
        font-size: 14px;
        font-weight: 500;
        transition: color 0.2s ease;
        padding: 8px 6px;
      }

      .il-nav-link {
        color: #6b5d53;
      }
      .il-nav-link:hover {
        color: #2c2420;
      }

      /* ── Buttons ── */
      .il-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 15px;
        border: none;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
        position: relative;
        overflow: hidden;
      }
      .il-btn:active {
        transform: scale(0.97);
      }

      .il-btn-primary {
        padding: 10px 24px;
        border-radius: 10px;
        background: #2c6b5e;
        color: #fff;
        box-shadow: 0 2px 8px -2px rgba(44, 107, 94, 0.25);
      }
      .il-btn-primary:hover {
        background: #24584d;
        box-shadow: 0 6px 16px -4px rgba(44, 107, 94, 0.35);
        transform: translateY(-1px);
      }
      .il-btn-primary:active {
        transform: translateY(0) scale(0.97);
      }

      .il-btn-ghost {
        padding: 10px 20px;
        border-radius: 10px;
        background: transparent;
        color: #6b5d53;
        border: 1px solid #d4cdc4;
      }
      .il-btn-ghost:hover {
        border-color: #b8aa9c;
        color: #2c2420;
        background: rgba(44, 107, 94, 0.04);
      }

      .il-btn-lg {
        padding: 14px 34px;
        font-size: 16px;
        border-radius: 12px;
      }

      /* ════════════════
         Hero
         ════════════════ */
      .il-hero {
        padding: 100px 0 80px;
        text-align: center;
        position: relative;
      }

      /* Subtle ink-wash decorative circle */
      .il-hero::before {
        content: '';
        position: absolute;
        top: -80px;
        left: 50%;
        transform: translateX(-50%);
        width: 600px;
        height: 600px;
        background: radial-gradient(circle at center, rgba(44, 107, 94, 0.04) 0%, rgba(44, 107, 94, 0.02) 40%, transparent 70%);
        pointer-events: none;
        border-radius: 50%;
      }

      .il-hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 16px;
        border-radius: 100px;
        background: rgba(44, 107, 94, 0.08);
        color: #2c6b5e;
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 32px;
        letter-spacing: 0.02em;
      }

      .il-hero-badge::before {
        content: '';
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #2c6b5e;
        opacity: 0.5;
      }

      .il-hero h1 {
        font-family: 'Noto Serif SC', serif;
        font-size: clamp(38px, 6vw, 60px);
        font-weight: 900;
        color: #1a1512;
        line-height: 1.25;
        letter-spacing: -0.02em;
        margin-bottom: 24px;
        text-wrap: balance;
      }

      .il-hero h1 .il-highlight {
        color: #2c6b5e;
      }

      .il-hero-sub {
        font-size: clamp(16px, 2.2vw, 19px);
        color: #6b5d53;
        max-width: 560px;
        margin: 0 auto 44px;
        line-height: 1.7;
        text-wrap: balance;
      }

      .il-hero-actions {
        display: flex;
        gap: 16px;
        justify-content: center;
        flex-wrap: wrap;
      }

      /* ── Hero metrics bar ── */
      .il-metrics {
        display: flex;
        justify-content: center;
        gap: 48px;
        margin-top: 64px;
        padding-top: 40px;
        position: relative;
      }

      .il-metrics::before {
        content: '';
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 120px;
        height: 1px;
        background: #d4cdc4;
      }

      .il-metric {
        text-align: center;
      }

      .il-metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #2c2420;
        font-variant-numeric: tabular-nums;
      }

      .il-metric-label {
        font-size: 13px;
        color: #9a8c80;
        margin-top: 4px;
        font-weight: 500;
        letter-spacing: 0.03em;
      }

      /* ════════════════
         Features — alternating 2-column
         ════════════════ */
      .il-features {
        padding: 80px 0 40px;
      }

      .il-features-heading {
        text-align: center;
        margin-bottom: 72px;
      }

      .il-features-heading h2 {
        font-family: 'Noto Serif SC', serif;
        font-size: 32px;
        font-weight: 700;
        color: #1a1512;
        margin-bottom: 12px;
        letter-spacing: -0.01em;
      }

      .il-features-heading p {
        color: #6b5d53;
        font-size: 16px;
        max-width: 480px;
        margin: 0 auto;
      }

      .il-feature-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 60px;
        align-items: center;
        padding: 60px 0;
        position: relative;
      }

      .il-feature-row + .il-feature-row {
        border-top: 1px solid #ede8e0;
      }

      .il-feature-row:nth-child(even) .il-feature-visual {
        order: -1;
      }

      .il-feature-number {
        font-family: 'Noto Serif SC', serif;
        font-size: 14px;
        font-weight: 600;
        color: #2c6b5e;
        letter-spacing: 0.08em;
        margin-bottom: 12px;
        display: block;
      }

      .il-feature-content h3 {
        font-family: 'Noto Serif SC', serif;
        font-size: 26px;
        font-weight: 700;
        color: #1a1512;
        margin-bottom: 16px;
        text-wrap: balance;
      }

      .il-feature-desc {
        color: #5c4f45;
        font-size: 15px;
        line-height: 1.7;
        max-width: 440px;
        text-wrap: pretty;
      }

      .il-feature-desc + .il-feature-desc {
        margin-top: 12px;
      }

      .il-feature-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 20px;
      }

      .il-feature-tag {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 6px;
        background: rgba(44, 107, 94, 0.07);
        color: #2c6b5e;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.02em;
      }

      /* ── Feature visual blocks ── */
      .il-feature-visual {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .il-visual-box {
        width: 100%;
        aspect-ratio: 4 / 3;
        border-radius: 20px;
        background: linear-gradient(145deg, #f3efe8, #ece7de);
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .il-visual-box::after {
        content: '';
        position: absolute;
        inset: 0;
        border: 1px solid rgba(44, 107, 94, 0.06);
        border-radius: 20px;
        pointer-events: none;
      }

      /* Decorative ink-wash character */
      .il-visual-char {
        font-family: 'Noto Serif SC', serif;
        font-size: 100px;
        font-weight: 900;
        color: rgba(44, 107, 94, 0.12);
        line-height: 1;
        user-select: none;
        transition: opacity 0.4s ease;
      }

      .il-visual-mini-cards {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        padding: 24px;
        width: 100%;
      }

      .il-visual-mini-card {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(4px);
        border-radius: 12px;
        padding: 18px 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        border: 1px solid rgba(255,255,255,0.5);
      }

      .il-visual-mini-card .mini-line {
        height: 8px;
        border-radius: 4px;
        background: #ede8e0;
        margin-bottom: 8px;
      }
      .il-visual-mini-card .mini-line:last-child { margin-bottom: 0; }
      .il-visual-mini-card .mini-line.short { width: 60%; }
      .il-visual-mini-card .mini-line.medium { width: 80%; }
      .il-visual-mini-card .mini-line.accent { background: rgba(44, 107, 94, 0.2); width: 45%; }
      .il-visual-mini-card .mini-line.sm { height: 6px; width: 50%; }

      .il-visual-mini-card .mini-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: rgba(44, 107, 94, 0.15);
        display: inline-block;
        margin-right: 6px;
      }

      .il-visual-mini-card .mini-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }

      /* ── Interface mockup: Paper list (Feature 1) ── */
      .il-visual-list {
        width: 100%;
        padding: 20px 24px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .il-visual-list-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
      }

      .il-visual-list-header .vlh-title {
        font-size: 12px;
        font-weight: 600;
        color: #5c4f45;
        letter-spacing: 0.03em;
      }

      .il-visual-list-header .vlh-btn {
        font-size: 11px;
        padding: 3px 10px;
        border-radius: 5px;
        background: rgba(44, 107, 94, 0.12);
        color: #2c6b5e;
        font-weight: 600;
      }

      .il-visual-paper-item {
        background: rgba(255,255,255,0.75);
        backdrop-filter: blur(4px);
        border-radius: 10px;
        padding: 12px 14px;
        border: 1px solid rgba(255,255,255,0.6);
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
      }

      .il-visual-paper-item .vpi-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        font-weight: 600;
        color: #2c2420;
        margin-bottom: 6px;
      }

      .il-visual-paper-item .vpi-title .vpi-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #2c6b5e;
        flex-shrink: 0;
      }

      .il-visual-paper-item .vpi-meta {
        display: flex;
        gap: 12px;
        font-size: 11px;
        color: #9a8c80;
        margin-bottom: 6px;
      }

      .il-visual-paper-item .vpi-tags {
        display: flex;
        gap: 6px;
      }

      .il-visual-paper-item .vpi-tags span {
        font-size: 10px;
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(44, 107, 94, 0.07);
        color: #2c6b5e;
      }

      .il-visual-paper-item .vpi-tags span:nth-child(2) {
        background: rgba(107, 93, 83, 0.07);
        color: #6b5d53;
      }

      /* ── Interface mockup: Translation panel (Feature 2) ── */
      .il-visual-trans {
        width: 100%;
        padding: 16px 20px;
        display: flex;
        flex-direction: column;
        gap: 0;
        height: 100%;
      }

      .il-visual-trans .vt-tabs {
        display: flex;
        gap: 16px;
        margin-bottom: 12px;
        border-bottom: 1px solid rgba(44, 107, 94, 0.1);
        padding-bottom: 8px;
      }

      .il-visual-trans .vt-tabs span {
        font-size: 11px;
        font-weight: 600;
        color: #9a8c80;
        padding-bottom: 8px;
        margin-bottom: -9px;
        letter-spacing: 0.03em;
      }

      .il-visual-trans .vt-tabs span.active {
        color: #2c6b5e;
        border-bottom: 2px solid #2c6b5e;
      }

      .il-visual-trans .vt-body {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        flex: 1;
      }

      .il-visual-trans .vt-col {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .il-visual-trans .vt-col .vt-col-label {
        font-size: 10px;
        font-weight: 600;
        color: #9a8c80;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
      }

      .il-visual-trans .vt-line {
        height: 7px;
        border-radius: 3px;
        background: #ede8e0;
      }

      .il-visual-trans .vt-line.short { width: 55%; }
      .il-visual-trans .vt-line.medium { width: 78%; }
      .il-visual-trans .vt-line.long { width: 92%; }
      .il-visual-trans .vt-line.accent { background: rgba(44, 107, 94, 0.15); }

      /* ── Interface mockup: AI Analysis card (Feature 3) ── */
      .il-visual-analysis {
        width: 100%;
        padding: 18px 22px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .il-visual-analysis .va-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-weight: 600;
        color: #2c6b5e;
        letter-spacing: 0.02em;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(44, 107, 94, 0.08);
      }

      .il-visual-analysis .va-header::before {
        content: '';
        width: 14px;
        height: 14px;
        border-radius: 4px;
        background: rgba(44, 107, 94, 0.15);
      }

      .il-visual-analysis .va-section {
        margin-bottom: 2px;
      }

      .il-visual-analysis .va-section .va-label {
        font-size: 10px;
        font-weight: 600;
        color: #9a8c80;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
      }

      .il-visual-analysis .va-section .va-bullet {
        font-size: 11px;
        color: #5c4f45;
        line-height: 1.8;
        padding-left: 12px;
        position: relative;
      }

      .il-visual-analysis .va-section .va-bullet::before {
        content: '';
        position: absolute;
        left: 0;
        top: 8px;
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: rgba(44, 107, 94, 0.3);
      }

      .il-visual-analysis .va-conclusion {
        margin-top: 4px;
        padding-top: 8px;
        border-top: 1px solid rgba(44, 107, 94, 0.08);
        font-size: 11px;
        color: #2c6b5e;
        font-weight: 500;
      }

      .il-visual-analysis .va-conclusion::before {
        content: '→ ';
      }

      /* ── Interface mockup: Notes & Outline (Feature 4) ── */
      .il-visual-notes {
        width: 100%;
        padding: 16px 20px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        height: 100%;
      }

      .il-visual-notes .vn-tabs {
        display: flex;
        gap: 14px;
        border-bottom: 1px solid rgba(44, 107, 94, 0.1);
        padding-bottom: 7px;
        margin-bottom: 4px;
      }

      .il-visual-notes .vn-tabs span {
        font-size: 11px;
        font-weight: 600;
        color: #9a8c80;
        padding-bottom: 7px;
        margin-bottom: -8px;
        letter-spacing: 0.02em;
      }

      .il-visual-notes .vn-tabs span.active {
        color: #2c6b5e;
        border-bottom: 2px solid #2c6b5e;
      }

      .il-visual-note-card {
        background: rgba(255,255,255,0.75);
        backdrop-filter: blur(4px);
        border-radius: 9px;
        padding: 10px 12px;
        border: 1px solid rgba(255,255,255,0.6);
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        display: flex;
        flex-direction: column;
        gap: 5px;
      }

      .il-visual-note-card .vn-title {
        font-size: 11px;
        font-weight: 600;
        color: #2c2420;
        display: flex;
        align-items: center;
        gap: 5px;
      }

      .il-visual-note-card .vn-title .vn-icon {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        background: rgba(44, 107, 94, 0.12);
        flex-shrink: 0;
      }

      .il-visual-note-card .vn-line {
        height: 6px;
        border-radius: 3px;
        background: #ede8e0;
      }

      .il-visual-note-card .vn-line.short { width: 50%; }
      .il-visual-note-card .vn-line.medium { width: 72%; }
      .il-visual-note-card .vn-line.long { width: 88%; }

      .il-visual-note-card.is-outline {
        background: rgba(44, 107, 94, 0.06);
        border-color: rgba(44, 107, 94, 0.1);
      }

      .il-visual-note-card.is-outline .vn-title .vn-icon {
        background: rgba(44, 107, 94, 0.2);
      }

      .il-visual-note-card.is-outline .vn-line.accent {
        background: rgba(44, 107, 94, 0.15);
      }

      .il-visual-note-card .vn-outline-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 10px;
        color: #5c4f45;
        line-height: 1.8;
      }

      .il-visual-note-card .vn-outline-item .vn-num {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        background: rgba(44, 107, 94, 0.08);
        color: #2c6b5e;
        font-size: 9px;
        font-weight: 600;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }

      /* ════════════════
         CTA Section
         ════════════════ */
      .il-cta {
        padding: 100px 0 80px;
        text-align: center;
        position: relative;
      }

      .il-cta::before {
        content: '';
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 80%;
        max-width: 500px;
        height: 1px;
        background: linear-gradient(90deg, transparent, #d4cdc4, transparent);
      }

      .il-cta h2 {
        font-family: 'Noto Serif SC', serif;
        font-size: clamp(28px, 4vw, 36px);
        font-weight: 700;
        color: #1a1512;
        margin-bottom: 16px;
        text-wrap: balance;
      }

      .il-cta p {
        color: #6b5d53;
        font-size: 16px;
        margin-bottom: 36px;
        margin-left: auto;
        margin-right: auto;
        white-space: nowrap;
      }

      @media (max-width: 480px) {
        .il-cta p { white-space: normal; }
      }

      .il-cta-actions {
        display: flex;
        gap: 16px;
        justify-content: center;
        flex-wrap: wrap;
      }

      /* ════════════════
         Footer
         ════════════════ */
      .il-footer {
        padding: 40px 0 48px;
        border-top: 1px solid #ede8e0;
      }

      .il-footer-inner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
      }

      .il-footer-copy {
        font-size: 13px;
        color: #9a8c80;
        font-weight: 400;
      }

      .il-footer-links {
        display: flex;
        gap: 20px;
      }

      .il-footer-links a {
        font-size: 13px;
        color: #9a8c80;
        text-decoration: none;
        transition: color 0.2s ease;
        font-weight: 500;
      }

      .il-footer-links a:hover {
        color: #2c2420;
      }

      /* ════════════════
         Responsive
         ════════════════ */
      @media (max-width: 900px) {
        .il-feature-row {
          grid-template-columns: 1fr;
          gap: 32px;
          padding: 48px 0;
        }
        .il-feature-row:nth-child(even) .il-feature-visual {
          order: 0;
        }
        .il-feature-desc {
          max-width: none;
        }
        .il-feature-content h3 {
          font-size: 22px;
        }
      }

      @media (max-width: 700px) {
        .il-hero { padding: 64px 0 56px; }
        .il-hero h1 { font-size: 30px; }

        .il-metrics { gap: 28px; flex-wrap: wrap; }
        .il-metric-value { font-size: 22px; }

        .il-features { padding: 48px 0 20px; }
        .il-features-heading { margin-bottom: 40px; }
        .il-features-heading h2 { font-size: 26px; }

        .il-cta { padding: 64px 0 48px; }

        .il-visual-char { font-size: 64px; }
        .il-visual-mini-cards { padding: 16px; gap: 8px; }
        .il-visual-mini-card { padding: 12px 10px; }
      }

      @media (max-width: 480px) {
        .il-container { padding: 0 20px; }

        .il-header { padding: 18px 0; }
        .il-logo-icon { font-size: 22px; }
        .il-logo-text { font-size: 17px; }
        .il-logo-lang { display: none; }

        .il-hero h1 { font-size: 26px; }
        .il-hero-sub { font-size: 15px; }
        .il-hero-actions { flex-direction: column; align-items: stretch; }
        .il-hero-actions .il-btn { text-align: center; }

        .il-metrics { flex-direction: column; gap: 20px; }

        .il-feature-row { padding: 36px 0; }
        .il-feature-content h3 { font-size: 20px; }

        .il-cta-actions { flex-direction: column; align-items: stretch; }
        .il-cta-actions .il-btn { text-align: center; }

        .il-footer-inner { flex-direction: column; text-align: center; }
      }

      /* ── Reduced motion ── */
      @media (prefers-reduced-motion: reduce) {
        html { scroll-behavior: auto; }
        .il-btn { transition: none; }
        .il-btn:hover { transform: none; }
        .il-btn:active { transform: none; }
        .il-nav a { transition: none; }
        .il-footer-links a { transition: none; }
      }
</style>
