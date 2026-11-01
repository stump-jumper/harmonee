import test from 'node:test'
import assert from 'node:assert/strict'
import { fetchSatelliteLayers } from '../src/api/propertyApi.js'

test('fetchSatelliteLayers queries /api/satellite-layers with coordinates', async () => {
  let calledUrl = ''
  globalThis.fetch = async (url) => {
    calledUrl = url
    return {
      ok: true,
      json: async () => ({
        layers: [
          { id: 'satellite-naip', name: 'USDA NAIP (Natural Color)' },
          { id: 'satellite-naip-cir', name: 'USDA NAIP Color-Infrared (CIR)' },
          { id: 'satellite-pema-leafoff', name: 'PEMA Leaf-Off Aerial (PA State)' },
          { id: 'satellite-lidar-hillshade', name: 'LiDAR Micro-Hillshade (PAMAP)' },
          { id: 'satellite-esri-wayback', name: 'Esri World Imagery Wayback' },
        ],
      }),
    }
  }

  const result = await fetchSatelliteLayers(40.631667, -75.556515)
  assert.equal(
    calledUrl,
    '/api/satellite-layers?lat=40.631667&lon=-75.556515'
  )
  assert.equal(result.layers.length, 5)
  assert.equal(result.layers[0].id, 'satellite-naip')
})
