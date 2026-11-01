import test from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'
import { useSatelliteImagery } from '../src/composables/useSatelliteImagery.js'

test('useSatelliteImagery manages active source, opacity, and wayback epochs', () => {
  const mapRef = ref(null)
  let changedSource = null
  let changedVisibility = null

  const {
    isSatellitePanelExpanded,
    activeSourceId,
    activeOpacity,
    sources,
    getActiveSource,
    getActiveTileUrl,
    getActiveCaptureDate,
    selectSource,
    setOpacity,
    selectWaybackEpoch,
    toggleVisibility,
    toggleExpand,
  } = useSatelliteImagery(mapRef, {
    token: 'test_token',
    onSourceChange: (s) => {
      changedSource = s
    },
    onVisibilityChange: (v) => {
      changedVisibility = v
    },
  })

  // 1. Initial defaults (expanded by default so user sees imagery options immediately)
  assert.equal(isSatellitePanelExpanded.value, true)
  assert.equal(activeSourceId.value, 'mapbox')
  assert.equal(activeOpacity.value, 1.0)
  assert.equal(getActiveSource().id, 'mapbox')
  assert.ok(getActiveTileUrl().includes('mapbox/satellite-v9'))
  assert.equal(getActiveCaptureDate('Jun 11, 2025'), 'Jun 11, 2025')

  // 2. Expand/collapse
  toggleExpand()
  assert.equal(isSatellitePanelExpanded.value, false)

  // 3. Select different source (NAIP)
  selectSource('naip')
  assert.equal(activeSourceId.value, 'naip')
  assert.equal(changedSource.id, 'naip')
  assert.ok(getActiveTileUrl().includes('collections/naip'))
  assert.equal(getActiveCaptureDate(), 'Apr 29, 2022')

  // 4. Set opacity
  setOpacity(0.5)
  assert.equal(activeOpacity.value, 0.5)

  // 5. Select Esri Wayback and switch epochs
  selectSource('esri-wayback')
  assert.equal(activeSourceId.value, 'esri-wayback')
  assert.ok(getActiveTileUrl().includes('20512'))
  assert.equal(getActiveCaptureDate(), 'Oct 23, 2025')

  selectWaybackEpoch(3) // 2023 (Jun)
  assert.ok(getActiveTileUrl().includes('25982'))
  assert.equal(getActiveCaptureDate(), 'Jun 13, 2023')

  selectSource('pema-leafoff')
  assert.equal(getActiveCaptureDate(), 'Spring 2018 (Leaf-Off)')

  // 6. Visibility toggle
  toggleVisibility(false)
  assert.equal(changedVisibility, false)
  toggleVisibility(true)
  assert.equal(changedVisibility, true)
})
