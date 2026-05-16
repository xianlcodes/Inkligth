<template>
  <div class="legal-page">
    <div class="legal-container">
      <h1 class="legal-title">InkLight 研墨 - 用户服务协议</h1>
      <p class="legal-meta">更新日期：2026年5月15日 &nbsp;|&nbsp; 生效日期：2026年5月15日</p>
      <div class="legal-content">
        <p>欢迎使用 InkLight 研墨（以下简称"本平台"）！</p>
        <p>本协议是您（以下简称"用户"）与本平台之间关于使用本平台服务的法律协议。请您仔细阅读并充分理解本协议各条款，特别是以加粗、下划线方式提示您注意的条款。您通过注册页面勾选"我已阅读并同意"即视为您已阅读、理解并接受本协议的全部内容。</p>

        <h2>一、服务说明</h2>
        <p>本平台是一个学术文献管理与阅读辅助工具，提供 PDF 文献上传、在线阅读、AI 翻译、AI 摘要分析、笔记管理、组会汇报大纲生成等功能。用户上传的文献仅供个人学习、研究使用。</p>

        <h2>二、用户账号</h2>
        <p>用户注册时需提供真实、准确的邮箱地址。用户应对其账号下的所有操作负责。账号仅限用户本人使用，不得转借、出租或出售。</p>

        <h2>三、用户上传内容</h2>
        <ol>
          <li>用户保证对其上传到本平台的文献（PDF 文件）拥有合法的使用权，或者其使用行为符合《中华人民共和国著作权法》规定的合理使用情形（如为个人学习、研究、教学目的）。</li>
          <li>用户上传的文献仅供用户本人使用，本平台不会将用户上传的文献公开传播或分享给其他用户，除非用户主动开启团队共享功能。</li>
          <li>用户不得上传含有违法内容、侵犯他人合法权益、或违反公序良俗的文献。</li>
          <li>因用户上传内容引发的任何知识产权纠纷，由用户自行承担全部法律责任。本平台在收到权利人有效通知后，有权删除相关内容。</li>
        </ol>

        <h2>四、AI 服务使用条款</h2>
        <ol>
          <li>本平台的 AI 翻译、AI 摘要、AI 分析等功能依赖用户自行配置的第三方 AI 服务（如 OpenAI、DeepSeek、通义千问等）。用户应自行获取相关 API Key 并遵守该第三方服务的使用条款。</li>
          <li>本平台仅作为 AI 服务的调用工具，不对 AI 生成内容的准确性、完整性、合法性作出任何明示或默示的保证。</li>
          <li>AI 生成内容仅供参考，不应被视为专业翻译、学术判断或法律建议。用户在论文写作、学术发表等场景中使用 AI 生成内容前，应自行核实内容的准确性和适当性。</li>
          <li>用户不得利用本平台的 AI 功能生成违法、侵权、虚假或有害内容。</li>
          <li>用户理解，将文献内容发送给第三方 AI 服务可能存在数据隐私风险。用户应自行评估并承担此类风险，选择符合其隐私要求的 AI 服务提供商。</li>
        </ol>

        <h2>五、知识产权</h2>
        <ol>
          <li>本平台的软件、代码、界面设计、Logo 等知识产权归本平台所有。</li>
          <li>用户上传的文献的知识产权归原权利人所有。</li>
          <li>用户在使用本平台过程中产生的笔记、标注、翻译结果等内容的权利归用户所有。</li>
        </ol>

        <h2>六、免责声明</h2>
        <ol>
          <li>本平台按"现状"提供服务，不保证服务无中断、及时、安全、无误。</li>
          <li>因不可抗力、网络故障、第三方服务故障等原因导致的服务中断或数据丢失，本平台不承担责任。</li>
          <li>用户使用本平台服务产生的任何直接或间接损失，在法律允许的最大范围内，本平台不承担责任。</li>
          <li>本平台不保证 AI 翻译结果的准确性、完整性，用户应自行核对翻译内容。</li>
        </ol>

        <h2>七、隐私保护</h2>
        <p>本平台重视用户隐私保护，具体隐私政策详见《隐私政策》。用户使用本平台即表示同意本平台按照《隐私政策》收集、使用、存储其个人信息。</p>

        <h2>八、协议修改</h2>
        <p>本平台有权根据法律法规变化或业务需要修改本协议。修改后的协议将在平台上公布，用户继续使用本平台服务即视为同意修改后的协议。</p>

        <p>如您对本协议有任何疑问，请联系：872948566@qq.com</p>
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