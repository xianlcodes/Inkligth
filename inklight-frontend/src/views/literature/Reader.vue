<template>
  <div class="reader-container">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <span class="toolbar-title">{{ literature?.title || '加载中...' }}</span>
        <div class="toolbar-tags">
          <el-tag
            v-for="tag in literatureTags"
            :key="tag.id"
            closable
            size="small"
            effect="plain"
            class="lit-tag"
            @close="handleRemoveTag(tag.id)"
          >
            {{ tag.name }}
          </el-tag>
          <el-popover
            :visible="tagPopoverVisible"
            placement="bottom-start"
            :width="200"
            trigger="click"
          >
            <template #reference>
              <el-button
                size="small"
                text
                class="add-tag-btn"
                @click="tagPopoverVisible = !tagPopoverVisible"
              >
                <el-icon><Plus /></el-icon>
              </el-button>
            </template>
            <div class="tag-popover-content">
              <el-input
                v-model="newTagName"
                placeholder="输入标签名"
                size="small"
                @keyup.enter="handleAddTag"
              >
                <template #append>
                  <el-button :loading="tagAdding" @click="handleAddTag">添加</el-button>
                </template>
              </el-input>
            </div>
          </el-popover>
        </div>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="fullTranslating" @click="handleFullTranslate">
          <el-icon><Document /></el-icon>
          全文翻译
        </el-button>
        <span v-if="backgroundTranslatingId" class="toolbar-translating-hint">
          <el-icon class="is-loading"><Loading /></el-icon>
          翻译中 {{ translateProgress }}%
        </span>
        <el-button :loading="parsing" @click="handleAIParse">
          <el-icon><MagicStick /></el-icon>
          AI 解析
        </el-button>
        <el-button :loading="outlineGenerating" @click="handleGenerateOutline">
          <el-icon><DataAnalysis /></el-icon>
          生成汇报大纲
        </el-button>
      </div>
    </div>

    <!-- 全文翻译进度对话框 -->
    <el-dialog
      v-model="progressDialogVisible"
      title="全文翻译进度"
      width="420px"
      :close-on-click-modal="false"
      @close="onProgressDialogClose"
    >
      <div class="progress-content">
        <el-progress
          :percentage="translateProgress"
          :status="translateProgressStatus"
          :stroke-width="16"
          :text-inside="true"
        />
        <p class="progress-text">
          {{ translateProgressText }}
        </p>
      </div>
      <template #footer>
        <el-button v-if="translateProgressStatus === 'success'" type="primary" @click="onTranslateComplete">
          查看译文
        </el-button>
        <el-button v-else-if="translateProgressStatus === 'exception'" @click="progressDialogVisible = false">
          关闭
        </el-button>
        <el-button v-else @click="onProgressDialogClose">
          后台翻译
        </el-button>
        <el-button
          v-if="translateProgressStatus !== 'success' && translateProgressStatus !== 'exception'"
          type="danger"
          :loading="cancelling"
          @click="handleStopTranslation"
        >
          停止翻译
        </el-button>
      </template>
    </el-dialog>

    <!-- 笔记编辑对话框 -->
    <el-dialog
      v-model="noteEditorVisible"
      title="记笔记"
      width="480px"
      :close-on-click-modal="false"
    >
      <div class="note-editor-body">
        <p v-if="floatingMenu.quotedText" class="note-editor-quote">"{{ floatingMenu.quotedText }}"</p>
        <div class="note-editor-field">
          <label class="note-editor-label">笔记类型</label>
          <el-select v-model="noteEditorType" style="width: 100%">
            <el-option label="通用" value="general" />
            <el-option label="创新点" value="innovation" />
            <el-option label="方法" value="method" />
            <el-option label="问题" value="question" />
          </el-select>
        </div>
        <div class="note-editor-field">
          <label class="note-editor-label">笔记内容</label>
          <el-input
            v-model="noteEditorContent"
            type="textarea"
            :rows="6"
            placeholder="输入笔记内容（支持 Markdown）..."
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="noteEditorVisible = false">取消</el-button>
        <el-button type="primary" :loading="noteSaving" @click="saveNoteWithHighlight">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- AI 分析进度对话框 -->
    <el-dialog
      v-model="analysisDialogVisible"
      :title="analysisData ? 'AI 解析结果' : 'AI 解析进度'"
      width="640px"
      :close-on-click-modal="false"
      :close-on-press-escape="!analyzing"
      :show-close="!analyzing"
    >
      <template v-if="analyzing">
        <div class="progress-content">
          <el-progress
            :percentage="analysisProgress"
            :status="analysisProgressStatus"
            :stroke-width="16"
            :text-inside="true"
          />
          <p class="progress-text">{{ analysisProgressText }}</p>
        </div>
      </template>
      <template v-else-if="analysisData">
        <div class="analysis-result">
          <!-- 结构化摘要 -->
          <div v-if="analysisData.summary" class="analysis-section">
            <h4 class="analysis-section-title">
              <el-icon><Document /></el-icon>
              结构化摘要
            </h4>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="summary-label">背景</span>
                <p class="summary-text">{{ analysisData.summary.background || '暂无' }}</p>
              </div>
              <div class="summary-item">
                <span class="summary-label">方法</span>
                <p class="summary-text">{{ analysisData.summary.method || '暂无' }}</p>
              </div>
              <div class="summary-item">
                <span class="summary-label">结果</span>
                <p class="summary-text">{{ analysisData.summary.result || '暂无' }}</p>
              </div>
              <div class="summary-item">
                <span class="summary-label">结论</span>
                <p class="summary-text">{{ analysisData.summary.conclusion || '暂无' }}</p>
              </div>
            </div>
          </div>

          <!-- 创新点 -->
          <div v-if="analysisData.innovations && analysisData.innovations.length > 0" class="analysis-section">
            <h4 class="analysis-section-title">
              <el-icon><Star /></el-icon>
              创新点
            </h4>
            <div class="innovation-list">
              <div
                v-for="(item, idx) in analysisData.innovations"
                :key="idx"
                class="innovation-item"
              >
                <span class="innovation-index">{{ idx + 1 }}</span>
                <p class="innovation-text">{{ item }}</p>
                <el-button
                  size="small"
                  type="primary"
                  plain
                  :loading="innovationAddingIdx === idx"
                  @click="addInnovationAsNote(item, idx)"
                >
                  加入笔记
                </el-button>
              </div>
            </div>
          </div>

          <!-- 方法步骤 -->
          <div v-if="analysisData.methods" class="analysis-section">
            <h4 class="analysis-section-title">
              <el-icon><Setting /></el-icon>
              可复现方法步骤
            </h4>
            <div class="methods-content">{{ analysisData.methods }}</div>
          </div>
        </div>
      </template>
      <template v-else>
        <el-empty description="暂无分析结果" :image-size="80" />
      </template>
      <template #footer>
        <el-button v-if="!analyzing" @click="analysisDialogVisible = false">关闭</el-button>
        <el-button v-if="!analyzing && analysisData" type="primary" @click="reAnalyze">
          重新分析
        </el-button>
      </template>
    </el-dialog>

    <!-- PPT 大纲预览对话框 -->
    <el-dialog
      v-model="outlineDialogVisible"
      title="汇报 PPT 大纲"
      width="720px"
      :close-on-click-modal="false"
      :close-on-press-escape="!outlineGenerating"
      :show-close="!outlineGenerating"
    >
      <template v-if="outlineGenerating">
        <div class="outline-progress">
          <el-icon class="outline-progress-icon is-loading" :size="40">
            <Loading />
          </el-icon>
          <p class="outline-progress-text">AI 正在生成汇报大纲...</p>
          <p class="outline-progress-sub">正在分析文献结构，请稍候</p>
        </div>
      </template>
      <template v-else-if="outlineData && outlineData.slides && outlineData.slides.length > 0">
        <div class="outline-container">
          <el-collapse v-model="outlineActiveSlides" accordion>
            <el-collapse-item
              v-for="(slide, idx) in outlineData.slides"
              :key="idx"
              :name="idx"
            >
              <template #title>
                <div class="slide-title-header">
                  <span class="slide-num">{{ idx + 1 }}</span>
                  <span class="slide-title-text">{{ slide.title }}</span>
                </div>
              </template>
              <ul class="slide-bullets">
                <li v-for="(bullet, bi) in slide.bullets" :key="bi">{{ bullet }}</li>
              </ul>
              <p v-if="slide.notes" class="slide-notes">
                <el-icon><ChatLineSquare /></el-icon>
                {{ slide.notes }}
              </p>
            </el-collapse-item>
          </el-collapse>
        </div>
      </template>
      <el-empty v-else description="暂无大纲数据" :image-size="80" />
      <template #footer>
        <el-button :disabled="outlineGenerating" @click="outlineDialogVisible = false">关闭</el-button>
        <div v-if="outlineGenerated" class="outline-synced-hint">
          <el-icon><CircleCheck /></el-icon>
          <span>已同步到组会</span>
          <el-button type="primary" text @click="goToPreMeeting">
            在组会看板中查看/下载
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </template>
    </el-dialog>

    <div class="reader-body">
      <!-- PDF 面板 -->
      <div class="pdf-panel" :style="{ width: pdfPanelWidth + 'px' }">
        <div class="pdf-toolbar">
          <el-button-group>
            <el-button size="small" :disabled="scale <= 0.5" @click="scale -= 0.25">
              <el-icon><ZoomOut /></el-icon>
            </el-button>
            <el-button size="small" disabled>
              {{ Math.round(scale * 100) }}%
            </el-button>
            <el-button size="small" :disabled="scale >= 3" @click="scale += 0.25">
              <el-icon><ZoomIn /></el-icon>
            </el-button>
          </el-button-group>
          <el-button size="small" @click="fitToWidth">
            适应宽度
          </el-button>
          <el-divider direction="vertical" />
          <el-switch
            v-model="paragraphMode"
            active-text="逐段模式"
            size="small"
          />
          <el-divider direction="vertical" />
          <el-switch
            v-model="continuousMode"
            active-text="连续翻译"
            size="small"
          />
        </div>
        <div
          ref="pdfViewerRef"
          class="pdf-viewer"
          v-loading="pdfLoading"
          @wheel="handleWheel"
          @mouseup="handleTextSelection"
          @click="handlePdfClick"
          @mousemove="handlePdfMouseMove"
        >
          <VuePdfEmbed
            v-if="pdfBlobUrl"
            :source="pdfBlobUrl"
            :scale="scale"
            :text-layer="true"
            @loaded="onPdfLoaded"
            @loading-failed="onPdfError"
          />

          <!-- 浮动菜单（文本选中） -->
          <Teleport to="body">
            <div
              v-if="floatingMenu.visible"
              class="floating-menu"
              :style="{ left: floatingMenu.x + 'px', top: floatingMenu.y + 'px' }"
              @click.stop
            >
              <button class="floating-menu-btn highlight-btn" @click="createHighlight">
                <el-icon><EditPen /></el-icon>
                高亮
              </button>
              <button class="floating-menu-btn note-btn" @click="openNoteEditor">
                <el-icon><Notebook /></el-icon>
                记笔记
              </button>
              <button class="floating-menu-btn translate-btn" @click="translateSelection">
                <el-icon><Document /></el-icon>
                翻译
              </button>
            </div>
          </Teleport>

          <!-- 高亮操作菜单 -->
          <Teleport to="body">
            <div
              v-if="highlightMenu.visible"
              class="floating-menu highlight-action-menu"
              :style="{ left: highlightMenu.x + 'px', top: highlightMenu.y + 'px' }"
              @click.stop
            >
              <button class="floating-menu-btn note-btn" @click="handleEditHighlightNote">
                <el-icon><Notebook /></el-icon>
                编辑笔记
              </button>
              <button class="floating-menu-btn highlight-btn" @click="handleDeleteHighlight">
                <el-icon><Delete /></el-icon>
                删除高亮
              </button>
            </div>
          </Teleport>
        </div>
      </div>

      <!-- 可拖拽分隔条 -->
      <div class="resizer" @mousedown="startResize">
        <div class="resizer-line"></div>
      </div>

      <!-- 侧边栏：翻译 + 笔记 -->
      <div class="side-panel" :style="{ width: sidePanelWidth + 'px' }">
        <div class="side-panel-header">
          <div class="side-panel-title">
            <el-icon :size="18"><Document /></el-icon>
            <span>{{ activeTab === 'translate' ? '智能翻译' : '我的笔记' }}</span>
          </div>
        </div>
        <el-tabs v-model="activeTab" class="side-tabs">
          <!-- 翻译 Tab -->
          <el-tab-pane label="翻译" name="translate">
            <div class="tab-content">
              <!-- 全文翻译视图 -->
              <div v-if="fullTranslationParagraphs.length > 0" class="full-translation-panel">
                <el-alert
                  v-if="translationAgeInfo?.isExpired"
                  title="译文已过期"
                  type="warning"
                  :closable="false"
                  show-icon
                  class="translation-expiry-warning"
                >
                  <template #default>
                    该译文生成于 {{ translationAgeInfo.ageDays }} 天前，已超过 {{ TRANSLATION_TTL_DAYS }} 天保留期限，建议重新翻译以获取最新结果。
                  </template>
                </el-alert>
                <el-alert
                  v-else-if="translationAgeInfo?.isNearExpiry"
                  :title="`译文即将过期（剩余 ${translationAgeInfo.remainingDays} 天）`"
                  type="info"
                  :closable="false"
                  show-icon
                  class="translation-expiry-warning"
                />
                <div class="full-trans-header">
                  <span class="full-trans-title">全文译文</span>
                  <div class="full-trans-actions">
                    <el-button text size="small" type="primary" @click="handleRetryFullTranslate">
                      <el-icon><Refresh /></el-icon>
                      重新翻译
                    </el-button>
                    <el-button text size="small" type="danger" @click="handleDeleteFullTranslation">
                      <el-icon><Delete /></el-icon>
                      删除翻译结果
                    </el-button>
                    <el-button text size="small" type="primary" @click="clearFullTranslation">
                      返回逐段翻译
                    </el-button>
                  </div>
                </div>
                <div class="full-trans-list">
                  <div
                    v-for="(para, idx) in fullTranslationParagraphs"
                    :key="idx"
                    class="full-trans-item"
                    :class="{ 'has-translation': para.translated, 'is-active': activeParagraphIndex === idx }"
                    @click="scrollToParagraph(idx)"
                  >
                    <div class="full-trans-index">{{ idx + 1 }}</div>
                    <div class="full-trans-content">
                      <p v-if="para.translated" class="full-trans-text">{{ para.translated }}</p>
                      <p v-else class="full-trans-empty">（空段落）</p>
                      <p class="full-trans-original">{{ para.original }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 逐段翻译视图 -->
              <template v-else>
                <div v-if="translationHistory.length === 0 && !translating" class="empty-hint">
                  <el-empty description="在左侧 PDF 中选中文本即可翻译，或点击「全文翻译」一键翻译全文" :image-size="80" />
                </div>
                <div v-else class="translation-panel">
                  <div class="trans-block">
                    <div class="block-label-row">
                      <p class="block-label trans-label">译文</p>
                      <el-button v-if="translationHistory.length > 0" text size="small" @click="copyTranslation">
                        <el-icon><CopyDocument /></el-icon>
                      </el-button>
                    </div>
                    <div v-if="translating" class="block-text translating">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      翻译中...
                    </div>
                    <div v-if="translating && streamingTarget" class="block-text streaming-preview">
                      {{ streamingTarget }}
                    </div>
                    <div v-if="!translating" class="trans-scroll">
                      <div
                        v-for="(item, idx) in translationHistory"
                        :key="idx"
                        class="trans-history-item"
                      >
                        <p class="block-text trans-text">{{ item.target }}</p>
                        <el-divider v-if="idx < translationHistory.length - 1" />
                      </div>
                    </div>
                  </div>
                  <div class="source-block">
                    <p class="block-label">原文</p>
                    <div class="source-scroll">
                      <div
                        v-for="(item, idx) in translationHistory"
                        :key="idx"
                        class="source-history-item"
                      >
                        <p class="block-text source-text">{{ item.source }}</p>
                        <el-divider v-if="idx < translationHistory.length - 1" />
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </el-tab-pane>

          <!-- 笔记 Tab -->
          <el-tab-pane label="笔记" name="notes">
            <div class="tab-content">
              <div class="notes-panel">
                <div class="notes-filter">
                  <el-radio-group v-model="noteFilter" size="small" @change="loadNotes">
                    <el-radio-button value="">全部</el-radio-button>
                    <el-radio-button value="general">通用</el-radio-button>
                    <el-radio-button value="innovation">创新点</el-radio-button>
                    <el-radio-button value="method">方法</el-radio-button>
                    <el-radio-button value="question">问题</el-radio-button>
                  </el-radio-group>
                </div>
                <div v-loading="notesLoading" class="notes-list">
                  <el-empty v-if="!notesLoading && notes.length === 0" description="暂无笔记，选中 PDF 文本后点击「记笔记」" :image-size="60" />
                  <div
                    v-for="note in notes"
                    :key="note.id"
                    class="note-card"
                    :class="{ 'note-card--active': activeNoteId === note.id }"
                    @click="focusNote(note)"
                  >
                    <div class="note-card-header">
                      <el-tag :type="noteTypeTag(note.note_type)" size="small" effect="plain">
                        {{ noteTypeLabel(note.note_type) }}
                      </el-tag>
                      <span class="note-card-page">第 {{ note.page_number }} 页</span>
                      <el-button text size="small" type="danger" @click.stop="deleteNoteById(note.id)">
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </div>
                    <p v-if="note.quoted_text" class="note-card-quote">"{{ note.quoted_text }}"</p>
                    <p v-if="note.content" class="note-card-content">{{ note.content }}</p>
                    <p v-else class="note-card-content note-card-content--empty">（仅高亮，无笔记内容）</p>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ZoomIn, ZoomOut, Document, MagicStick, CopyDocument, Loading, EditPen, Notebook, Delete, Star, Setting, DataAnalysis, ChatLineSquare, Plus, CircleCheck, ArrowRight, Refresh } from '@element-plus/icons-vue'
