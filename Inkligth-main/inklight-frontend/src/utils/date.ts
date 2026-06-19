/**
 * 将 UTC ISO 日期字符串格式化为中国北京时间显示。
 * 后端存储的时间为 UTC，无时区后缀，此函数自动补充 +Z 并转为 Asia/Shanghai 时区。
 */
export function formatDateCN(dateStr: string): string {
  if (!dateStr) return '-'
  // 无时区信息的 ISO 字符串视为 UTC
  const normalized = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z'
  return new Date(normalized).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}
