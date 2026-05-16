<template>
  <div class="legal-page">
    <div class="legal-container">
      <h1 class="legal-title">InkLight 研墨 - 隐私政策</h1>
      <p class="legal-meta">更新日期：2026年5月15日 &nbsp;|&nbsp; 生效日期：2026年5月15日</p>
      <div class="legal-content">
        <p>本隐私政策说明了 InkLight 研墨（以下简称"本平台"）如何收集、使用、存储和保护用户的个人信息。请您仔细阅读本隐私政策。</p>

        <h2>一、我们收集哪些信息</h2>
        <ol>
          <li>注册信息：当您注册账号时，我们收集您的邮箱地址。</li>
          <li>上传内容：您上传的 PDF 文献文件及其内容文本。</li>
          <li>使用记录：您的阅读记录、笔记、高亮标注、翻译历史、AI 分析结果。</li>
          <li>AI 引擎配置：您自行填写的第三方 API Key（加密存储）。</li>
          <li>设备信息：IP 地址、浏览器类型、访问时间等日志信息。</li>
        </ol>

        <h2>二、我们如何使用信息</h2>
        <ol>
          <li>提供核心服务：文献管理、在线阅读、AI 翻译、AI 分析、组会汇报大纲生成等功能。</li>
          <li>改善服务质量：分析用户使用习惯，优化产品体验。</li>
          <li>安全与合规：防止恶意注册、滥用服务，履行法律法规要求的义务。</li>
        </ol>

        <h2>三、信息的存储与保护</h2>
        <ol>
          <li>用户数据存储在位于中华人民共和国的服务器上。</li>
          <li>用户密码采用 bcrypt 加密存储，API Key 采用 Fernet 对称加密存储。</li>
          <li>我们采取合理的技术措施保护用户数据安全，防止未经授权的访问、泄露或篡改。</li>
        </ol>

        <h2>四、信息的共享与披露</h2>
        <ol>
          <li>我们不会将用户上传的文献内容出售或分享给第三方。</li>
          <li>用户使用 AI 翻译/分析功能时，文献内容会发送给用户自行配置的第三方 AI 服务商。我们建议用户选择信誉良好的服务商，并阅读其隐私政策。</li>
          <li>在法律要求或政府机关依法要求时，我们可能会披露用户信息。</li>
        </ol>

        <h2>五、用户权利</h2>
        <ol>
          <li>用户可随时查看、修改自己的账号信息和 AI 引擎配置。</li>
          <li>用户可随时删除自己上传的文献及相关笔记、标注。</li>
          <li>用户可注销账号，账号注销后相关数据将被永久删除。</li>
        </ol>

        <h2>六、Cookie 使用</h2>
        <p>本平台可能使用必要的 Cookie 来维持用户登录状态，不用于广告追踪。</p>

        <h2>七、政策更新</h2>
        <p>我们可能会更新本隐私政策，更新后的政策将在平台上公布。</p>

        <p>如您对本隐私政策有任何疑问，请联系：xianlcodes@gmail.com</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.legal-page {
  min-height: 100vh;
  background: var(--bg-secondary, #f5f7fa);
  padding: 40px 20px;
  box-sizing: border-box;
}

.legal-container {
  max-width: 800px;
  margin: 0 auto;
  background: #fff;
  border-radius: 12px;
  padding: 40px 48px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.legal-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #1a1a2e);
  margin: 0 0 8px;
  text-align: center;
}

.legal-meta {
  font-size: 13px;
  color: var(--text-tertiary, #999);
  text-align: center;
  margin: 0 0 32px;
}

.legal-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary, #555);
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

.legal-content h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #1a1a2e);
  margin: 24px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-color, #eee);
}

.legal-content ol {
  padding-left: 20px;
  margin: 8px 0;
}

.legal-content li {
  margin-bottom: 6px;
}

.legal-content p {
  margin: 8px 0;
}
</style>