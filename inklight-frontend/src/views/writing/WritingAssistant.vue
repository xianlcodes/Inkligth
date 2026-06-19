<template>
  <div class="writing-assistant">
    <div class="section-bar" style="padding: 28px 32px 0 32px; margin-bottom: 0;">
      <div class="section-bar-line"></div>
      <h2 class="section-title">学术写作</h2>
      <span class="section-accent">WRITING</span>
    </div>
    <div class="writing-layout">
      <!-- Left: Skills + History -->
      <aside class="side-panel">
        <!-- Skills Section -->
        <div class="panel-section">
          <h3 class="panel-title">写作技能</h3>
          <p class="panel-desc">勾选技能后，AI 将按对应规则回应你的输入</p>
          <div v-if="availableSkills.length === 0" class="empty-skills">
            <p>暂无可用技能</p>
            <el-button size="small" @click="$router.push('/settings/skills')">去安装</el-button>
          </div>
          <div v-else class="skill-list">
            <el-checkbox-group v-model="selectedSkillNames">
              <label v-for="skill in availableSkills" :key="skill.id" class="skill-item">
                <el-checkbox :value="skill.name" />
                <div class="skill-info">
                  <span class="skill-name">{{ skill.name }}</span>
                  <span class="skill-desc">{{ skill.description }}</span>
                </div>
              </label>
            </el-checkbox-group>
          </div>
          <div v-if="availableSkills.length > 0" class="skill-actions">
            <el-button size="small" @click="toggleAll">
              {{ allSelected ? '全部取消' : '全部启用' }}
            </el-button>
          </div>
        </div>

        <!-- History Section -->
        <div class="panel-section history-section">
          <div class="history-header">
            <h3 class="panel-title">历史对话</h3>
            <el-button v-if="conversationId" text size="small" @click="handleNewConversation">
              <el-icon><Plus /></el-icon>
              新建
            </el-button>
          </div>
          <div v-if="loadingHistory" class="empty-skills">
            <p>加载中...</p>
          </div>
          <div v-else-if="historyList.length === 0" class="empty-skills">
            <p>暂无历史对话</p>
          </div>
          <div v-else class="history-list">
            <div
              v-for="conv in historyList"
              :key="conv.id"
              class="history-item"
              :class="{ active: conv.id === conversationId }"
            >
              <div class="history-item-content" @click="loadConversation(conv.id)">
                <div class="history-item-title">{{ conv.title }}</div>
                <div class="history-item-time">{{ formatRelative(conv.updated_at) }}</div>
              </div>
              <el-button
                text
                size="small"
                type="danger"
                class="history-delete-btn"
                @click.stop="handleDeleteConversation(conv.id)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </aside>

      <!-- Right: Chat Area -->
      <main class="chat-area">
        <!-- Active skills bar -->
        <div class="active-skills-bar">
          <template v-if="selectedSkillNames.length > 0">
            <span class="bar-label">已启用:</span>
            <el-tag v-for="name in selectedSkillNames" :key="name" size="small" type="warning" effect="plain">{{ name }}</el-tag>
          </template>
          <span v-else class="bar-label bar-muted">未启用任何技能 — 通用写作模式</span>
        </div>

        <!-- Messages -->
        <div class="message-list" ref="messageListRef">
          <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
            <div class="msg-label">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
            <div class="msg-bubble" v-html="msg.role === 'assistant' ? renderMarkdown(msg.content) : escapeHtml(msg.content)"></div>
          </div>
          <div v-if="sending" class="message ai">
            <div class="msg-label">AI</div>
            <div class="msg-bubble thinking">
              <el-icon class="is-loading"><Loading /></el-icon>
              思考中...
            </div>
          </div>
          <el-empty v-if="messages.length === 0 && !sending" description="输入内容开始写作" />
        </div>

        <!-- Input Area -->
        <div class="input-area">
          <div v-if="showContextInput" class="context-section">
            <div class="context-header">
              <span>上下文 / 草稿</span>
              <el-button text size="small" @click="showContextInput = false; contextText = ''">清除</el-button>
            </div>
            <el-input v-model="contextText" type="textarea" :rows="4" placeholder="粘贴论文片段、草稿或参考资料..." />
          </div>
          <div class="input-row">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="3"
              placeholder="输入你的论文内容或问题... (Enter 发送, Shift+Enter 换行)"
              @keydown="handleKeydown"
            />
          </div>
          <div class="input-actions">
            <div class="input-actions-left">
              <el-button text size="small" @click="showContextInput = !showContextInput">
                <el-icon><UploadFilled /></el-icon>
                上下文
              </el-button>
              <el-button text size="small" @click="clearConversation">
                <el-icon><Delete /></el-icon>
                清除对话
              </el-button>
            </div>
            <el-button type="primary" :loading="sending" :disabled="!inputText.trim()" @click="sendMessage">
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAiEngineStore } from '@/stores/aiEngine'
import { Loading, UploadFilled, Delete, Promotion, Plus } from '@element-plus/icons-vue'
import { formatRelative } from '@/utils/time'
import { getSkills, type Skill } from '@/api/skills'
import {
  writingChat,
  getConversations,
  getConversationMessages,
  deleteConversation,
  type ConversationSummary,
} from '@/api/writing'

