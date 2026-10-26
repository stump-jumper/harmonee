/**
 * API client functions for property address, geocoding autocomplete, and aerial imagery metadata.
 */

export async function fetchPropertyData() {
  const res = await fetch('/api/address')
  if (!res.ok) {
    throw new Error(`Failed to fetch property data (${res.status})`)
  }
  return res.json()
}

export async function savePropertyAddress({ address, lat = null, lon = null }) {
  const res = await fetch('/api/address', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address, lat, lon }),
  })
  if (!res.ok) {
    throw new Error(`Failed to save address (${res.status})`)
  }
  return res.json()
}

export async function fetchAddressSuggestions(query) {
  const res = await fetch(`/api/address/autocomplete?q=${encodeURIComponent(query)}`)
  if (!res.ok) {
    throw new Error(`Autocomplete request failed (${res.status})`)
  }
  const data = await res.json()
  return data.suggestions || []
}

export async function fetchImageryCaptureDate(lat, lon) {
  const res = await fetch(
    `/api/imagery-date?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`
  )
  if (!res.ok) {
    return null
  }
  const data = await res.json()
  return data.captureDate || null
}

export async function fetchSupportedCounties() {
  const res = await fetch('/api/supported-counties')
  if (!res.ok) {
    throw new Error(`Failed to fetch supported counties (${res.status})`)
  }
  return res.json()
}
