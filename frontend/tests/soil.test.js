import test from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'

import { useSoilSurvey } from '../src/composables/useSoilSurvey.js'
import { fetchSoilSurvey } from '../src/api/propertyApi.js'

test('useSoilSurvey initializes with empty state and collapsed panel', () => {
  const mapRef = ref(null)
  const { soilSurveyData, soilLoading, soilError, selectedSoilSymbol, isPanelExpanded } =
    useSoilSurvey(mapRef)

  assert.equal(soilSurveyData.value, null)
  assert.equal(soilLoading.value, false)
  assert.equal(soilError.value, '')
  assert.equal(selectedSoilSymbol.value, null)
  assert.equal(isPanelExpanded.value, false)
})

test('useSoilSurvey renders layers and centered symbol markers on map', () => {
  const sources = new Map()
  const layers = new Map()
  const eventListeners = new Map()

  const fakeMapInstance = {
    isStyleLoaded: () => true,
    getSource: (id) => sources.get(id),
    addSource: (id, config) => sources.set(id, { ...config, setData: (d) => (config.data = d) }),
    getLayer: (id) => layers.get(id),
    addLayer: (config, beforeId) => layers.set(config.id, { ...config, beforeId }),
    setLayoutProperty: (id, prop, val) => {
      if (layers.has(id)) layers.get(id).layout[prop] = val
    },
    on: (evt, layerId, handler) => {
      const key = `${evt}:${layerId || ''}`
      eventListeners.set(key, handler)
    },
    getCanvas: () => ({ style: {} }),
    getZoom: () => 18,
    flyTo: (opts) => {
      fakeMapInstance.lastFlyTo = opts
    },
  }

  const mapRef = ref(fakeMapInstance)

  class FakePopup {
    constructor(opts) {
      this.opts = opts
      this._open = false
      this._html = ''
    }
    setLngLat(coords) {
      this.coords = coords
      return this
    }
    setHTML(html) {
      this._html = html
      return this
    }
    addTo(map) {
      this._open = true
      return this
    }
    isOpen() {
      return this._open
    }
    remove() {
      this._open = false
    }
  }

  class FakeMarker {
    constructor(opts) {
      this.element = opts.element
      this.anchor = opts.anchor
      this.coords = null
      this._popup = null
    }
    setLngLat(coords) {
      this.coords = coords
      return this
    }
    setPopup(popup) {
      this._popup = popup
      return this
    }
    getPopup() {
      return this._popup
    }
    togglePopup() {
      if (this._popup) {
        this._popup._open = !this._popup._open
      }
    }
    getElement() {
      return this.element
    }
    addTo(map) {
      return this
    }
    remove() {
      this.removed = true
    }
  }

  const fakeDoc = {
    createElement: (tag) => {
      const el = {
        tagName: tag,
        className: '',
        style: {
          display: 'flex',
          setProperty: (k, v) => (el.style[k] = v),
        },
        attributes: {},
        setAttribute: (k, v) => (el.attributes[k] = v),
        getAttribute: (k) => el.attributes[k],
        children: [],
        appendChild: (child) => el.children.push(child),
        addEventListener: (evt, fn) => {
          el[`on_${evt}`] = fn
        },
      }
      return el
    },
  }

  let layerVisible = false
  let setLayerCalls = []
  const {
    soilSurveyData,
    soilMarkers,
    isPanelExpanded,
    togglePanel,
    renderSoilOnMap,
    syncWithLayerToggle,
    focusOnSoilUnit,
    cleanupSoilMarkers,
  } = useSoilSurvey(mapRef, {
    isLayerVisible: (id) => (id === 'soil-survey-layer' ? layerVisible : false),
    setLayerVisibility: (id, visible) => {
      setLayerCalls.push({ id, visible })
      layerVisible = visible
    },
    mapboxLib: { Marker: FakeMarker, Popup: FakePopup },
    doc: fakeDoc,
  })

  const mockData = {
    summary: [
      {
        mukey: '543135',
        musym: 'DbB',
        muname: 'Duffield silt loam, 3 to 8 percent slopes',
        percentage: 50.1,
        color: '#c28b5e',
      },
      {
        mukey: '543212',
        musym: 'WaC',
        muname: 'Washington silt loam, 8 to 15 percent slopes',
        percentage: 30.4,
        color: '#8b7355',
      },
    ],
    geojson: {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          id: 'soil-DbB',
          properties: { musym: 'DbB', muname: 'Duffield silt loam', percentage: 50.1, color: '#c28b5e' },
          geometry: { type: 'Polygon', coordinates: [] },
        },
      ],
    },
    labelsGeojson: {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { musym: 'DbB', muname: 'Duffield silt loam', percentage: 50.1, color: '#c28b5e' },
          geometry: { type: 'Point', coordinates: [-75.5568, 40.6315] },
        },
        {
          type: 'Feature',
          properties: { musym: 'WaC', muname: 'Washington silt loam', percentage: 30.4, color: '#8b7355' },
          geometry: { type: 'Point', coordinates: [-75.5562, 40.6318] },
        },
      ],
    },
  }

  // 1. Initially rendered when layerVisible is false (hidden until clicked)
  renderSoilOnMap(mockData)

  assert.ok(sources.has('soil-survey-data'))
  assert.ok(layers.has('soil-survey-fill'))
  assert.ok(layers.has('soil-survey-outline'))
  assert.equal(layers.get('soil-survey-fill').layout.visibility, 'none')
  assert.equal(layers.get('soil-survey-outline').layout.visibility, 'none')

  // Centered markers were created but hidden initially
  assert.equal(soilMarkers.length, 2)
  assert.equal(soilMarkers[0].anchor, 'center')
  assert.deepEqual(soilMarkers[0].coords, [-75.5568, 40.6315])
  assert.equal(soilMarkers[0].getElement().getAttribute('data-symbol'), 'DbB')
  assert.equal(soilMarkers[0].getElement().style.display, 'none')

  // 2. User clicks the panel header -> togglePanel() expands panel and shows layer
  assert.equal(isPanelExpanded.value, false)
  togglePanel()
  assert.equal(isPanelExpanded.value, true)
  assert.equal(setLayerCalls.length, 1)
  assert.deepEqual(setLayerCalls[0], { id: 'soil-survey-layer', visible: true })
  assert.equal(soilMarkers[0].getElement().style.display, '')
  assert.equal(layers.get('soil-survey-fill').layout.visibility, 'visible')

  // 3. User clicks map layer checkbox to turn it off -> syncWithLayerToggle(false)
  layerVisible = false
  syncWithLayerToggle(false)
  assert.equal(isPanelExpanded.value, false)
  assert.equal(soilMarkers[0].getElement().style.display, 'none')
  assert.equal(layers.get('soil-survey-fill').layout.visibility, 'none')

  // 4. User clicks map layer checkbox to turn it on -> syncWithLayerToggle(true)
  layerVisible = true
  syncWithLayerToggle(true)
  assert.equal(isPanelExpanded.value, true)
  assert.equal(soilMarkers[0].getElement().style.display, '')
  assert.equal(layers.get('soil-survey-fill').layout.visibility, 'visible')

  // 5. Test focusing on a soil unit
  soilSurveyData.value = mockData
  focusOnSoilUnit(mockData.summary[1]) // WaC
  assert.ok(fakeMapInstance.lastFlyTo)
  assert.deepEqual(fakeMapInstance.lastFlyTo.center, [-75.5562, 40.6318])

  // 6. Test cleanup
  cleanupSoilMarkers()
  assert.equal(soilMarkers.length, 0)
})

test('fetchSoilSurvey queries /api/soil-survey endpoint', async () => {
  let calledUrl = ''
  globalThis.fetch = async (url) => {
    calledUrl = url
    return {
      ok: true,
      json: async () => ({
        summary: [{ musym: 'DbB', muname: 'Duffield silt loam', percentage: 100 }],
      }),
    }
  }

  const result = await fetchSoilSurvey()
  assert.equal(calledUrl, '/api/soil-survey')
  assert.equal(result.summary[0].musym, 'DbB')
})