import VuePdfEmbed from 'vue-pdf-embed'
import 'vue-pdf-embed/dist/styles/textLayer.css'
import { getLiterature, getLiteratureFileBlob, type Literature } from '@/api/literature'
import { translateText, translateTextStream, startFullTranslate, getTaskStatus, deleteFullTranslation, cancelTask, type TranslatedParagraph } from '@/api/translate'
import { createNote, getNotes, deleteNote, type Note, type RectCoords } from '@/api/note'
import { startAnalyze, getAnalysis, type AnalysisData } from '@/api/analysis'
import { generateOutline, type OutlineData } from '@/api/outline'
import { getLiteratureTags, addTagToLiterature, removeTagFromLiterature, type TagItem } from '@/api/tag'
import { recordReading } from '@/api/stats'

const route = useRoute()
const router = useRouter()

const literature = ref<Literature | null>(null)
const pdfBlobUrl = ref('')
const pdfLoading = ref(true)
const scale = ref(1)
const activeTab = ref('translate')
const translating = ref(false)
const streamingTarget = ref('')
const parsing = ref(false)
const continuousMode = ref(false)
const translationHistory = ref<{ source: string; target: string }[]>([])

watch(continuousMode, (newVal) => {
  if (!newVal) {
    translationHistory.value = []
  }
})
const paragraphMode = ref(false)
const pdfViewerRef = ref<HTMLElement | null>(null)

