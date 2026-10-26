/**
 * API client functions for eBird sightings, feeder options, and feeder visitor likelihood.
 */

export async function fetchEbirdSightings({ lat, lon, radiusMiles = 1.0, days = 30 }) {
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_miles: String(radiusMiles),
    days: String(days),
  })
  const res = await fetch(`/api/ebird/sightings?${params.toString()}`)
  if (!res.ok) {
    throw new Error(`Failed to load eBird sightings (${res.status})`)
  }
  return res.json()
}

export async function calculateFeederVisitors({ foods, lon = null, lat = null }) {
  const res = await fetch('/api/feeder/likelihood', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ foods, lon, lat }),
  })
  if (!res.ok) {
    throw new Error(`HTTP error ${res.status}`)
  }
  return res.json()
}

export async function fetchFeederOptions() {
  const res = await fetch('/api/feeder/options')
  if (!res.ok) {
    throw new Error(`Failed to fetch feeder options (${res.status})`)
  }
  return res.json()
}

export function getBirdPhotoUrl(species) {
  return `/api/birds/photo?species=${encodeURIComponent(species)}`
}