const router = useRouter()

// ── Skills ──
const availableSkills = ref<Skill[]>([])
const selectedSkillNames = ref<string[]>([])

const allSelected = computed(() =>
  availableSkills.value.length > 0 && selectedSkillNames.value.length === availableSkills.value.length
)

async function loadSkills() {
  try {
    const res = await getSkills({ layer: 'agents' })
    availableSkills.value = res.items.filter(s => s.is_active)
  } catch {
    availableSkills.value = []
  }
}

function toggleAll() {
  if (allSelected.value) {
    selectedSkillNames.value = []
  } else {
    selectedSkillNames.value = availableSkills.value.map(s => s.name)
  }
}

// ── Conversation History ──
const historyList = ref<ConversationSummary[]>([])
const loadingHistory = ref(false)

async function loadHistory() {
  loadingHistory.value = true
  try {
    const res = await getConversations('writing')
    historyList.value = res.items
  } catch {
    historyList.value = []
  } finally {
    loadingHistory.value = false
  }
}

async function loadConversation(id: string) {
  try {
    const res = await getConversationMessages(id)
    conversationId.value = res.conversation_id
    messages.value = res.messages.map(m => ({ role: m.role, content: m.content }))
    // 恢复该对话保存的技能选中状态
    if (res.skill_names?.length) {
      selectedSkillNames.value = res.skill_names
    }
  } catch {
    // ignore
  }
}

function handleNewConversation() {
  clearConversation()
}

