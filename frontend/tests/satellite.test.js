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
          { id: 'satellite-sentinel2', name: 'Sentinel-2 (Copernicus)' },
          { id: 'satellite-landsat', name: 'Landsat 9 (USGS/NASA)' },
          { id: 'satellite-naip', name: 'USDA NAIP Aerial' },
          { id: 'satellite-usgs-tnm', name: 'USGS The National Map' },
        ],
      }),
    }
  }

  const result = await fetchSatelliteLayers(40.631667, -75.556515)
  assert.equal(
    calledUrl,
    '/api/satellite-layers?lat=40.631667&lon=-75.556515'
  )
  assert.equal(result.layers.length, 4)
  assert.equal(result.layers[0].id, 'satellite-sentinel2')
})