const resizerWidth = 6
const sidePanelWidth = ref(0)
const pdfPanelWidth = ref(0)

let pdfPageWidth = 0
const totalPages = ref(0)

const fullTranslating = ref(false)
const progressDialogVisible = ref(false)
const translateProgress = ref(0)
const translateProgressStatus = ref<'success' | 'exception' | 'warning' | ''>('')
const translateProgressText = ref('')
const fullTranslationParagraphs = ref<TranslatedParagraph[]>([])
const activeParagraphIndex = ref(-1)
let pollingTimer: ReturnType<typeof setInterval> | null = null
let cancelling = false
let currentTaskId = ''
const backgroundTranslatingId = ref('')

const TRANSLATION_TTL_DAYS = 7

const translationAgeInfo = computed(() => {
  if (!literature.value?.translated_at || !literature.value?.translated_text) return null
  const translatedAt = new Date(literature.value.translated_at)
  const now = new Date()
  const ageDays = (now.getTime() - translatedAt.getTime()) / (1000 * 60 * 60 * 24)
  const remainingDays = TRANSLATION_TTL_DAYS - ageDays
  return {
    ageDays: Math.round(ageDays * 10) / 10,
    remainingDays: Math.round(remainingDays * 10) / 10,
    isExpired: remainingDays <= 0,
    isNearExpiry: remainingDays > 0 && remainingDays <= 1,
  }
})

const floatingMenu = ref<{
  visible: boolean
  x: number
  y: number
  quotedText: string
  pageNumber: string
  rectCoords: RectCoords | null
}>({
  visible: false,
  x: 0,
  y: 0,
  quotedText: '',
  pageNumber: '1',
  rectCoords: null,
})

const highlightMenu = ref<{
  visible: boolean
  x: number
  y: number
  noteId: string
}>({
  visible: false,
  x: 0,
  y: 0,
  noteId: '',
})

const notes = ref<Note[]>([])
const notesLoading = ref(false)
const noteFilter = ref('')
const activeNoteId = ref<string | null>(null)

const noteEditorVisible = ref(false)
const noteEditorType = ref('general')
const noteEditorContent = ref('')
const noteSaving = ref(false)

const highlights = ref<Note[]>([])

const analyzing = ref(false)
const analysisDialogVisible = ref(false)
const analysisData = ref<AnalysisData | null>(null)
const analysisProgress = ref(0)
const analysisProgressStatus = ref<'success' | 'exception' | 'warning' | ''>('')
const analysisProgressText = ref('')
let analysisPollingTimer: ReturnType<typeof setInterval> | null = null
const innovationAddingIdx = ref(-1)

const outlineGenerating = ref(false)
const outlineDialogVisible = ref(false)
const outlineData = ref<OutlineData | null>(null)
const outlineActiveSlides = ref<number[]>([])
const outlineGenerated = ref(false)

const searchChunkIndex = ref(-1)

const literatureTags = ref<TagItem[]>([])
const tagPopoverVisible = ref(false)
const newTagName = ref('')
const tagAdding = ref(false)

let readingStartTime = 0
let readingTimer: ReturnType<typeof setInterval> | null = null
let lastRecordedPage = 0
const currentPage = ref(1)
let resizeObserver: ResizeObserver | null = null
let resizeDebounceTimer: ReturnType<typeof setTimeout> | null = null

