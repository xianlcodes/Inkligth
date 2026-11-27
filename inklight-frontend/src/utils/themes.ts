export interface ThemePreset {
  name: string
  label: string
  isDark: boolean
  variables: Record<string, string>
}

// 分层语义默认值：纸感三层背景（主/次/三级各不相同，不再压平）
const LIGHT_SEMANTIC_DEFAULTS: Record<string, string> = {
  '--bg-primary': 'var(--bg-color)',
  '--bg-secondary': 'var(--bg-secondary-c)',
  '--bg-tertiary': 'var(--bg-tertiary-c)',
  '--bg-hover': 'var(--bg-hover-c)',
  '--bg-overlay': 'rgba(255,255,255,0.55)',
  '--bg-overlay-hover': 'rgba(255,255,255,0.75)',
  '--bg-overlay-heavy': 'rgba(255,255,255,0.8)',
  '--text-primary': '#1f2a24',
  '--text-secondary': '#46544c',
  '--text-tertiary': '#63756c',
  '--text-muted': '#8fa096',
  '--border-color': 'rgba(31, 42, 36, 0.12)',
  '--border-light': 'rgba(31, 42, 36, 0.06)',
  '--shadow-sm': '0 1px 2px 0 rgb(31 42 36 / 0.05)',
  '--shadow-md': '0 4px 6px -1px rgb(31 42 36 / 0.1), 0 2px 4px -2px rgb(31 42 36 / 0.1)',
  '--shadow-lg': '0 10px 15px -3px rgb(31 42 36 / 0.1), 0 4px 6px -4px rgb(31 42 36 / 0.1)',
  '--el-bg-color': 'var(--bg-color)',
  '--el-bg-color-overlay': 'var(--bg-color)',
  '--el-text-color-primary': '#1f2a24',
  '--el-text-color-regular': '#46544c',
  '--el-text-color-secondary': '#8fa096',
  '--el-text-color-placeholder': '#a8b5ad',
  '--el-border-color': 'rgba(31, 42, 36, 0.12)',
  '--el-border-color-light': 'rgba(31, 42, 36, 0.08)',
  '--el-border-color-lighter': 'rgba(31, 42, 36, 0.06)',
  '--el-border-color-extra-light': 'rgba(31, 42, 36, 0.04)',
  '--el-fill-color': 'var(--bg-secondary-c)',
  '--el-fill-color-light': 'var(--bg-secondary-c)',
  '--el-fill-color-blank': 'var(--bg-color)',
  '--el-color-white': 'var(--bg-color)',
  '--el-color-black': '#1a120c',
}

// 每个纸色预设的分层底色（主/次/三级/悬停）
interface PaperLayers {
  bg: string
  secondary: string
  tertiary: string
  hover: string
}

const PAPER_LAYERS: Record<string, PaperLayers> = {
  '#ffffff': { bg: '#ffffff', secondary: '#faf7f2', tertiary: '#f3efe7', hover: '#eef4ef' },
  '#f7f3ee': { bg: '#f7f3ee', secondary: '#f3ede4', tertiary: '#ece5d8', hover: '#eef4ef' },
  '#e8f3ec': { bg: '#e8f3ec', secondary: '#e1efe7', tertiary: '#d7e8dd', hover: '#eef4ef' },
  '#e3eef7': { bg: '#e3eef7', secondary: '#ddebf5', tertiary: '#d2e4f0', hover: '#edf4fb' },
  '#ede5f2': { bg: '#ede5f2', secondary: '#e8dfee', tertiary: '#dfd5e8', hover: '#f2edf6' },
  '#f5eae3': { bg: '#f5eae3', secondary: '#f1e3da', tertiary: '#ead9cc', hover: '#f7f1ec' },
  '#edeeef': { bg: '#edeeef', secondary: '#e7e9ea', tertiary: '#dfe2e4', hover: '#f1f3f4' },
}

export const DEFAULT_THEME_COLOR = '#ffffff'

// 文献阅读平台：全部为亮色纸感预设，无深色（护眼靠低饱和底色而非深色模式）
export const themePresets: ThemePreset[] = [
  {
    name: '纯净白',
    label: '纯净白',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      ...layerVars('#ffffff'),
    },
  },
  {
    name: '暖白',
    label: '暖白',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      ...layerVars('#f7f3ee'),
    },
  },
  {
    name: '薄荷',
    label: '薄荷',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      ...layerVars('#e8f3ec'),
    },
  },
  {
    name: '雾蓝',
    label: '雾蓝',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      ...layerVars('#e3eef7'),
    },
  },
  {
    name: '淡紫',
    label: '淡紫',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      ...layerVars('#ede5f2'),
    },
  },
  {
    name: '杏粉',
    label: '杏粉',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      ...layerVars('#f5eae3'),
    },
  },
  {
    name: '烟灰',
    label: '烟灰',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      ...layerVars('#edeeef'),
    },
  },
]

function layerVars(bg: string): Record<string, string> {
  const layers = PAPER_LAYERS[bg] ?? PAPER_LAYERS['#ffffff']
  return {
    '--bg-color': layers.bg,
    '--bg-secondary-c': layers.secondary,
    '--bg-tertiary-c': layers.tertiary,
    '--bg-hover-c': layers.hover,
  }
}

export function findThemeByColor(color: string | null | undefined): ThemePreset {
  if (!color) return themePresets[0]
  const found = themePresets.find(t => t.variables['--bg-color'] === color)
  if (!found) {
    // 历史原因：旧版本曾提供深色主题（#1a1a1a）；已随「全站亮色」方向移除，
    // 存量用户的深色设置回退到暖白（最接近纸质阅读观感）
    console.warn(`[Theme] 未找到匹配预设的颜色值: "${color}", 回退到默认主题`)
    return themePresets[0]
  }
  return found
}

export function applyTheme(preset: ThemePreset) {
  const root = document.documentElement

  for (const [key, value] of Object.entries(preset.variables)) {
    root.style.setProperty(key, value)
  }

  document.body.style.backgroundColor = preset.variables['--bg-color'] || DEFAULT_THEME_COLOR
}

export function applyDefaultTheme() {
  const preset = themePresets[0]
  applyTheme(preset)
}