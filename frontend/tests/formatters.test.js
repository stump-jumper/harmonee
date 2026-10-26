import test from 'node:test'
import assert from 'node:assert/strict'
import { escapeHtml, formatSightingDate } from '../src/utils/formatters.js'

test('escapeHtml escapes dangerous HTML entities', () => {
  const raw = `<script alert("test") & 'hello' "world">`
  const escaped = escapeHtml(raw)
  assert.equal(escaped, `&lt;script alert(&quot;test&quot;) &amp; &#039;hello&#039; &quot;world&quot;&gt;`)
})

test('escapeHtml handles null and empty string', () => {
  assert.equal(escapeHtml(null), '')
  assert.equal(escapeHtml(''), '')
})

test('formatSightingDate formats relative time periods', () => {
  const base = new Date('2026-10-26T12:00:00Z')

  // 30 minutes ago -> Just now
  const justNow = new Date(base.getTime() - 30 * 60 * 1000).toISOString()
  assert.equal(formatSightingDate(justNow, base), 'Just now')

  // 3 hours ago -> 3h ago
  const hoursAgo = new Date(base.getTime() - 3 * 3600 * 1000).toISOString()
  assert.equal(formatSightingDate(hoursAgo, base), '3h ago')

  // 1 day ago -> Yesterday
  const yesterday = new Date(base.getTime() - 25 * 3600 * 1000).toISOString()
  assert.equal(formatSightingDate(yesterday, base), 'Yesterday')

  // 3 days ago -> 3d ago
  const daysAgo = new Date(base.getTime() - 3 * 24 * 3600 * 1000).toISOString()
  assert.equal(formatSightingDate(daysAgo, base), '3d ago')
})
