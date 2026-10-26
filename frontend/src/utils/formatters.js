/**
 * String escaping and human-readable timestamp formatting helpers.
 */

export function escapeHtml(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

export function formatSightingDate(dtStr, nowDate = null) {
  if (!dtStr) return ''
  try {
    const d = new Date(dtStr.replace(' ', 'T'))
    if (isNaN(d.getTime())) return dtStr
    const now = nowDate || new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffHrs = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHrs < 1) return 'Just now'
    if (diffHrs < 24) return `${diffHrs}h ago`
    const diffDays = Math.floor(diffHrs / 24)
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return dtStr
  }
}