async function handleDeleteConversation(id: string) {
  try {
    await deleteConversation(id)
    if (conversationId.value === id) {
      clearConversation()
    }
    await loadHistory()
    ElMessage.success('对话已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

// ── Chat ──
const messages = ref<{ role: string; content: string }[]>([])
const inputText = ref('')
const contextText = ref('')
const conversationId = ref('')
const sending = ref(false)
const showContextInput = ref(false)
const messageListRef = ref<HTMLElement | null>(null)

async function sendMessage() {
  const msg = inputText.value.trim()
  if (!msg) return

  const aiEngineStore = useAiEngineStore()
  await aiEngineStore.loadEngines()
  if (!aiEngineStore.defaultEngine) {
    try {
      await ElMessageBox.confirm('请先配置 AI 引擎后再使用学术写作功能，是否前往设置？', '提示', {
        confirmButtonText: '去配置',
        cancelButtonText: '取消',
        type: 'warning',
      })
      router.push('/settings/ai')
    } catch { /* cancelled */ }
    return
  }

  sending.value = true
  messages.value.push({ role: 'user', content: msg })
  inputText.value = ''

  try {
    const data = await writingChat({
      message: msg,
      conversation_id: conversationId.value || undefined,
      skill_names: selectedSkillNames.value,
      context_text: contextText.value,
    })
    messages.value.push({ role: 'assistant', content: data.reply })
    conversationId.value = data.conversation_id
    // 刷新历史列表
    loadHistory()
  } catch {
    messages.value.push({ role: 'assistant', content: '请求失败，请检查网络或 AI 引擎设置后重试。' })
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function clearConversation() {
  messages.value = []
  conversationId.value = ''
  contextText.value = ''
}

function scrollToBottom() {
  setTimeout(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  }, 50)
}

// ── Markdown ──
function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function applyInline(html: string): string {
  return html
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
}

function renderMarkdown(text: string): string {
  let html = escapeHtml(text)

  // 1. Extract fenced code blocks
  const codeBlocks: string[] = []
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_m: string, _lang: string, code: string) => {
    codeBlocks.push(code.replace(/\n$/, ''))
    return `%%CB${codeBlocks.length - 1}%%`
  })

  // 2. Process line by line for block-level elements
  const lines = html.split('\n')
  const out: string[] = []
  let inParagraph = false
  let inList: string | null = null

  function closePara() {
    if (inParagraph) { out.push('</p>'); inParagraph = false }
  }
  function closeList() {
    if (inList) { out.push(`</${inList}>`); inList = null }
  }

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trimEnd()

    // Code block placeholder
    if (/^%%CB\d+%%$/.test(trimmed)) {
      closePara(); closeList()
      const idx = parseInt(trimmed.match(/\d+/)?.[0] || '0', 10)
      out.push(`<pre><code>${codeBlocks[idx]}</code></pre>`)
      continue
    }

    // Headers
    const hMatch = trimmed.match(/^(#{1,4})\s(.+)$/)
    if (hMatch) {
      closePara(); closeList()
      const level = hMatch[1].length + 1
      out.push(`<h${level}>${applyInline(hMatch[2])}</h${level}>`)
      continue
    }

    // Horizontal rule
    if (/^-{3,}$/.test(trimmed)) {
      closePara(); closeList()
      out.push('<hr>')
      continue
    }

    // Blockquote
    if (/^>\s?/.test(trimmed)) {
      closePara(); closeList()
      out.push(`<blockquote>${applyInline(trimmed.replace(/^>\s?/, ''))}</blockquote>`)
      continue
    }

    // Unordered list
    const ulMatch = trimmed.match(/^[-*]\s(.+)$/)
    if (ulMatch) {
      closePara()
      if (inList !== 'ul') { closeList(); inList = 'ul'; out.push('<ul>') }
      out.push(`<li>${applyInline(ulMatch[1])}</li>`)
      continue
    }

    // Ordered list
    const olMatch = trimmed.match(/^\d+\.\s(.+)$/)
    if (olMatch) {
      closePara()
      if (inList !== 'ol') { closeList(); inList = 'ol'; out.push('<ol>') }
      out.push(`<li>${applyInline(olMatch[1])}</li>`)
      continue
    }

    // Empty line = paragraph break
    if (trimmed === '') {
      closePara(); continue
    }

    // Regular paragraph text
    if (!inParagraph) { out.push('<p>'); inParagraph = true }
    else { out.push('<br>') }
    out.push(applyInline(lines[i]))
  }

  closePara(); closeList()
  return out.join('')
}
// ── Lifecycle ──
onMounted(() => {
  loadSkills()
  loadHistory()
  // 从 localStorage 恢复上次技能选中状态（仅用于新对话）
  const saved = localStorage.getItem('writing_skill_names')
  if (saved) {
    try {
      const names = JSON.parse(saved)
      if (Array.isArray(names)) selectedSkillNames.value = names
    } catch { /* ignore */ }
  }
})

// 技能选中状态变化时保存到 localStorage
watch(selectedSkillNames, (val) => {
  localStorage.setItem('writing_skill_names', JSON.stringify(val))
}, { deep: true })
</script>

<style scoped>
/* ── Section Bar ── */
.section-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
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

.writing-assistant {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.writing-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  margin: 0 32px 0;
  border-radius: var(--radius-xl);
  overflow: hidden;
  gap: 0;
}

/* ── Side Panel ── */
.side-panel {
  width: 260px;
  min-width: 260px;
  background: var(--bg-overlay);
  backdrop-filter: blur(8px);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-section {
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.panel-section + .panel-section {
  border-top: 1px solid var(--border-color);
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px;
}

.panel-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin: 0 0 12px;
  line-height: 1.4;
}

.empty-skills {
  text-align: center;
  padding: 24px 0;
  color: var(--text-muted);
  font-size: 12px;
}

.skill-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  max-height: 200px;
  overflow-y: auto;
}

.skill-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.skill-item:hover {
  background: var(--bg-hover);
}

.skill-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.skill-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1.3;
}

.skill-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.skill-actions {
  padding-top: 8px;
  margin-top: 4px;
}

/* ── History ── */
.history-section {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-item {
  display: flex;
  align-items: center;
  padding: 6px 4px 6px 10px;
  border-radius: 6px;
  transition: background 0.15s;
}

.history-item:hover {
  background: var(--bg-hover);
}

.history-item.active {
  background: var(--accent-light);
  border: 1px solid var(--accent-muted);
}

.history-item-content {
  flex: 1;
  min-width: 0;
  cursor: pointer;
  padding: 2px 0;
}

.history-delete-btn {
  flex-shrink: 0;
  opacity: 0;
  margin-left: 4px;
}

.history-item:hover .history-delete-btn,
.history-item.active .history-delete-btn {
  opacity: 1;
}

.history-item-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ── Chat Area ── */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(4px);
}

.active-skills-bar {
  padding: 8px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-height: 38px;
}

.bar-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.bar-muted {
  color: var(--text-muted);
  font-style: italic;
}

/* ── Messages ── */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 10px;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.msg-label {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  color: #fff;
}

.message.ai .msg-label {
  background: linear-gradient(135deg, var(--mint-500, #10b981), #059669);
}

.message.user .msg-label {
  background: linear-gradient(135deg, var(--accent-primary), var(--sky-500));
}

.msg-bubble {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  word-break: break-word;
}

.message.ai .msg-bubble {
  background: var(--bg-overlay-heavy);
  border: 1px solid var(--border-color);
}

.message.user .msg-bubble {
  background: rgba(240,249,255,0.7);
  border: 1px solid rgba(2,132,199,0.15);
  color: var(--text-primary);
}

.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
}

/* ── Input Area ── */
.input-area {
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.context-section {
  background: rgba(255,251,235,0.6);
  border: 1px solid rgba(254,243,199,0.5);
  border-radius: 8px;
  padding: 12px;
}

.context-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #92400e;
  font-weight: 600;
  margin-bottom: 8px;
}

.input-row {
  display: flex;
  gap: 8px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-actions-left {
  display: flex;
  gap: 4px;
}
</style>

<!-- 非 scoped 样式：用于 v-html 渲染的 Markdown 内容 -->
<style>
.writing-assistant .msg-bubble p {
  margin: 8px 0;
  line-height: 1.75;
}
.writing-assistant .msg-bubble > p:first-child {
  margin-top: 0;
}
.writing-assistant .msg-bubble > p:last-child {
  margin-bottom: 0;
}

</style>
