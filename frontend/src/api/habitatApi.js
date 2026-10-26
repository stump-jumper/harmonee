/**
 * API client functions for habitat objects and interactive paint segmentation.
 */

export async function fetchHabitatObjects() {
  const res = await fetch('/api/habitat-objects')
  if (!res.ok) {
    throw new Error(`Failed to fetch habitat objects (${res.status})`)
  }
  return res.json()
}

export async function persistHabitatObjects(objects) {
  const res = await fetch('/api/habitat-objects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ objects }),
  })
  if (!res.ok) {
    throw new Error(`Failed to save habitat objects (${res.status})`)
  }
  return res.json()
}

export async function segmentParcelFromPaint(strokes) {
  const res = await fetch('/api/segment/paint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strokes }),
  })
  if (!res.ok) {
    throw new Error(`Paint segmentation failed (${res.status})`)
  }
  return res.json()
}