function updateWidths() {
  const readerBody = document.querySelector('.reader-body') as HTMLElement | null
  const available = readerBody ? readerBody.clientWidth : window.innerWidth - 240 - resizerWidth
  if (available <= 0) return

  if (!sidePanelWidth.value || sidePanelWidth.value <= 0) {
    sidePanelWidth.value = Math.round(available * 0.40)
  }

  let side = sidePanelWidth.value

  const maxSide = available - resizerWidth - 10
  if (side > maxSide) side = maxSide
  if (side < 200) side = 200

  if (available - side < 150) {
    side = available - 150
    if (side < 200) side = 200
  }

  sidePanelWidth.value = side
  pdfPanelWidth.value = available - side
}

onMounted(() => {
  updateWidths()
  loadLiterature()
  window.addEventListener('resize', onWindowResize)
  document.addEventListener('click', onDocumentClick)
  handleSearchNavigation()
  startReadingTracking()

  const readerBody = document.querySelector('.reader-body') as HTMLElement | null
  if (readerBody) {
    resizeObserver = new ResizeObserver(() => {
      updateWidths()
      if (resizeDebounceTimer) clearTimeout(resizeDebounceTimer)
      resizeDebounceTimer = setTimeout(() => {
        fitToWidth()
      }, 350)
    })
    resizeObserver.observe(readerBody)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', onWindowResize)
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', stopResize)
  document.removeEventListener('click', onDocumentClick)
  stopPolling()
  stopAnalysisPolling()
  stopReadingTracking()
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (resizeDebounceTimer) {
    clearTimeout(resizeDebounceTimer)
    resizeDebounceTimer = null
  }
})

function onDocumentClick() {
  floatingMenu.value.visible = false
  highlightMenu.value.visible = false
}

function detectCurrentPage(): number {
  const pageEls = document.querySelectorAll('[data-page-number]')
  let bestPage = 1
  let bestVisibility = 0
  const container = document.querySelector('.reader-body') as HTMLElement | null
  if (!container) return bestPage

  const containerRect = container.getBoundingClientRect()
  const containerCenter = containerRect.top + containerRect.height * 0.3

  pageEls.forEach((el) => {
    const rect = el.getBoundingClientRect()
    const visibleTop = Math.max(rect.top, containerRect.top)
    const visibleBottom = Math.min(rect.bottom, containerRect.bottom)
    const visibleHeight = Math.max(0, visibleBottom - visibleTop)
    const distanceToCenter = Math.abs(rect.top - containerCenter)

    if (visibleHeight > bestVisibility || (visibleHeight === bestVisibility && distanceToCenter < Math.abs(bestPage * 1000))) {
      bestVisibility = visibleHeight
      const pageNum = parseInt(el.getAttribute('data-page-number') || '1', 10)
      if (!isNaN(pageNum)) bestPage = pageNum
    }
  })

  return bestPage
}

function startReadingTracking() {
  readingStartTime = Date.now()
  readingTimer = setInterval(() => {
    const page = detectCurrentPage()
    currentPage.value = page
    if (page !== lastRecordedPage) {
      const elapsed = Math.round((Date.now() - readingStartTime) / 1000)
      sendReadingRecord(page, elapsed)
      lastRecordedPage = page
      readingStartTime = Date.now()
    }
  }, 30000)
}

function stopReadingTracking() {
  if (readingTimer) {
    clearInterval(readingTimer)
    readingTimer = null
  }
  const page = detectCurrentPage()
  if (page > 0) {
    const elapsed = Math.round((Date.now() - readingStartTime) / 1000)
    sendReadingRecord(page, elapsed)
  }
}

async function sendReadingRecord(page: number, duration: number) {
  if (!literature.value) return
  try {
    await recordReading(literature.value.id, page, Math.max(duration, 0))
  } catch {
    // silently fail
  }
}

function handleSearchNavigation() {
  const page = route.query.page
  const chunk = route.query.chunk
  if (page) {
    const pageNum = parseInt(page as string, 10)
    if (!isNaN(pageNum) && pageNum > 0) {
      currentPage.value = pageNum
      nextTick(() => {
        scrollToPage(pageNum)
      })
    }
  }
  if (chunk) {
    searchChunkIndex.value = parseInt(chunk as string, 10)
    nextTick(() => {
      setTimeout(() => highlightSearchChunk(), 800)
    })
  }
}

function scrollToPage(pageNum: number) {
  const pageEl = document.querySelector(`[data-page-number="${pageNum}"]`)
  if (pageEl) {
    pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function highlightSearchChunk() {
  if (searchChunkIndex.value < 0) return
  const textLayerEls = document.querySelectorAll('.textLayer')
  textLayerEls.forEach((el) => {
    const spans = el.querySelectorAll('span')
    const chunkStart = searchChunkIndex.value * 10
    const chunkEnd = chunkStart + 10
    spans.forEach((span, i) => {
      if (i >= chunkStart && i < chunkEnd) {
        ;(span as HTMLElement).style.backgroundColor = 'rgba(13, 148, 136, 0.15)'
        ;(span as HTMLElement).style.borderRadius = '2px'
      }
    })
  })
}

watch(scale, () => {
  nextTick(() => renderHighlights())
})

function onWindowResize() {
  updateWidths()
  if (resizeDebounceTimer) clearTimeout(resizeDebounceTimer)
  resizeDebounceTimer = setTimeout(() => {
    fitToWidth()
  }, 350)
}

async function loadLiterature() {
  const id = route.params.id as string
  if (!id) {
    ElMessage.error('文献 ID 无效')
    goBack()
    return
  }
  try {
    const lit = await getLiterature(id)
    literature.value = lit.data
    const resp = await getLiteratureFileBlob(id)
    pdfBlobUrl.value = URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }))

    if (literature.value.translated_text) {
      try {
        fullTranslationParagraphs.value = JSON.parse(literature.value.translated_text)
      } catch {
        fullTranslationParagraphs.value = []
      }
    }

    await loadNotes()
    await loadLiteratureTags()
    await nextTick()
    renderHighlights()
  } catch {
    ElMessage.error('加载文献失败')
    goBack()
  }
}

function onPdfLoaded(doc: { numPages: number; getPage: (n: number) => Promise<{ getViewport: (opts: { scale: number }) => { width: number } }> }) {
  pdfLoading.value = false
  totalPages.value = doc.numPages
  doc.getPage(1).then((page) => {
    const viewport = page.getViewport({ scale: 1 })
    pdfPageWidth = viewport.width
    fitToWidth()
    nextTick(() => renderHighlights())
  })
}

function fitToWidth() {
  if (pdfPageWidth === 0) return
  const availableWidth = pdfPanelWidth.value - 48
  if (availableWidth <= 0) return
  scale.value = Math.max(0.1, availableWidth / pdfPageWidth)
}

function onPdfError() {
  pdfLoading.value = false
  ElMessage.error('PDF 加载失败')
}

function goBack() {
  router.push('/literature')
}

function handleWheel(e: WheelEvent) {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    scale.value = Math.max(0.5, Math.min(3, scale.value + delta))
  }
}

function handleTextSelection() {
  setTimeout(() => {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed || !selection.rangeCount) {
      floatingMenu.value.visible = false
      return
    }
    const text = selection.toString().trim()
    if (!text) {
      floatingMenu.value.visible = false
      return
    }

    const range = selection.getRangeAt(0)
    const rect = range.getBoundingClientRect()

    const pdfViewer = pdfViewerRef.value
    if (!pdfViewer) return

    const pageElement = (range.startContainer as Node).parentElement?.closest('.vue-pdf-embed__page') as HTMLElement | null
    const pageNumber = pageElement ? getPageNumber(pageElement) : '1'

    let rectCoords: RectCoords | null = null
    if (pageElement) {
      const pageRect = pageElement.getBoundingClientRect()
      rectCoords = {
        x: (rect.left - pageRect.left) / pageRect.width,
        y: (rect.top - pageRect.top) / pageRect.height,
        width: rect.width / pageRect.width,
        height: rect.height / pageRect.height,
      }
    }

    floatingMenu.value = {
      visible: true,
      x: rect.left + rect.width / 2,
      y: rect.top - 12,
      quotedText: text,
      pageNumber,
      rectCoords,
    }
  }, 100)
}

