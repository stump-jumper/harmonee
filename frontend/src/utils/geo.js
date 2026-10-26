/**
 * Geospatial calculations for parcel area, bounding boxes, circles, and ground-meter projections.
 */

export function computeRingAreaSqMeters(ring) {
  if (!ring || ring.length < 3) return 0
  const lat0 = (ring[0][1] * Math.PI) / 180
  const metersPerDegLat = 111132.954 - 559.822 * Math.cos(2 * lat0) + 1.175 * Math.cos(4 * lat0)
  const metersPerDegLon = 111412.84 * Math.cos(lat0) - 93.5 * Math.cos(3 * lat0)

  let sum = 0
  for (let i = 0; i < ring.length - 1; i++) {
    const x1 = ring[i][0] * metersPerDegLon
    const y1 = ring[i][1] * metersPerDegLat
    const x2 = ring[i + 1][0] * metersPerDegLon
    const y2 = ring[i + 1][1] * metersPerDegLat
    sum += x1 * y2 - x2 * y1
  }
  return Math.abs(sum) / 2
}

export function calculateParcelAcreage(feat) {
  if (!feat) return null

  const props = feat.properties || {}
  if (props.ACRES && !isNaN(Number(props.ACRES))) {
    return `${Number(props.ACRES).toFixed(2)} acres`
  }

  if (props.Shape_Area && !isNaN(Number(props.Shape_Area)) && Number(props.Shape_Area) > 0) {
    const acres = Number(props.Shape_Area) / 43560
    return `${acres.toFixed(2)} acres`
  }

  const geom = feat.geometry
  const polygons =
    geom?.type === 'Polygon'
      ? [geom.coordinates]
      : geom?.type === 'MultiPolygon'
        ? geom.coordinates
        : []

  if (polygons.length > 0) {
    let totalSqMeters = 0
    for (const poly of polygons) {
      if (!poly || !poly.length) continue
      totalSqMeters += computeRingAreaSqMeters(poly[0])
      for (let h = 1; h < poly.length; h++) {
        totalSqMeters -= computeRingAreaSqMeters(poly[h])
      }
    }
    const acres = totalSqMeters / 4046.8564224
    if (acres > 0) {
      return `${acres.toFixed(2)} acres`
    }
  }

  return null
}

export function getParcelCoordinatesBounds(feature) {
  const geom = feature?.geometry
  if (!geom) return null

  const rings =
    geom.type === 'Polygon'
      ? geom.coordinates
      : geom.type === 'MultiPolygon'
        ? geom.coordinates.flat(1)
        : []

  const coords = rings.flat(1)
  if (!coords.length) return null

  let minLng = coords[0][0]
  let maxLng = coords[0][0]
  let minLat = coords[0][1]
  let maxLat = coords[0][1]

  for (const pt of coords) {
    if (pt[0] < minLng) minLng = pt[0]
    if (pt[0] > maxLng) maxLng = pt[0]
    if (pt[1] < minLat) minLat = pt[1]
    if (pt[1] > maxLat) maxLat = pt[1]
  }

  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ]
}

export function createGeoJSONCircle(center, radiusInMiles, points = 64) {
  const km = radiusInMiles * 1.609344
  const coords = []
  const distanceX = km / (111.32 * Math.cos((center[1] * Math.PI) / 180))
  const distanceY = km / 110.574

  for (let i = 0; i < points; i++) {
    const theta = (i / points) * (2 * Math.PI)
    const x = distanceX * Math.cos(theta)
    const y = distanceY * Math.sin(theta)
    coords.push([center[0] + x, center[1] + y])
  }
  coords.push(coords[0])

  return {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [coords],
    },
    properties: {
      radiusMiles: radiusInMiles,
    },
  }
}

export function metersToRadiusPixels(meters, centerLat = 40.5, zoom = 18.5) {
  const metersPerPixel = (156543.03392 * Math.cos((centerLat * Math.PI) / 180)) / Math.pow(2, zoom)
  return Math.max(3, Math.round(meters / metersPerPixel))
}
