import test from 'node:test'
import assert from 'node:assert/strict'
import {
  computeRingAreaSqMeters,
  calculateParcelAcreage,
  getParcelCoordinatesBounds,
  createGeoJSONCircle,
  metersToRadiusPixels,
} from '../src/utils/geo.js'

test('computeRingAreaSqMeters calculates correct area for polygon ring', () => {
  // A small ~100m square in Pennsylvania (~40.0 N, -75.0 W)
  // ~0.001 deg lon is ~85.3m, ~0.001 deg lat is ~111m
  const ring = [
    [-75.0, 40.0],
    [-75.0, 40.001],
    [-75.001, 40.001],
    [-75.001, 40.0],
    [-75.0, 40.0],
  ]
  const area = computeRingAreaSqMeters(ring)
  assert.ok(area > 8000 && area < 11000, `Area ${area} should be around ~9470 sq meters`)
})

test('computeRingAreaSqMeters returns 0 for empty or invalid ring', () => {
  assert.equal(computeRingAreaSqMeters(null), 0)
  assert.equal(computeRingAreaSqMeters([]), 0)
  assert.equal(computeRingAreaSqMeters([[-75.0, 40.0]]), 0)
})

test('calculateParcelAcreage uses properties.ACRES if provided', () => {
  const feat = { properties: { ACRES: 2.456 } }
  assert.equal(calculateParcelAcreage(feat), '2.46 acres')
})

test('calculateParcelAcreage calculates acreage from geometry if no properties', () => {
  const feat = {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'Polygon',
      coordinates: [
        [
          [-75.0, 40.0],
          [-75.0, 40.001],
          [-75.001, 40.001],
          [-75.001, 40.0],
          [-75.0, 40.0],
        ],
      ],
    },
  }
  const acreage = calculateParcelAcreage(feat)
  assert.ok(acreage && acreage.endsWith(' acres'))
})

test('getParcelCoordinatesBounds computes bounding box [[minLng, minLat], [maxLng, maxLat]]', () => {
  const feat = {
    geometry: {
      type: 'Polygon',
      coordinates: [
        [
          [-75.5, 40.1],
          [-75.4, 40.1],
          [-75.4, 40.2],
          [-75.5, 40.2],
          [-75.5, 40.1],
        ],
      ],
    },
  }
  const bounds = getParcelCoordinatesBounds(feat)
  assert.deepEqual(bounds, [
    [-75.5, 40.1],
    [-75.4, 40.2],
  ])
})

test('createGeoJSONCircle generates valid closed polygon feature', () => {
  const circle = createGeoJSONCircle([-75.5, 40.0], 0.5, 32)
  assert.equal(circle.type, 'Feature')
  assert.equal(circle.geometry.type, 'Polygon')
  const ring = circle.geometry.coordinates[0]
  assert.equal(ring.length, 33) // 32 points + closing point
  assert.deepEqual(ring[0], ring[ring.length - 1])
  assert.equal(circle.properties.radiusMiles, 0.5)
})

test('metersToRadiusPixels produces scaled pixel radius', () => {
  const px = metersToRadiusPixels(10, 40.0, 18)
  assert.ok(px >= 3)
  const pxLarger = metersToRadiusPixels(20, 40.0, 18)
  assert.ok(pxLarger > px)
})