function getPageNumber(pageElement: HTMLElement): string {
  const pages = pdfViewerRef.value?.querySelectorAll('.vue-pdf-embed__page')
  if (!pages) return '1'
  for (let i = 0; i < pages.length; i++) {
    if (pages[i] === pageElement) return String(i + 1)
  }
  return '1'
}

async function createHighlight() {
  if (!literature.value || !floatingMenu.value.rectCoords) return

  try {
    const resp = await createNote({
      literature_id: literature.value.id,
      page_number: floatingMenu.value.pageNumber,
      rect_coords: floatingMenu.value.rectCoords,
      quoted_text: floatingMenu.value.quotedText,
      note_type: 'general',
    })
    floatingMenu.value.visible = false
    ElMessage.success('高亮已保存')
    await loadNotes()
    await nextTick()
    renderHighlights()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '保存高亮失败'
    ElMessage.error(detail)
  }
}

function openNoteEditor() {
  noteEditorType.value = 'general'
  noteEditorContent.value = ''
  noteEditorVisible.value = true
}

function translateSelection() {
  const rawText = floatingMenu.value.quotedText
  floatingMenu.value.visible = false
  if (rawText) {
    const mergedText = rawText
      .replace(/[\r\n]+/g, ' ')
      .replace(/\s{2,}/g, ' ')
      .trim()
    doTranslate(mergedText, rawText)
  }
}

async function saveNoteWithHighlight() {
  if (!literature.value || !floatingMenu.value.rectCoords) return

  noteSaving.value = true
  try {
    await createNote({
      literature_id: literature.value.id,
      page_number: floatingMenu.value.pageNumber,
      rect_coords: floatingMenu.value.rectCoords,
      quoted_text: floatingMenu.value.quotedText,
      content: noteEditorContent.value,
      note_type: noteEditorType.value,
    })
    floatingMenu.value.visible = false
    noteEditorVisible.value = false
    ElMessage.success('笔记已保存')
    await loadNotes()
    await nextTick()
    renderHighlights()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '保存笔记失败'
    ElMessage.error(detail)
  } finally {
    noteSaving.value = false
  }
}

async function loadNotes() {
  if (!literature.value) return
  notesLoading.value = true
  try {
    const resp = await getNotes(literature.value.id, noteFilter.value || undefined)
    notes.value = resp.data.items
    highlights.value = notes.value.filter(n => n.rect_coords)
  } catch {
    notes.value = []
    highlights.value = []
  } finally {
    notesLoading.value = false
  }
}

function focusNote(note: Note) {
  activeNoteId.value = note.id

  const pdfViewer = pdfViewerRef.value
  if (!pdfViewer) return

  const pageElements = pdfViewer.querySelectorAll('.vue-pdf-embed__page')
  const pageNum = parseInt(note.page_number, 10)
  const targetPage = pageElements[pageNum - 1] as HTMLElement | undefined
  if (targetPage) {
    targetPage.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  setTimeout(() => renderHighlights(), 300)
}

async function deleteNoteById(noteId: string) {
  try {
    await deleteNote(noteId)
    ElMessage.success('笔记已删除')
    if (activeNoteId.value === noteId) activeNoteId.value = null
    await loadNotes()
    await nextTick()
    renderHighlights()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '删除笔记失败'
    ElMessage.error(detail)
  }
}

function handlePdfClick(e: MouseEvent) {
  setTimeout(() => {
    const selection = window.getSelection()
    if (selection && !selection.isCollapsed && selection.rangeCount > 0) {
      return
    }

    const pdfViewer = pdfViewerRef.value
    if (!pdfViewer) return

    const overlays = pdfViewer.querySelectorAll('.pdf-highlight-overlay')
    for (const overlay of overlays) {
      const rect = (overlay as HTMLElement).getBoundingClientRect()
      if (
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom
      ) {
        const noteId = (overlay as HTMLElement).dataset.noteId
        if (noteId) {
          highlightMenu.value = {
            visible: true,
            x: e.clientX,
            y: e.clientY - 8,
            noteId,
          }
          return
        }
      }
    }

    highlightMenu.value.visible = false
  }, 150)
}

function handlePdfMouseMove(e: MouseEvent) {
  const pdfViewer = pdfViewerRef.value
  if (!pdfViewer) return

  const overlays = pdfViewer.querySelectorAll('.pdf-highlight-overlay')
  let hovering = false
  for (const overlay of overlays) {
    const rect = (overlay as HTMLElement).getBoundingClientRect()
    if (
      e.clientX >= rect.left &&
      e.clientX <= rect.right &&
      e.clientY >= rect.top &&
      e.clientY <= rect.bottom
    ) {
      hovering = true
      break
    }
  }

  const viewerEl = pdfViewer as HTMLElement
  if (hovering) {
    viewerEl.style.cursor = 'pointer'
  } else {
    viewerEl.style.cursor = ''
  }
}

async function handleDeleteHighlight() {
  const noteId = highlightMenu.value.noteId
  if (!noteId) return

  try {
    await ElMessageBox.confirm('确定要删除此高亮吗？关联的笔记也会一并删除。', '删除高亮', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    highlightMenu.value.visible = false
    return
  }

  highlightMenu.value.visible = false

  try {
    await deleteNote(noteId)
    const overlay = pdfViewerRef.value?.querySelector(`.pdf-highlight-overlay[data-note-id="${noteId}"]`)
    if (overlay) overlay.remove()
    highlights.value = highlights.value.filter(n => n.id !== noteId)
    notes.value = notes.value.filter(n => n.id !== noteId)
    ElMessage.success('高亮已删除')
  } catch (error: any) {
    const detail = error.response?.data?.detail || '删除高亮失败'
    ElMessage.error(detail)
  }
}

function handleEditHighlightNote() {
  const noteId = highlightMenu.value.noteId
  highlightMenu.value.visible = false

  const note = notes.value.find(n => n.id === noteId)
  if (!note) return

  focusNote(note)
}

function noteTypeTag(type: string) {
  const map: Record<string, string> = {
    general: '',
    innovation: 'success',
    method: 'warning',
    question: 'danger',
  }
  return map[type] || ''
}

function noteTypeLabel(type: string) {
  const map: Record<string, string> = {
    general: '通用',
    innovation: '创新点',
    method: '方法',
    question: '问题',
  }
  return map[type] || type
}

function renderHighlights() {
  clearHighlights()

  const pdfViewer = pdfViewerRef.value
  if (!pdfViewer) return

  const pageElements = pdfViewer.querySelectorAll('.vue-pdf-embed__page')
  const highlightColorMap: Record<string, string> = {
    general: 'rgba(255, 235, 59, 0.35)',
    innovation: 'rgba(76, 175, 80, 0.35)',
    method: 'rgba(255, 152, 0, 0.35)',
    question: 'rgba(244, 67, 54, 0.35)',
  }

  highlights.value.forEach(note => {
    const pageNum = parseInt(note.page_number, 10)
    const pageEl = pageElements[pageNum - 1] as HTMLElement | undefined
    if (!pageEl || !note.rect_coords) return

    const coords = note.rect_coords
    const pageRect = pageEl.getBoundingClientRect()

    const highlightDiv = document.createElement('div')
    highlightDiv.className = 'pdf-highlight-overlay'
    highlightDiv.dataset.noteId = note.id
    highlightDiv.style.position = 'absolute'
    highlightDiv.style.left = `${coords.x * 100}%`
    highlightDiv.style.top = `${coords.y * 100}%`
    highlightDiv.style.width = `${coords.width * 100}%`
    highlightDiv.style.height = `${coords.height * 100}%`
    highlightDiv.style.backgroundColor = highlightColorMap[note.note_type] || highlightColorMap.general
    highlightDiv.style.pointerEvents = 'none'
    highlightDiv.style.zIndex = '5'
    highlightDiv.style.borderRadius = '2px'

    if (note.id === activeNoteId.value) {
      highlightDiv.style.outline = '2px solid var(--accent-primary)'
      highlightDiv.style.outlineOffset = '1px'
    }

    pageEl.style.position = pageEl.style.position || 'relative'
    pageEl.appendChild(highlightDiv)
  })
}

function clearHighlights() {
  const pdfViewer = pdfViewerRef.value
  if (!pdfViewer) return
  pdfViewer.querySelectorAll('.pdf-highlight-overlay').forEach(el => el.remove())
}

async function doTranslate(text: string, sourceText: string) {
  activeTab.value = 'translate'
  fullTranslationParagraphs.value = []
  translating.value = true
  streamingTarget.value = ''
  let accumulated = ''
  try {
    await translateTextStream(
      { text, source_lang: 'en', target_lang: 'zh' },
      (chunk: string) => {
        accumulated += chunk
        streamingTarget.value = accumulated
      },
      () => {
        const entry = { source: sourceText, target: accumulated }
        if (continuousMode.value) {
          translationHistory.value.push(entry)
        } else {
          translationHistory.value = [entry]
        }
        translating.value = false
        streamingTarget.value = ''
      },
      (error: string) => {
        ElMessage.error(error)
        translating.value = false
        streamingTarget.value = ''
      },
    )
  } catch (error: any) {
    const detail = error?.message || '翻译失败，请重试'
    ElMessage.error(detail)
    translating.value = false
    streamingTarget.value = ''
  }
}

function copyTranslation() {
  const text = translationHistory.value.map(h => h.target).join('\n\n')
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('译文已复制到剪贴板')
  })
}

