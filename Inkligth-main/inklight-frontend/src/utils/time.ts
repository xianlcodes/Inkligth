/**
 * 北京时间格式化工具
 *
 * 后端存储的时间为 UTC（无时区后缀的 ISO 字符串），
 * 此模块自动补偿 +Z 并转为 Asia/Shanghai 时区，
 * 所有组件统一通过此模块格式化时间，避免各组件自行处理。
 */

// Asia/Shanghai 是 UTC+8，480 分钟
const BJ_OFFSET = 480

/**
 * 将 Date 对象「偏移」到北京时间，使 .getHours() / .getDate() 等返回北京时间分量
 *
 * 原理：给 epoch 加上时区差（北京偏移 - 本地偏移），
 * 这样浏览器在本地时区下读取 getHours 时得到的就是北京时间的时/分/秒。
 */
function toBeijingTime(date: Date): Date {
  const localOffset = -date.getTimezoneOffset()
  return new Date(date.getTime() + (BJ_OFFSET - localOffset) * 60000)
}

/**
 * 将后端 UTC ISO 字符串转为 Date（自动补 Z）
 */
function toDate(dateStr: string): Date {
  const normalized = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z'
  return new Date(normalized)
}

/**
 * 获取北京时间的年/月/日/时/分/秒分量
 */
function getBeijingComponents(date: Date) {
  const bj = toBeijingTime(date)
  return {
    year: bj.getFullYear(),
    month: bj.getMonth() + 1,
    day: bj.getDate(),
    hours: bj.getHours(),
    minutes: bj.getMinutes(),
    seconds: bj.getSeconds(),
  }
}

/**
 * 完整日期时间: 2024/01/15 14:30:00
 * 适用场景：表格列、详情页
 */
export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    return toDate(dateStr).toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return '-'
  }
}

/**
 * 短日期 + 时间: 1月15日 14:30
 * 适用场景：文献卡片、笔记列表、对话历史
 */
export function formatDateShort(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const c = getBeijingComponents(toDate(dateStr))
    const h = String(c.hours).padStart(2, '0')
    const min = String(c.minutes).padStart(2, '0')
    return `${c.month}月${c.day}日 ${h}:${min}`
  } catch {
    return '-'
  }
}

/**
 * 仅日期: 1月15日
 * 适用场景：文献卡片
 */
export function formatDateOnly(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const c = getBeijingComponents(toDate(dateStr))
    return `${c.month}月${c.day}日`
  } catch {
    return '-'
  }
}

/**
 * 仅日期带年: 2024年1月15日
 * 适用场景：需要显示完整日期的场景
 */
export function formatDateFull(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const c = getBeijingComponents(toDate(dateStr))
    return `${c.year}年${c.month}月${c.day}日`
  } catch {
    return '-'
  }
}

/**
 * 仅时间: 14:30
 * 适用场景：聊天消息
 */
export function formatTimeOnly(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const c = getBeijingComponents(toDate(dateStr))
    return `${String(c.hours).padStart(2, '0')}:${String(c.minutes).padStart(2, '0')}`
  } catch {
    return '-'
  }
}

/**
 * 相对时间: 刚刚 / 3分钟前 / 2小时前 / 昨天 14:30 / 1月15日
 * 适用场景：对话历史、动态更新时间
 */
export function formatRelative(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const d = toDate(dateStr)
    const now = new Date()

    // 将当前时间和目标时间都偏移到北京时间，再计算差值
    const nowBJ = toBeijingTime(now)
    const dBJ = toBeijingTime(d)
    const diffMs = nowBJ.getTime() - dBJ.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    const diffHour = Math.floor(diffMs / 3600000)
    const diffDay = Math.floor(diffMs / 86400000)

    if (diffMin < 1) return '刚刚'
    if (diffMin < 60) return `${diffMin}分钟前`
    if (diffHour < 24) return `${diffHour}小时前`
    if (diffDay === 1) return `昨天 ${String(dBJ.getHours()).padStart(2, '0')}:${String(dBJ.getMinutes()).padStart(2, '0')}`
    if (diffDay < 7) return `${diffDay}天前`

    const c = getBeijingComponents(d)
    const nowBJComponents = getBeijingComponents(now)
    if (c.year !== nowBJComponents.year) {
      return `${c.year}年${c.month}月${c.day}日`
    }
    return `${c.month}月${c.day}日`
  } catch {
    return '-'
  }
}

/**
 * ISO 日期格式: 2024-01-15
 * 适用场景：文件导出命名等
 */
export function formatISODate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const c = getBeijingComponents(toDate(dateStr))
    return `${c.year}-${String(c.month).padStart(2, '0')}-${String(c.day).padStart(2, '0')}`
  } catch {
    return '-'
  }
}

/**
 * 兼容旧名称 —— 完整日期时间格式
 * @deprecated 使用 formatDateTime 替代
 */
export const formatDateCN = formatDateTime

// ── 辅助函数 ──

/**
 * 返回一个「本地时间分量等于北京时间」的 Date 对象
 * 例：北京时间 2024-01-15 14:30 → .getHours() = 14（无论浏览器时区）
 */
export function getBeijingNow(): Date {
  return toBeijingTime(new Date())
}

/**
 * 计算两个 UTC 字符串之间相差的北京时间天数（用于 Reader 译文过期判断等）
 */
export function getBeijingAgeDays(dateStr: string): number {
  const d = toDate(dateStr)
  const nowBJ = toBeijingTime(new Date())
  const dBJ = toBeijingTime(d)
  return (nowBJ.getTime() - dBJ.getTime()) / (1000 * 60 * 60 * 24)
}
