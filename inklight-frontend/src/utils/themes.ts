export interface ThemePreset {
  name: string
  label: string
  isDark: boolean
  variables: Record<string, string>
}

const LIGHT_SEMANTIC_DEFAULTS: Record<string, string> = {
  '--bg-primary': 'var(--bg-color)',
  '--bg-secondary': 'var(--bg-color)',
  '--bg-tertiary': 'var(--bg-color)',
  '--bg-hover': 'var(--bg-color)',
  '--text-primary': '#1e293b',
  '--text-secondary': '#475569',
  '--text-tertiary': '#64748b',
  '--text-muted': '#94a3b8',
  '--border-color': 'rgba(0, 0, 0, 0.1)',
  '--border-light': 'rgba(0, 0, 0, 0.06)',
  '--shadow-sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  '--shadow-md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  '--shadow-lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  '--el-bg-color': 'var(--bg-color)',
  '--el-bg-color-overlay': 'var(--bg-color)',
  '--el-text-color-primary': '#303133',
  '--el-text-color-regular': '#606266',
  '--el-text-color-secondary': '#909399',
  '--el-text-color-placeholder': '#a8abb2',
  '--el-border-color': 'rgba(0, 0, 0, 0.1)',
  '--el-border-color-light': 'rgba(0, 0, 0, 0.08)',
  '--el-border-color-lighter': 'rgba(0, 0, 0, 0.06)',
  '--el-border-color-extra-light': 'rgba(0, 0, 0, 0.04)',
  '--el-fill-color': 'var(--bg-color)',
  '--el-fill-color-light': 'var(--bg-color)',
  '--el-fill-color-blank': 'var(--bg-color)',
  '--el-color-white': 'var(--bg-color)',
  '--el-color-black': '#000000',
}

const DARK_SEMANTIC_OVERRIDES: Record<string, string> = {
  '--bg-primary': '#1e1e1e',
  '--bg-secondary': '#252525',
  '--bg-tertiary': '#2d2d2d',
  '--bg-hover': '#333333',
  '--text-primary': '#e0e0e0',
  '--text-secondary': '#b0b0b0',
  '--text-tertiary': '#888888',
  '--text-muted': '#666666',
  '--border-color': '#333333',
  '--border-light': '#2a2a2a',
  '--shadow-sm': '0 1px 2px 0 rgb(0 0 0 / 0.3)',
  '--shadow-md': '0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3)',
  '--shadow-lg': '0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.4)',
  '--el-bg-color': '#1e1e1e',
  '--el-bg-color-overlay': '#252525',
  '--el-text-color-primary': '#e0e0e0',
  '--el-text-color-regular': '#b0b0b0',
  '--el-text-color-secondary': '#888888',
  '--el-text-color-placeholder': '#666666',
  '--el-border-color': '#333333',
  '--el-border-color-light': '#2a2a2a',
  '--el-border-color-lighter': '#252525',
  '--el-border-color-extra-light': '#222222',
  '--el-fill-color': '#2d2d2d',
  '--el-fill-color-light': '#252525',
  '--el-fill-color-blank': '#1e1e1e',
  '--el-color-white': '#1e1e1e',
  '--el-color-black': '#e0e0e0',
}

export const DEFAULT_THEME_COLOR = '#e8f2e2'

export const themePresets: ThemePreset[] = [
  {
    name: '极淡绿',
    label: '极淡绿',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      '--bg-color': '#e8f2e2',
    },
  },
  {
    name: '淡蓝',
    label: '淡蓝',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      '--bg-color': '#e2ecf2',
    },
  },
  {
    name: '淡紫',
    label: '淡紫',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      '--bg-color': '#e8e2f0',
    },
  },
  {
    name: '淡粉',
    label: '淡粉',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      '--bg-color': '#f2e6e8',
    },
  },
  {
    name: '米白',
    label: '米白',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      '--bg-color': '#f0e8e2',
    },
  },
  {
    name: '浅灰',
    label: '浅灰',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      '--bg-color': '#e8e8e8',
    },
  },
  {
    name: '纯净白',
    label: '纯净白',
    isDark: false,
    variables: {
      ...LIGHT_SEMANTIC_DEFAULTS,
      '--bg-color': '#ffffff',
    },
  },
  {
    name: '深色',
    label: '深色',
    isDark: true,
    variables: {
      '--bg-color': '#1a1a1a',
      ...DARK_SEMANTIC_OVERRIDES,
    },
  },
]

export function findThemeByColor(color: string | null | undefined): ThemePreset {
  if (!color) return themePresets[0]
  const found = themePresets.find(t => t.variables['--bg-color'] === color)
  if (!found) {
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