function copySource() {
  const text = translationHistory.value.map(h => h.source).join('\n\n')
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('原文已复制到剪贴板')
  })
}

function editSource() {
  ElMessage.info('修改功能即将上线')
}

function handleAIExplain() {
  ElMessage.info('AI 解读功能即将上线')
}

async function handleFullTranslate() {
  if (!literature.value) return

  if (!literature.value.raw_text) {
    ElMessage.warning('该文献暂无文本内容，无法翻译')
    return
  }

  fullTranslating.value = true
  activeTab.value = 'translate'
  try {
    const resp = await startFullTranslate(literature.value.id)

    if (resp.data.task_id === 'cached') {
      if (literature.value.translated_text) {
        try {
          fullTranslationParagraphs.value = JSON.parse(literature.value.translated_text)
        } catch {
          fullTranslationParagraphs.value = []
        }
      }
      ElMessage.success('已加载缓存译文')
      fullTranslating.value = false
      return
    }

    progressDialogVisible.value = true
    translateProgress.value = 0
    translateProgressStatus.value = ''
    translateProgressText.value = '正在准备翻译...'
    backgroundTranslatingId.value = ''

    if (resp.data.message === '翻译任务正在进行中，请查看进度') {
      ElMessage.info('翻译任务正在进行中，已为您关联到当前进度')
      try {
        const litResp = await getLiterature(literature.value!.id)
        literature.value = litResp.data
        if (literature.value.translated_text) {
          fullTranslationParagraphs.value = JSON.parse(literature.value.translated_text)
        }
      } catch {
        // 加载已翻译内容失败不阻塞
      }
    }

    currentTaskId = resp.data.task_id
    startPolling(resp.data.task_id)
  } catch (error: any) {
    fullTranslating.value = false
    const detail = error.response?.data?.detail || '启动翻译失败'
    ElMessage.error(detail)
  }
}

