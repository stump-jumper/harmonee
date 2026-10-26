/**
 * API client functions for iNaturalist property observations and settings.
 */

export async function fetchInaturalistObservations({
  username = '',
  propertyOnly = true,
  radiusMiles = 0.5,
  scope = 'property',
  taxon = '',
  lat = null,
  lon = null,
} = {}) {
  const params = new URLSearchParams()
  if (username) params.append('username', username)
  params.append('property_only', String(Boolean(propertyOnly)))
  params.append('scope', scope)
  if (radiusMiles != null) params.append('radius_miles', String(radiusMiles))
  if (taxon && taxon !== 'all') params.append('taxon', taxon)
  if (lat != null) params.append('lat', String(lat))
  if (lon != null) params.append('lon', String(lon))

  const res = await fetch(`/api/inaturalist/observations?${params.toString()}`)
  if (!res.ok) {
    throw new Error(`Failed to load iNaturalist observations (${res.status})`)
  }
  return res.json()
}

export async function fetchInaturalistUsername() {
  const res = await fetch('/api/inaturalist/username')
  if (!res.ok) {
    throw new Error(`Failed to load iNaturalist username (${res.status})`)
  }
  return res.json()
}

export async function saveInaturalistUsername(username) {
  const res = await fetch('/api/inaturalist/username', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username }),
  })
  if (!res.ok) {
    throw new Error(`Failed to update iNaturalist username (${res.status})`)
  }
  return res.json()
}