function startPolling(taskId: string) {
  stopPolling()
  pollingTimer = setInterval(async () => {
    try {
      const resp = await getTaskStatus(taskId)
      const task = resp.data

      if (task.total > 0) {
        translateProgress.value = Math.round((task.progress / task.total) * 100)
      }
      translateProgressText.value = `已完成 ${task.progress} / ${task.total} 段`

      if (task.status === 'completed') {
        translateProgress.value = 100
        translateProgressStatus.value = 'success'
        translateProgressText.value = `翻译完成！共 ${task.total} 段`
        stopPolling()
        fullTranslating.value = false
        backgroundTranslatingId.value = ''
        if (literature.value) {
          const litResp = await getLiterature(literature.value.id)
          literature.value = litResp.data
          if (literature.value.translated_text) {
            fullTranslationParagraphs.value = JSON.parse(literature.value.translated_text)
          }
        }
      } else if (task.status === 'failed') {
        translateProgressStatus.value = 'exception'
        translateProgressText.value = task.error || '翻译失败'
        stopPolling()
        fullTranslating.value = false
        backgroundTranslatingId.value = ''
      } else if (task.status === 'cancelled') {
        translateProgressStatus.value = 'exception'
        translateProgressText.value = '翻译已停止'
        stopPolling()
        fullTranslating.value = false
        backgroundTranslatingId.value = ''
        if (literature.value && literature.value.translated_text) {
          fullTranslationParagraphs.value = JSON.parse(literature.value.translated_text)
        }
      } else if (task.progress > 0 && literature.value) {
        try {
          const litResp = await getLiterature(literature.value.id)
          literature.value = litResp.data
          if (literature.value.translated_text) {
            fullTranslationParagraphs.value = JSON.parse(literature.value.translated_text)
            if (fullTranslationParagraphs.value.length === 1 && activeTab.value !== 'translate') {
              activeTab.value = 'translate'
            }
          }
        } catch {
          // 渐进加载失败不中断
        }
      }
    } catch (err: any) {
      if (err?.response?.status === 401) {
        stopPolling()
        fullTranslating.value = false
        backgroundTranslatingId.value = ''
        translateProgressStatus.value = 'exception'
        translateProgressText.value = '登录已过期，请刷新页面后重新登录'
        return
      }
    }
  }, 1500)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function onProgressDialogClose() {
  progressDialogVisible.value = false
  fullTranslating.value = false
  backgroundTranslatingId.value = currentTaskId
  ElMessage.info('翻译在后台继续，结果将实时更新')
}

function onTranslateComplete() {
  progressDialogVisible.value = false
  activeTab.value = 'translate'
}

async function handleStopTranslation() {
  try {
    await ElMessageBox.confirm(
      '停止后已完成的翻译结果将保留，未完成的段落不会继续翻译。是否确认停止？',
      '确认停止翻译',
      { confirmButtonText: '停止', cancelButtonText: '继续翻译', type: 'warning' },
    )
  } catch {
    return
  }

  cancelling = true
  try {
    await cancelTask(currentTaskId)
    stopPolling()
    fullTranslating.value = false
    backgroundTranslatingId.value = ''
    translateProgressStatus.value = 'exception'
    translateProgressText.value = '翻译已停止'
    ElMessage.success('翻译已停止，已完成的部分已保留')
  } catch {
    stopPolling()
    fullTranslating.value = false
    backgroundTranslatingId.value = ''
    translateProgressStatus.value = 'exception'
    translateProgressText.value = '翻译已停止'
    ElMessage.warning('翻译已停止（部分结果可能未完整保存）')
  } finally {
    cancelling = false
  }
}

function clearFullTranslation() {
  fullTranslationParagraphs.value = []
  activeParagraphIndex.value = -1
}

async function handleRetryFullTranslate() {
  if (!literature.value) return
  try {
    await ElMessageBox.confirm('重新翻译将覆盖当前译文，是否继续？', '确认重新翻译', {
      confirmButtonText: '重新翻译',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  stopPolling()
  backgroundTranslatingId.value = ''

  try {
    await deleteFullTranslation(literature.value.id)
    literature.value.translated_text = null
  } catch {
    literature.value.translated_text = null
  }

  fullTranslationParagraphs.value = []
  await handleFullTranslate()
}

async function handleDeleteFullTranslation() {
  if (!literature.value) return
  try {
    await ElMessageBox.confirm('删除后将清除所有译文数据，此操作不可恢复。是否继续？', '确认删除译文', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return
  }

  stopPolling()
  fullTranslating.value = false
  backgroundTranslatingId.value = ''

  try {
    await deleteFullTranslation(literature.value.id)
    ElMessage.success('翻译结果已删除')
  } catch (error: any) {
    const detail = error.response?.data?.detail || '删除失败'
    ElMessage.error(detail)
  }

  literature.value.translated_text = null
  fullTranslationParagraphs.value = []
  activeParagraphIndex.value = -1
}

function scrollToParagraph(idx: number) {
  activeParagraphIndex.value = idx

  const pdfViewer = pdfViewerRef.value
  if (!pdfViewer || totalPages.value === 0) return

  const totalParagraphs = fullTranslationParagraphs.value.length
  if (totalParagraphs === 0) return

  const estimatedPage = Math.max(1, Math.min(totalPages.value, Math.floor((idx / totalParagraphs) * totalPages.value) + 1))

  const pageElements = pdfViewer.querySelectorAll('.vue-pdf-embed__page')
  const targetPage = pageElements[estimatedPage - 1] as HTMLElement | undefined
  if (targetPage) {
    targetPage.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

async function handleAIParse() {
  if (!literature.value) return

  if (!literature.value.raw_text) {
    ElMessage.warning('该文献暂无文本内容，无法分析')
    return
  }

  analyzing.value = true
  analysisDialogVisible.value = true
  analysisData.value = null
  analysisProgress.value = 0
  analysisProgressStatus.value = ''
  analysisProgressText.value = '正在启动 AI 分析...'

  try {
    const resp = await startAnalyze(literature.value.id)

    if (resp.data.task_id === 'cached') {
      analysisProgressText.value = '已有缓存，正在加载...'
      await loadAnalysisResult()
      return
    }

    startAnalysisPolling(resp.data.task_id)
  } catch (error: any) {
    analyzing.value = false
    const detail = error.response?.data?.detail || '启动分析失败'
    ElMessage.error(detail)
  }
}

function startAnalysisPolling(taskId: string) {
  stopAnalysisPolling()
  analysisPollingTimer = setInterval(async () => {
    try {
      const resp = await getTaskStatus(taskId)
      const task = resp.data

      analysisProgress.value = task.total > 0 ? Math.round((task.progress / task.total) * 100) : 50
      analysisProgressText.value = 'AI 正在分析文献内容...'

      if (task.status === 'completed') {
        analysisProgress.value = 100
        analysisProgressStatus.value = 'success'
        analysisProgressText.value = '分析完成！'
        stopAnalysisPolling()
        await loadAnalysisResult()
      } else if (task.status === 'failed') {
        analysisProgressStatus.value = 'exception'
        analysisProgressText.value = task.error || '分析失败'
        stopAnalysisPolling()
        analyzing.value = false
      }
    } catch {
      // 轮询失败不中断
    }
  }, 1500)
}

function stopAnalysisPolling() {
  if (analysisPollingTimer) {
    clearInterval(analysisPollingTimer)
    analysisPollingTimer = null
  }
}

async function loadAnalysisResult() {
  if (!literature.value) return
  try {
    const resp = await getAnalysis(literature.value.id)
    analysisData.value = resp.data
  } catch {
    analysisData.value = null
  } finally {
    analyzing.value = false
  }
}

async function reAnalyze() {
  analysisData.value = null
  await handleAIParse()
}

async function addInnovationAsNote(text: string, idx: number) {
  if (!literature.value) return

  innovationAddingIdx.value = idx
  try {
    await createNote({
      literature_id: literature.value.id,
      page_number: '1',
      rect_coords: { x: 0, y: 0, width: 0, height: 0 },
      quoted_text: text,
      content: text,
      note_type: 'innovation',
    })
    ElMessage.success('创新点已加入笔记')
    await loadNotes()
    await nextTick()
    renderHighlights()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '添加笔记失败'
    ElMessage.error(detail)
  } finally {
    innovationAddingIdx.value = -1
  }
}

async function handleGenerateOutline() {
  if (!literature.value) return

  outlineGenerating.value = true
  outlineGenerated.value = false
  outlineDialogVisible.value = true
  outlineData.value = null

  try {
    const resp = await generateOutline(literature.value.id)
    outlineData.value = resp.data.data
    outlineGenerated.value = true
  } catch (error: any) {
    outlineDialogVisible.value = false
    const detail = error.response?.data?.detail || '生成大纲失败'
    ElMessage.error(detail)
  } finally {
    outlineGenerating.value = false
  }
}

function goToPreMeeting() {
  outlineDialogVisible.value = false
  router.push('/presentation')
}

async function loadLiteratureTags() {
  if (!literature.value) return
  try {
    const resp = await getLiteratureTags(literature.value.id)
    literatureTags.value = resp.data.tags
  } catch {
    literatureTags.value = []
  }
}

async function handleAddTag() {
  if (!literature.value || !newTagName.value.trim()) return
  tagAdding.value = true
  try {
    await addTagToLiterature(literature.value.id, newTagName.value.trim())
    newTagName.value = ''
    tagPopoverVisible.value = false
    await loadLiteratureTags()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '添加标签失败'
    ElMessage.error(detail)
  } finally {
    tagAdding.value = false
  }
}

async function handleRemoveTag(tagId: string) {
  if (!literature.value) return
  try {
    await removeTagFromLiterature(literature.value.id, tagId)
    await loadLiteratureTags()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '删除标签失败'
    ElMessage.error(detail)
  }
}

// ========== 拖拽分隔条 ==========
let isResizing = false

function startResize() {
  isResizing = true
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onResizeMove(e: MouseEvent) {
  if (!isResizing) return
  const readerBody = document.querySelector('.reader-body') as HTMLElement | null
  const readerRect = readerBody ? readerBody.getBoundingClientRect() : { right: window.innerWidth }
  const newSideWidth = readerRect.right - e.clientX - resizerWidth
  sidePanelWidth.value = newSideWidth
  updateWidths()
}

function stopResize() {
  isResizing = false
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}
</script>

<style scoped>
.reader-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--bg-secondary);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 24px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-primary);
  flex-shrink: 0;
  height: 52px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.toolbar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  margin-left: 12px;
}

.lit-tag {
  border-radius: var(--radius-lg);
  cursor: default;
}

.add-tag-btn {
  width: 24px;
  height: 24px;
  padding: 0;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
}

.add-tag-btn:hover {
  color: var(--accent-primary);
  background: var(--teal-50);
}

.tag-popover-content {
  padding: 4px 0;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.toolbar-translating-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--accent-primary);
  white-space: nowrap;
}

.toolbar-translating-hint .el-icon {
  font-size: 14px;
}

.toolbar-actions .el-button {
  border-radius: var(--radius-lg);
  font-weight: 500;
}

.reader-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.pdf-panel {
  display: flex;
  flex-direction: column;
  background: var(--slate-100);
  overflow: hidden;
  flex-shrink: 0;
  min-width: 0;
}

.pdf-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.pdf-viewer {
  flex: 1;
  overflow: auto;
  padding: 20px;
}

.pdf-viewer :deep(.vue-pdf-embed) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.pdf-viewer :deep(.vue-pdf-embed__page) {
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  border-radius: 4px;
}

.resizer {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  position: relative;
  flex-shrink: 0;
  z-index: 10;
}

.resizer:hover .resizer-line,
.resizer:active .resizer-line {
  background: var(--accent-primary);
}

.resizer-line {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 2px;
  transform: translateX(-50%);
  background: var(--border-color);
  transition: background 0.2s;
}

.side-panel {
  border-left: 1px solid var(--border-color);
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
  min-width: 0;
}

.side-panel-header {
  padding: 12px 20px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.side-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.side-panel-title .el-icon {
  color: var(--accent-primary);
}

.side-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  width: 100%;
  overflow: hidden;
}

.side-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  flex-shrink: 0;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  padding: 0 8px;
}

.side-tabs :deep(.el-tabs__nav) {
  margin-left: 12px;
}

.side-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  min-height: 0;
  width: 100%;
}

.side-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.tab-content {
  height: 100%;
  overflow: hidden;
  padding: 16px;
  box-sizing: border-box;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.translation-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  min-height: 0;
  flex: 1;
}

.trans-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.trans-history-item,
.source-history-item {
  padding: 4px 0;
}

.trans-history-item .el-divider,
.source-history-item .el-divider {
  margin: 8px 0;
}

.source-block,
.trans-block {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 14px;
  width: 100%;
  box-sizing: border-box;
  min-height: 0;
}

.trans-block {
  background: var(--teal-50);
  border-color: var(--teal-100);
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.source-block {
  flex: 1;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.source-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.source-scroll::-webkit-scrollbar {
  width: 4px;
}

.source-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.source-scroll::-webkit-scrollbar-thumb {
  background: var(--slate-300);
  border-radius: 2px;
}

.source-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--slate-400);
}

.block-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.block-label {
  font-size: 12px;
  font-weight: 600;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.block-label.trans-label {
  color: var(--teal-600);
}

.block-label:not(.trans-label) {
  color: var(--text-muted);
}

.block-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  margin: 0;
  word-break: normal;
  overflow-wrap: break-word;
}

.source-text {
  color: var(--text-secondary);
}

.trans-text {
  color: var(--text-primary);
}

.trans-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.trans-scroll::-webkit-scrollbar {
  width: 4px;
}

.trans-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.trans-scroll::-webkit-scrollbar-thumb {
  background: var(--slate-300);
  border-radius: 2px;
}

.trans-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--slate-400);
}

.translating {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
}

.streaming-preview {
  max-height: 300px;
  overflow-y: auto;
  line-height: 1.8;
  color: var(--text-primary);
  background: rgba(66, 184, 131, 0.04);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-top: 8px;
  white-space: pre-wrap;
  word-break: break-word;
}

.note-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.note-panel :deep(.el-textarea__inner) {
  flex: 1;
  resize: none;
  border-radius: var(--radius-lg);
  border-color: var(--border-color);
  font-size: 14px;
  line-height: 1.7;
}

.note-panel :deep(.el-textarea__inner:focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.1);
}

.save-btn {
  align-self: flex-end;
  border-radius: var(--radius-lg);
}

.progress-content {
  text-align: center;
  padding: 20px 0;
}

.progress-text {
  margin-top: 16px;
  font-size: 14px;
  color: var(--text-secondary);
}

.full-translation-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.full-trans-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 4px;
}

.translation-expiry-warning {
  margin-bottom: 12px;
  flex-shrink: 0;
}

.full-trans-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.full-trans-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--accent-primary);
}

.full-trans-list {
  flex: 1;
  overflow-y: auto;
  padding-top: 8px;
}

.full-trans-item {
  display: flex;
  gap: 10px;
  padding: 10px 8px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid var(--border-light);
}

.full-trans-item:hover {
  background: var(--bg-tertiary);
}

.full-trans-item.has-translation:hover {
  background: var(--teal-50);
}

.full-trans-item.is-active {
  background: var(--teal-50);
  border-left: 3px solid var(--accent-primary);
  padding-left: 5px;
}

.full-trans-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  flex-shrink: 0;
  margin-top: 2px;
}

.has-translation .full-trans-index {
  background: var(--teal-100);
  color: var(--teal-700);
}

.full-trans-content {
  flex: 1;
  min-width: 0;
}

.full-trans-text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.full-trans-original {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-muted);
  margin: 0;
}

.full-trans-empty {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0 0 4px 0;
  font-style: italic;
}

.floating-menu {
  position: fixed;
  z-index: 9999;
  transform: translate(-50%, -100%);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  display: flex;
  gap: 2px;
  padding: 4px;
}

.floating-menu-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}

.floating-menu-btn:hover {
  background: var(--bg-tertiary);
}

.floating-menu-btn .el-icon {
  font-size: 15px;
}

.highlight-btn:hover {
  color: var(--accent-primary);
  background: var(--teal-50);
}

.note-btn:hover {
  color: var(--accent-primary);
  background: var(--teal-50);
}

.translate-btn:hover {
  color: var(--accent-primary);
  background: var(--teal-50);
}

.notes-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.notes-filter {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.notes-filter :deep(.el-radio-button__inner) {
  font-size: 12px;
  padding: 6px 12px;
}

.notes-list {
  flex: 1;
  overflow-y: auto;
  padding-top: 8px;
}

.note-card {
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.note-card:hover {
  border-color: var(--accent-primary);
  background: var(--teal-50);
}

.note-card--active {
  border-color: var(--accent-primary);
  background: var(--teal-50);
  box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.15);
}

.note-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.note-card-page {
  font-size: 12px;
  color: var(--text-muted);
  flex: 1;
}

.note-card-quote {
  font-size: 13px;
  color: var(--text-secondary);
  font-style: italic;
  margin: 0 0 6px 0;
  padding: 6px 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--accent-primary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.note-card-content {
  font-size: 13px;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.note-card-content--empty {
  color: var(--text-muted);
  font-style: italic;
}

.note-editor-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.note-editor-quote {
  font-size: 13px;
  color: var(--text-secondary);
  font-style: italic;
  margin: 0;
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--accent-primary);
  line-height: 1.6;
}

.note-editor-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.note-editor-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.pdf-highlight-overlay {
  transition: outline 0.2s;
}

.analysis-result {
  max-height: 60vh;
  overflow-y: auto;
}

.analysis-section {
  margin-bottom: 20px;
}

.analysis-section:last-child {
  margin-bottom: 0;
}

.analysis-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.analysis-section-title .el-icon {
  color: var(--accent-primary);
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.summary-item {
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 12px;
}

.summary-label {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
  background: var(--teal-50);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.summary-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  margin: 0;
}

.innovation-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.innovation-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--accent-primary);
}

.innovation-index {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--accent-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
}

.innovation-text {
  flex: 1;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  margin: 0;
}

.innovation-item .el-button {
  flex-shrink: 0;
  border-radius: var(--radius-lg);
}

.methods-content {
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 14px;
}

.outline-container {
  max-height: 60vh;
  overflow-y: auto;
}

.outline-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
}

.outline-progress-icon {
  color: var(--accent-primary);
  margin-bottom: 16px;
}

.outline-progress-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px 0;
}

.outline-progress-sub {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

.slide-title-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.slide-num {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--accent-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.slide-title-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.slide-bullets {
  margin: 0;
  padding: 0 0 0 36px;
  list-style: none;
}

.slide-bullets li {
  position: relative;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-secondary);
  padding: 4px 0;
}

.slide-bullets li::before {
  content: '';
  position: absolute;
  left: -18px;
  top: 12px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-primary);
}

.slide-notes {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 8px 0 0 36px;
  font-size: 12px;
  color: var(--accent-primary);
  font-style: italic;
  background: var(--teal-50);
  padding: 8px 12px;
  border-radius: var(--radius-md);
}

.slide-notes .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.outline-synced-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--teal-600);
  font-size: 13px;
  font-weight: 500;
}
</style>
