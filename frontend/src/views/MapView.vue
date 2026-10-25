<script setup>
import { ref, computed, watch, toRaw, onMounted, onBeforeUnmount } from 'vue'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

const currentAddress = ref('')
const captureDate = ref('')
const ecoregions = ref(null)
const birdOfTheDay = ref(null)
const keystonePlants = ref(null)
const habitatSegmentation = ref(null)
const isSegmenting = ref(false)
const showBirdModal = ref(false)
const parcelFeature = ref(null)
const mapElement = ref(null)
const errorMessage = ref('')
let mapInstance = null

const token = import.meta.env.VITE_MAPBOX_TOKEN

function computeRingAreaSqMeters(ring) {
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

const parcelAcreage = computed(() => {
  const feat = parcelFeature.value
  if (!feat) return null

  const props = feat.properties || {}
  if (props.ACRES && !isNaN(Number(props.ACRES))) {
    return `${Number(props.ACRES).toFixed(2)} acres`
  }

  if (props.Shape_Area && !isNaN(Number(props.Shape_Area)) && Number(props.Shape_Area) > 0) {
    const acres = Number(props.Shape_Area) / 43560
    return `${acres.toFixed(2)} acres`
  }

  // Calculate geodesic area across all polygons in Polygon or MultiPolygon (WGS84)
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
      // Exterior ring minus any interior hole rings
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
})

// Layer system registry
// Base layer (Satellite Imagery) is fixed/locked (`toggleable: false`).
// Overlay layers can be toggled on/off by the user.
const layers = ref([
  {
    id: 'satellite-base',
    name: 'Satellite Imagery',
    type: 'base',
    visible: true,
    toggleable: false,
    color: '#6ee7b7',
    mapLayerIds: ['satellite-layer'],
  },
  {
    id: 'property-boundary',
    name: 'Property Boundary',
    type: 'overlay',
    visible: true,
    toggleable: true,
    color: '#f2cc8f',
    mapLayerIds: ['parcel-boundary-fill', 'parcel-boundary-outline'],
  },
])

const BRUSH_CLASSES = [
  { id: 'tree_canopy', name: 'Tree Canopy', color: '#15803d', icon: '🌳' },
  { id: 'low_vegetation', name: 'Low Vegetation', color: '#4ade80', icon: '🌱' },
  { id: 'impervious_surfaces', name: 'Impervious Surfaces', color: '#94a3af', icon: '🏠' },
  { id: 'water', name: 'Water', color: '#38bdf8', icon: '💧' },
  { id: 'barren', name: 'Barren', color: '#d97706', icon: '🏜️' },
]

const isPaintMode = ref(false)
const activeBrushClass = ref('tree_canopy')
const brushSizeMeters = ref(6.0)
const strokes = ref([])
const isDrawing = ref(false)
const currentStroke = ref(null)

const isMouseOnMap = ref(false)
const cursorPos = ref({ x: -1000, y: -1000 })
const brushDiameterPx = ref(20)

const activeBrushColor = computed(() => {
  const b = BRUSH_CLASSES.find((c) => c.id === activeBrushClass.value)
  return b ? b.color : '#52b788'
})

function updateBrushDiameter() {
  if (!mapInstance) return
  const center = mapInstance.getCenter()
  const centerLat = center ? center.lat : 40.5
  const zoom = mapInstance.getZoom() || 18.5
  const metersPerPixel = (156543.03392 * Math.cos((centerLat * Math.PI) / 180)) / Math.pow(2, zoom)
  const radPx = Math.max(3, Math.round(brushSizeMeters.value / metersPerPixel))
  brushDiameterPx.value = radPx * 2
}

watch(brushSizeMeters, () => {
  updateBrushDiameter()
})

function handleMapMouseMove(e) {
  if (!isPaintMode.value) return
  isMouseOnMap.value = true
  const rect = mapElement.value?.getBoundingClientRect()
  if (rect) {
    cursorPos.value = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    }
  }
}

function handleMapMouseLeave() {
  isMouseOnMap.value = false
}

function updatePaintStrokesSource() {
  if (!mapInstance || !mapInstance.getSource('user-paint-strokes')) return

  // The paint strokes disappear when not in paint mode so the clean segmented boundaries are visible
  if (!isPaintMode.value) {
    mapInstance.getSource('user-paint-strokes').setData({
      type: 'FeatureCollection',
      features: [],
    })
    return
  }

  const center = mapInstance.getCenter()
  const centerLat = center ? center.lat : 40.5
  const zoom = mapInstance.getZoom() || 18.5
  const metersPerPixel = (156543.03392 * Math.cos((centerLat * Math.PI) / 180)) / Math.pow(2, zoom)

  const allStrokes = currentStroke.value
    ? [...strokes.value, currentStroke.value]
    : strokes.value
  const features = []

  for (const s of allStrokes) {
    const radM = s.radiusMeters || 6.0
    const radPx = Math.max(3, Math.round(radM / metersPerPixel))
    const widthPx = radPx * 2

    for (const pt of s.coordinates) {
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: pt },
        properties: { color: s.color, radiusPx: radPx },
      })
    }

    if (s.coordinates.length >= 2) {
      features.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: s.coordinates },
        properties: { color: s.color, widthPx: widthPx },
      })
    }
  }

  mapInstance.getSource('user-paint-strokes').setData({
    type: 'FeatureCollection',
    features,
  })
}

function onMapMouseDown(e) {
  if (!isPaintMode.value || !mapInstance) return
  if (e.originalEvent && e.originalEvent.button !== 0) return // only left click
  isDrawing.value = true
  const coords = [e.lngLat.lng, e.lngLat.lat]
  const brush = BRUSH_CLASSES.find((c) => c.id === activeBrushClass.value) || BRUSH_CLASSES[0]

  currentStroke.value = {
    id: Date.now(),
    categoryId: brush.id,
    color: brush.color,
    radiusMeters: brushSizeMeters.value,
    coordinates: [coords],
  }
  updatePaintStrokesSource()
}

function onMapMouseMove(e) {
  if (!isPaintMode.value || !isDrawing.value || !currentStroke.value) return
  const coords = [e.lngLat.lng, e.lngLat.lat]
  const last = currentStroke.value.coordinates[currentStroke.value.coordinates.length - 1]
  if (
    !last ||
    Math.abs(coords[0] - last[0]) > 0.000003 ||
    Math.abs(coords[1] - last[1]) > 0.000003
  ) {
    currentStroke.value.coordinates.push(coords)
    updatePaintStrokesSource()
  }
}

function onMapMouseUp() {
  if (!isPaintMode.value || !isDrawing.value) return
  isDrawing.value = false
  if (currentStroke.value && currentStroke.value.coordinates.length > 0) {
    strokes.value.push(currentStroke.value)
    currentStroke.value = null
    updatePaintStrokesSource()
  }
}

function togglePaintMode() {
  isPaintMode.value = !isPaintMode.value
  if (!mapInstance) return

  if (isPaintMode.value) {
    mapInstance.dragPan.disable()
    const canvas = mapInstance.getCanvas()
    if (canvas) canvas.style.cursor = 'none'
    updateBrushDiameter()
  } else {
    mapInstance.dragPan.enable()
    const canvas = mapInstance.getCanvas()
    if (canvas) canvas.style.cursor = ''
    isDrawing.value = false
    currentStroke.value = null
    isMouseOnMap.value = false
  }
  updatePaintStrokesSource()
}

function undoStroke() {
  strokes.value.pop()
  updatePaintStrokesSource()
}

function clearAllStrokes() {
  strokes.value = []
  currentStroke.value = null
  updatePaintStrokesSource()
}

async function triggerPaintSegmentation() {
  if (isSegmenting.value) return
  if (!strokes.value.length) {
    alert('Please paint at least one stroke on your parcel first to indicate a habitat class.')
    return
  }
  isSegmenting.value = true
  try {
    const res = await fetch('/api/segment/paint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strokes: strokes.value }),
    })
    if (res.ok) {
      const segData = await res.json()
      habitatSegmentation.value = segData
      registerHabitatLayers(segData)

      // Exit paint mode and ensure strokes disappear so only the clean segmentation is visible
      if (isPaintMode.value) {
        togglePaintMode()
      } else {
        updatePaintStrokesSource()
      }
    }
  } catch (err) {
    console.error('Segmentation error:', err)
  } finally {
    isSegmenting.value = false
  }
}

function toggleLayer(layer) {
  if (!layer.toggleable) return
  layer.visible = !layer.visible
  if (!mapInstance) return

  const visibility = layer.visible ? 'visible' : 'none'
  for (const mapLayerId of layer.mapLayerIds) {
    if (mapInstance.getLayer(mapLayerId)) {
      mapInstance.setLayoutProperty(mapLayerId, 'visibility', visibility)
    }
  }
}

function registerHabitatLayers(segData) {
  const segLayers = segData?.layers || []
  // Keep base and property-boundary layers, replace habitat layers
  const coreLayers = layers.value.filter((l) => l.type !== 'habitat')
  const dynamicLayers = segLayers.map((seg) => ({
    id: seg.id,
    name: seg.name,
    type: 'habitat',
    visible: true,
    toggleable: true,
    color: seg.color,
    percentage: seg.percentage,
    feature: seg.feature,
    mapLayerIds: [`${seg.id}-fill`, `${seg.id}-outline`],
  }))
  layers.value = [...coreLayers, ...dynamicLayers]

  if (!mapInstance || !mapInstance.isStyleLoaded()) return

  // Clean up any stale habitat layers or sources from previous segmentations
  const activeHabitatIds = new Set(dynamicLayers.map((l) => l.id))
  const currentLayers = mapInstance.getStyle()?.layers || []
  for (const mLayer of currentLayers) {
    if (mLayer.id.startsWith('habitat-')) {
      const baseId = mLayer.id.replace(/-fill$|-outline$/, '')
      if (!activeHabitatIds.has(baseId)) {
        if (mapInstance.getLayer(mLayer.id)) mapInstance.removeLayer(mLayer.id)
        const srcId = `${baseId}-source`
        if (mapInstance.getSource(srcId)) mapInstance.removeSource(srcId)
      }
    }
  }

  const beforeId = mapInstance.getLayer('parcel-boundary-outline')
    ? 'parcel-boundary-outline'
    : undefined

  for (const hLayer of dynamicLayers) {
    const srcId = `${hLayer.id}-source`
    const fillId = `${hLayer.id}-fill`
    const outlineId = `${hLayer.id}-outline`
    const rawFeature = JSON.parse(JSON.stringify(toRaw(hLayer.feature)))

    if (mapInstance.getSource(srcId)) {
      mapInstance.getSource(srcId).setData(rawFeature)
    } else {
      mapInstance.addSource(srcId, {
        type: 'geojson',
        data: rawFeature,
      })
      mapInstance.addLayer(
        {
          id: fillId,
          type: 'fill',
          source: srcId,
          layout: { visibility: hLayer.visible ? 'visible' : 'none' },
          paint: {
            'fill-color': hLayer.color,
            'fill-opacity': 0.52,
          },
        },
        beforeId
      )
      mapInstance.addLayer(
        {
          id: outlineId,
          type: 'line',
          source: srcId,
          layout: {
            visibility: hLayer.visible ? 'visible' : 'none',
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': hLayer.color,
            'line-width': 1.5,
            'line-opacity': 0.9,
          },
        },
        beforeId
      )
    }
  }
}

function getParcelBounds(feature) {
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

  const bounds = new mapboxgl.LngLatBounds(coords[0], coords[0])
  for (const pt of coords) {
    bounds.extend(pt)
  }
  return bounds
}

async function refreshCaptureDate(lat, lon) {
  try {
    const res = await fetch(
      `/api/imagery-date?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`
    )
    if (res.ok) {
      const data = await res.json()
      if (data.captureDate) {
        captureDate.value = data.captureDate
      }
    }
  } catch {
    // Ignore metadata lookup error
  }
}

function handleKeydown(e) {
  if (e.key === 'Escape' && showBirdModal.value) {
    showBirdModal.value = false
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  let lat = null
  let lon = null

  try {
    const res = await fetch('/api/address')
    if (res.ok) {
      const data = await res.json()
      currentAddress.value = data.address || ''
      lat = data.lat
      lon = data.lon
      captureDate.value = data.captureDate || ''
      parcelFeature.value = data.parcel || null
      ecoregions.value = data.ecoregions || null
      birdOfTheDay.value = data.birdOfTheDay || null
      keystonePlants.value = data.keystonePlants || null
      habitatSegmentation.value = data.habitatSegmentation || null
      if (Array.isArray(data.paintStrokes) && data.paintStrokes.length > 0) {
        strokes.value = data.paintStrokes
      }
      if (data.habitatSegmentation) {
        registerHabitatLayers(data.habitatSegmentation)
      }
    }
  } catch {
    const local = localStorage.getItem('harmonee_address')
    if (local) currentAddress.value = local
  }

  if (!token) {
    errorMessage.value = 'Missing Mapbox access token (VITE_MAPBOX_TOKEN).'
    return
  }

  if (lat == null || lon == null) {
    errorMessage.value = 'Enter an address on the home page to view its satellite imagery.'
    return
  }

  if (!captureDate.value) {
    refreshCaptureDate(lat, lon)
  }

  const rawParcel = parcelFeature.value
    ? JSON.parse(JSON.stringify(toRaw(parcelFeature.value)))
    : null

  const boundaryLayerConfig = layers.value.find((l) => l.id === 'property-boundary')
  const initialVisibility = boundaryLayerConfig?.visible ? 'visible' : 'none'

  const styleSources = {
    'mapbox-satellite-tiles': {
      type: 'raster',
      tiles: [
        `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/512/{z}/{x}/{y}@2x?access_token=${token}`,
      ],
      tileSize: 512,
      maxzoom: 22,
    },
    'user-paint-strokes': {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    },
  }

  const styleLayers = [
    {
      id: 'satellite-layer',
      type: 'raster',
      source: 'mapbox-satellite-tiles',
      minzoom: 0,
      maxzoom: 22,
    },
  ]

  if (rawParcel) {
    styleSources['parcel-boundary'] = {
      type: 'geojson',
      data: rawParcel,
    }
    styleLayers.push(
      {
        id: 'parcel-boundary-fill',
        type: 'fill',
        source: 'parcel-boundary',
        layout: {
          visibility: initialVisibility,
        },
        paint: {
          'fill-color': '#f2cc8f',
          'fill-opacity': 0.14,
        },
      },
      {
        id: 'parcel-boundary-outline',
        type: 'line',
        source: 'parcel-boundary',
        layout: {
          visibility: initialVisibility,
          'line-join': 'round',
          'line-cap': 'round',
        },
        paint: {
          'line-color': '#f2cc8f',
          'line-width': 3,
        },
      }
    )
  }

  // Add paint stroke layers so user strokes are rendered on top of the satellite imagery
  styleLayers.push(
    {
      id: 'user-paint-strokes-lines',
      type: 'line',
      source: 'user-paint-strokes',
      layout: {
        'line-cap': 'round',
        'line-join': 'round',
      },
      paint: {
        'line-color': ['get', 'color'],
        'line-width': ['get', 'widthPx'],
        'line-opacity': 0.88,
      },
    },
    {
      id: 'user-paint-strokes-points',
      type: 'circle',
      source: 'user-paint-strokes',
      paint: {
        'circle-color': ['get', 'color'],
        'circle-radius': ['get', 'radiusPx'],
        'circle-opacity': 0.88,
      },
    }
  )

  mapboxgl.accessToken = token
  mapInstance = new mapboxgl.Map({
    container: mapElement.value,
    style: {
      version: 8,
      sources: styleSources,
      layers: styleLayers,
    },
    center: [lon, lat],
    zoom: 18.5,
    preserveDrawingBuffer: true,
    attributionControl: false,
  })

  mapInstance.addControl(new mapboxgl.NavigationControl(), 'bottom-right')
  mapInstance.addControl(new mapboxgl.FullscreenControl(), 'bottom-right')
  mapInstance.addControl(
    new mapboxgl.ScaleControl({ maxWidth: 120, unit: 'imperial' }),
    'bottom-left'
  )

  mapInstance.once('load', () => {
    mapInstance.resize()
    if (habitatSegmentation.value) {
      registerHabitatLayers(habitatSegmentation.value)
    }
    if (rawParcel) {
      const bounds = getParcelBounds(rawParcel)
      if (bounds) {
        mapInstance.fitBounds(bounds, {
          padding: 110,
          maxZoom: 18.5,
          duration: 0,
        })
      }
      if (strokes.value.length > 0) {
        updatePaintStrokesSource()
      }
    }
  })

  mapInstance.on('mousedown', onMapMouseDown)
  mapInstance.on('mousemove', onMapMouseMove)
  mapInstance.on('mouseup', onMapMouseUp)
  mapInstance.on('zoom', () => {
    updateBrushDiameter()
    updatePaintStrokesSource()
  })
  mapInstance.on('move', () => {
    updateBrushDiameter()
    updatePaintStrokesSource()
  })

  mapInstance.on('moveend', () => {
    const center = mapInstance.getCenter()
    refreshCaptureDate(center.lat, center.lng)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
})
</script>

<template>
  <section
    class="map-page"
    @mousemove="handleMapMouseMove"
    @mouseleave="handleMapMouseLeave"
  >
    <div class="map-sidebar-left">
      <div v-if="currentAddress" class="info-panel">
        <div class="panel-heading">Property Info</div>
        <div class="address-text">{{ currentAddress }}</div>
        <div v-if="parcelAcreage" class="acreage-text">
          Parcel Size: {{ parcelAcreage }}
        </div>
      </div>

      <div v-if="ecoregions" class="ecoregion-panel">
        <div class="panel-heading">Ecoregion Info</div>
        <ul class="ecoregion-list">
          <li v-if="ecoregions.level1" class="ecoregion-row">
            <span class="ecoregion-label">Level I:</span>
            <span class="ecoregion-value">{{ ecoregions.level1 }}</span>
          </li>
          <li v-if="ecoregions.level2" class="ecoregion-row">
            <span class="ecoregion-label">Level II:</span>
            <span class="ecoregion-value">{{ ecoregions.level2 }}</span>
          </li>
          <li v-if="ecoregions.level3" class="ecoregion-row">
            <span class="ecoregion-label">Level III:</span>
            <span class="ecoregion-value">{{ ecoregions.level3 }}</span>
          </li>
          <li v-if="ecoregions.level4" class="ecoregion-row">
            <span class="ecoregion-label">Level IV:</span>
            <span class="ecoregion-value">{{ ecoregions.level4 }}</span>
          </li>
        </ul>
        <p v-if="ecoregions.description" class="ecoregion-description">
          {{ ecoregions.description }}
        </p>
      </div>

      <div v-if="birdOfTheDay" class="bird-panel">
        <div class="panel-heading">Bird of the Day</div>
        <div class="bird-content">
          <button
            type="button"
            class="bird-image-frame"
            title="Click to view full Audubon illustration"
            @click="showBirdModal = true"
          >
            <img
              :src="birdOfTheDay.proxyImageUrl || birdOfTheDay.imageUrl"
              :alt="`${birdOfTheDay.commonName} — Audubon illustration`"
              class="bird-illustration"
            />
          </button>
          <div class="bird-details">
            <div class="bird-name">{{ birdOfTheDay.commonName }}</div>
            <div class="bird-scientific">{{ birdOfTheDay.scientificName }}</div>
            <div v-if="birdOfTheDay.plate" class="bird-plate">
              {{ birdOfTheDay.plate }} (J.J. Audubon)
            </div>
            <div v-if="birdOfTheDay.location" class="bird-sighting">
              Spotted nearby on {{ birdOfTheDay.source || 'eBird' }}: {{ birdOfTheDay.location }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="keystonePlants" class="keystone-panel">
        <div class="panel-heading">Keystone Native Plants</div>
        <div class="keystone-subtitle">
          Ranked by butterfly &amp; moth species supported
        </div>

        <div
          v-if="keystonePlants.treesAndShrubs?.length"
          class="keystone-group"
        >
          <div class="keystone-group-title">Top 3 Native Trees &amp; Shrubs</div>
          <ul class="keystone-list">
            <li
              v-for="(plant, idx) in keystonePlants.treesAndShrubs"
              :key="plant.genus"
              class="keystone-item"
            >
              <div class="keystone-row-top">
                <span class="keystone-name">
                  {{ idx + 1 }}. {{ plant.commonName }}
                  <span class="keystone-genus">({{ plant.genus }})</span>
                </span>
                <span class="keystone-count">{{ plant.lepidopteraCount }} spp.</span>
              </div>
              <div class="keystone-examples">{{ plant.exampleSpecies }}</div>
            </li>
          </ul>
        </div>

        <div
          v-if="keystonePlants.flowersAndGrasses?.length"
          class="keystone-group"
        >
          <div class="keystone-group-title">Top 3 Native Flowers &amp; Grasses</div>
          <ul class="keystone-list">
            <li
              v-for="(plant, idx) in keystonePlants.flowersAndGrasses"
              :key="plant.genus"
              class="keystone-item"
            >
              <div class="keystone-row-top">
                <span class="keystone-name">
                  {{ idx + 1 }}. {{ plant.commonName }}
                  <span class="keystone-genus">({{ plant.genus }})</span>
                </span>
                <span class="keystone-count">{{ plant.lepidopteraCount }} spp.</span>
              </div>
              <div class="keystone-examples">{{ plant.exampleSpecies }}</div>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div
      v-if="showBirdModal && birdOfTheDay"
      class="bird-modal-backdrop"
      @click="showBirdModal = false"
    >
      <div class="bird-modal" @click.stop>
        <div class="bird-modal-header">
          <div class="bird-modal-titles">
            <span class="bird-modal-name">{{ birdOfTheDay.commonName }}</span>
            <span class="bird-modal-scientific">{{ birdOfTheDay.scientificName }}</span>
          </div>
          <button
            type="button"
            class="bird-modal-close"
            aria-label="Close full image"
            @click="showBirdModal = false"
          >
            ✕
          </button>
        </div>
        <div class="bird-modal-image-wrap">
          <img
            :src="birdOfTheDay.proxyImageUrl || birdOfTheDay.imageUrl"
            :alt="`${birdOfTheDay.commonName} — Full Audubon illustration`"
            class="bird-modal-image"
          />
        </div>
        <div class="bird-modal-footer">
          <span v-if="birdOfTheDay.plate">{{ birdOfTheDay.plate }} — John James Audubon</span>
          <span v-if="birdOfTheDay.location">
            Spotted nearby on {{ birdOfTheDay.source || 'eBird' }}: {{ birdOfTheDay.location }}
          </span>
        </div>
      </div>
    </div>

    <div class="map-sidebar-right">
      <div class="layers-panel">
        <div class="panel-heading">Layers</div>
        <ul class="layers-list">
          <li v-for="layer in layers" :key="layer.id" class="layer-item">
            <label
              :class="['layer-row', { locked: !layer.toggleable }]"
              @click.prevent="layer.toggleable && toggleLayer(layer)"
            >
              <input
                v-if="layer.toggleable"
                type="checkbox"
                :checked="layer.visible"
                @change="toggleLayer(layer)"
                @click.stop
              />
              <span v-else class="base-indicator" title="Base layer (always active)"></span>
              <span
                class="layer-swatch"
                :style="{
                  borderColor: layer.color,
                  backgroundColor: layer.type !== 'overlay' ? layer.color : 'transparent',
                }"
              ></span>
              <span class="layer-name">{{ layer.name }}</span>
              <span v-if="!layer.toggleable" class="layer-tag">Base</span>
              <span v-else-if="layer.percentage != null" class="layer-tag">
                {{ layer.percentage }}%
              </span>
            </label>
          </li>
        </ul>

        <!-- User-driven Interactive Paint Segmentation Section -->
        <div v-if="parcelFeature" class="paint-controls-section">
          <div class="section-divider"></div>
          <button
            type="button"
            :class="['paint-toggle-btn', { active: isPaintMode }]"
            @click="togglePaintMode"
          >
            <span class="btn-icon">{{ isPaintMode ? '✕' : '🎨' }}</span>
            <span>{{ isPaintMode ? 'Exit Paint Mode' : 'Paint Habitat Seeds' }}</span>
          </button>

          <div v-if="strokes.length > 0" class="strokes-status-bar">
            <span class="strokes-badge">{{ strokes.length }} stroke{{ strokes.length === 1 ? '' : 's' }}</span>
            <div class="tool-btn-group">
              <button type="button" class="tool-btn-sm" title="Undo last stroke" @click="undoStroke">↩</button>
              <button type="button" class="tool-btn-sm" title="Clear all strokes" @click="clearAllStrokes">🗑</button>
            </div>
          </div>

          <button
            type="button"
            class="segment-btn"
            :disabled="isSegmenting || !strokes.length"
            @click="triggerPaintSegmentation"
          >
            <span v-if="isSegmenting">Segmenting from Paint...</span>
            <span v-else-if="strokes.length">🚀 Segment from Paint</span>
            <span v-else>Paint seeds to segment</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Floating Paint Toolbar -->
    <div v-if="isPaintMode" class="paint-floating-toolbar">
      <div class="toolbar-header">
        <div class="toolbar-title-wrap">
          <span class="toolbar-icon">🎨</span>
          <span class="toolbar-title">Paint Habitat Seeds</span>
        </div>
        <span class="toolbar-hint">Drag on the map to paint target habitat areas</span>
        <button type="button" class="toolbar-close-btn" title="Exit Paint Mode" @click="togglePaintMode">✕</button>
      </div>

      <div class="toolbar-palette">
        <button
          v-for="b in BRUSH_CLASSES"
          :key="b.id"
          type="button"
          :class="['palette-chip', { active: activeBrushClass === b.id }]"
          :style="{ '--chip-color': b.color }"
          @click="activeBrushClass = b.id"
        >
          <span class="chip-swatch" :style="{ backgroundColor: b.color }"></span>
          <span class="chip-icon">{{ b.icon }}</span>
          <span class="chip-name">{{ b.name }}</span>
        </button>
      </div>

      <div class="toolbar-footer">
        <div class="brush-size-group">
          <span class="size-label">Brush:</span>
          <button
            type="button"
            :class="['size-btn', { active: brushSizeMeters === 3.0 }]"
            @click="brushSizeMeters = 3.0"
          >
            S (3m)
          </button>
          <button
            type="button"
            :class="['size-btn', { active: brushSizeMeters === 6.0 }]"
            @click="brushSizeMeters = 6.0"
          >
            M (6m)
          </button>
          <button
            type="button"
            :class="['size-btn', { active: brushSizeMeters === 12.0 }]"
            @click="brushSizeMeters = 12.0"
          >
            L (12m)
          </button>
        </div>

        <div class="toolbar-actions">
          <button
            type="button"
            class="action-btn"
            :disabled="!strokes.length"
            title="Undo last stroke"
            @click="undoStroke"
          >
            ↩ Undo
          </button>
          <button
            type="button"
            class="action-btn"
            :disabled="!strokes.length"
            title="Clear all strokes"
            @click="clearAllStrokes"
          >
            🗑 Clear
          </button>
          <button
            type="button"
            class="action-btn-primary"
            :disabled="isSegmenting || !strokes.length"
            @click="triggerPaintSegmentation"
          >
            {{ isSegmenting ? 'Segmenting...' : '🚀 Segment Habitats' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="map-empty">
      <p>{{ errorMessage }}</p>
    </div>

    <div v-show="!errorMessage" ref="mapElement" class="satellite-map"></div>

    <!-- Real-time Brush Reticle Cursor (scaled accurately to map ground meters & zoom) -->
    <div
      v-if="isPaintMode && isMouseOnMap"
      class="brush-reticle-cursor"
      :style="{
        left: `${cursorPos.x}px`,
        top: `${cursorPos.y}px`,
        width: `${brushDiameterPx}px`,
        height: `${brushDiameterPx}px`,
        borderColor: activeBrushColor,
      }"
    >
      <span class="reticle-center-dot" :style="{ backgroundColor: activeBrushColor }"></span>
      <span class="reticle-size-pill">{{ brushSizeMeters }}m</span>
    </div>

    <div v-if="captureDate && !errorMessage" class="capture-date">
      Imagery captured: {{ captureDate }}
    </div>
  </section>
</template>

<style scoped>
.map-page {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
}

.map-sidebar-left {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  max-width: 340px;
  max-height: calc(100% - 54px);
  overflow-y: auto;
}

.map-sidebar-right {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

:deep(.mapboxgl-ctrl-bottom-right) {
  bottom: 38px;
  right: 4px;
}

.info-panel,
.layers-panel,
.ecoregion-panel,
.bird-panel,
.keystone-panel {
  padding: 0.65rem 0.85rem;
  background-color: rgba(30, 58, 47, 0.9);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
  text-align: left;
}

.layers-panel {
  width: 280px;
}

.panel-heading {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 0.4rem;
}

.address-text {
  font-size: 0.9rem;
  color: var(--text-cream);
  line-height: 1.35;
}

.acreage-text {
  margin-top: 0.35rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.ecoregion-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.ecoregion-row {
  font-size: 0.85rem;
  line-height: 1.35;
}

.ecoregion-label {
  color: var(--text-muted);
  font-weight: 600;
  margin-right: 0.35rem;
}

.ecoregion-value {
  color: var(--text-cream);
}

.ecoregion-description {
  margin: 0.55rem 0 0 0;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(61, 102, 86, 0.55);
  font-size: 0.8rem;
  line-height: 1.4;
  color: var(--text-muted);
}

.bird-content {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
}

.bird-image-frame {
  width: 96px;
  height: 116px;
  flex-shrink: 0;
  background-color: var(--text-cream);
  border: 1px solid var(--border-sage);
  border-radius: 4px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: zoom-in;
  transition: border-color 0.15s ease;
}

.bird-image-frame:hover {
  border-color: var(--text-cream);
}

.bird-illustration {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 46%;
  transform: scale(1.65);
  transition: transform 0.2s ease;
  display: block;
}

.bird-image-frame:hover .bird-illustration {
  transform: scale(1.78);
}

.bird-details {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 0;
}

.bird-name {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-cream);
  line-height: 1.25;
}

.bird-scientific {
  font-size: 0.78rem;
  font-style: italic;
  color: var(--text-muted);
}

.bird-plate {
  margin-top: 0.15rem;
  font-size: 0.74rem;
  color: var(--text-cream);
  opacity: 0.9;
  line-height: 1.3;
}

.bird-sighting {
  margin-top: 0.2rem;
  font-size: 0.74rem;
  color: var(--text-muted);
  line-height: 1.3;
}

.bird-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  background-color: rgba(15, 30, 24, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.bird-modal {
  background-color: var(--bg-forest);
  border: 1px solid var(--border-sage);
  border-radius: 8px;
  max-width: min(760px, 92vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 0.9rem 1.1rem;
  gap: 0.75rem;
}

.bird-modal-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
}

.bird-modal-titles {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.bird-modal-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-cream);
}

.bird-modal-scientific {
  font-size: 0.9rem;
  font-style: italic;
  color: var(--text-muted);
}

.bird-modal-close {
  background: transparent;
  border: 1px solid var(--border-sage);
  color: var(--text-cream);
  border-radius: 4px;
  width: 28px;
  height: 28px;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.bird-modal-close:hover {
  background-color: var(--bg-forest-light);
  border-color: var(--text-cream);
}

.bird-modal-image-wrap {
  background-color: var(--text-cream);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.bird-modal-image {
  max-width: 100%;
  max-height: 72vh;
  object-fit: contain;
  display: block;
}

.bird-modal-footer {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.keystone-subtitle {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: -0.15rem;
  margin-bottom: 0.55rem;
}

.keystone-group + .keystone-group {
  margin-top: 0.65rem;
  padding-top: 0.55rem;
  border-top: 1px solid rgba(61, 102, 86, 0.55);
}

.keystone-group-title {
  font-size: 0.74rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-cream);
  margin-bottom: 0.35rem;
}

.keystone-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.42rem;
}

.keystone-item {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.keystone-row-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.45rem;
}

.keystone-name {
  font-size: 0.83rem;
  font-weight: 600;
  color: var(--text-cream);
  line-height: 1.25;
}

.keystone-genus {
  font-weight: 400;
  font-style: italic;
  color: var(--text-muted);
  font-size: 0.77rem;
}

.keystone-count {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: var(--bg-forest-light);
  border: 1px solid var(--border-sage);
  border-radius: 3px;
  padding: 0.05rem 0.35rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.keystone-examples {
  font-size: 0.74rem;
  color: var(--text-muted);
  line-height: 1.3;
  padding-left: 0.85rem;
}

.layers-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.layer-item {
  margin: 0;
}

.layer-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
  color: var(--text-cream);
  cursor: pointer;
  user-select: none;
  padding: 0.2rem 0;
}

.layer-row.locked {
  cursor: default;
  opacity: 0.9;
}

.base-indicator {
  width: 14px;
  height: 14px;
  display: inline-block;
  border-radius: 3px;
  background-color: rgba(200, 214, 206, 0.25);
  border: 1px solid var(--border-sage);
}

.layer-swatch {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  border: 2px solid;
  display: inline-block;
  flex-shrink: 0;
}

.layer-name {
  flex: 1;
}

.layer-tag {
  font-size: 0.7rem;
  color: var(--text-muted);
  padding: 0.05rem 0.35rem;
  border: 1px solid var(--border-sage);
  border-radius: 3px;
}

.segment-btn {
  margin-top: 0.55rem;
  width: 100%;
  padding: 0.4rem 0.6rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: var(--bg-forest-light);
  border: 1px solid var(--border-sage);
  border-radius: 4px;
  cursor: pointer;
}

.segment-btn:hover:not(:disabled) {
  border-color: var(--text-cream);
}

.segment-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.section-divider {
  height: 1px;
  background-color: var(--border-sage);
  margin: 0.6rem 0 0.5rem 0;
  opacity: 0.6;
}

.paint-toggle-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.45rem 0.6rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: var(--bg-forest-light);
  border: 1px solid var(--border-sage);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.paint-toggle-btn:hover {
  border-color: var(--color-leaf-bright);
}

.paint-toggle-btn.active {
  background-color: #2d6a4f;
  border-color: #52b788;
  color: #fff;
  box-shadow: 0 0 10px rgba(82, 183, 136, 0.4);
}

.strokes-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.4rem;
  padding: 0.2rem 0.3rem;
  font-size: 0.74rem;
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.strokes-badge {
  color: #a7f3d0;
  font-weight: 600;
}

.tool-btn-group {
  display: flex;
  gap: 0.3rem;
}

.tool-btn-sm {
  background: none;
  border: 1px solid var(--border-sage);
  color: var(--text-cream);
  border-radius: 3px;
  font-size: 0.72rem;
  padding: 0.1rem 0.35rem;
  cursor: pointer;
}

.tool-btn-sm:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-color: var(--text-cream);
}

/* Floating Paint Toolbar */
.paint-floating-toolbar {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background-color: rgba(20, 36, 29, 0.94);
  backdrop-filter: blur(12px);
  border: 1px solid #52b788;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 16px rgba(82, 183, 136, 0.25);
  max-width: 620px;
  width: calc(100% - 28px);
}

.toolbar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.toolbar-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.toolbar-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #e8f5e9;
}

.toolbar-hint {
  font-size: 0.74rem;
  color: var(--text-muted);
  flex: 1;
  text-align: center;
}

.toolbar-close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.95rem;
  cursor: pointer;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}

.toolbar-close-btn:hover {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.1);
}

.toolbar-palette {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.palette-chip {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.55rem;
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: rgba(0, 0, 0, 0.35);
  border: 1.5px solid rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.palette-chip:hover {
  border-color: var(--chip-color);
  background-color: rgba(0, 0, 0, 0.5);
}

.palette-chip.active {
  border-color: var(--chip-color);
  background-color: rgba(255, 255, 255, 0.12);
  box-shadow: 0 0 10px var(--chip-color);
  color: #fff;
}

.chip-swatch {
  width: 9px;
  height: 9px;
  border-radius: 2px;
  display: inline-block;
}

.chip-icon {
  font-size: 0.85rem;
}

.toolbar-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  padding-top: 0.3rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.brush-size-group {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.size-label {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-right: 0.15rem;
}

.size-btn {
  padding: 0.15rem 0.45rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-sage);
  border-radius: 3px;
  cursor: pointer;
}

.size-btn.active {
  background-color: #2d6a4f;
  border-color: #52b788;
  color: #fff;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.action-btn {
  padding: 0.25rem 0.55rem;
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-sage);
  border-radius: 4px;
  cursor: pointer;
}

.action-btn:hover:not(:disabled) {
  border-color: var(--text-cream);
}

.action-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.action-btn-primary {
  padding: 0.3rem 0.8rem;
  font-size: 0.78rem;
  font-weight: 700;
  color: #fff;
  background-color: #2d6a4f;
  border: 1px solid #52b788;
  border-radius: 4px;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(82, 183, 136, 0.3);
  transition: all 0.15s ease;
}

.action-btn-primary:hover:not(:disabled) {
  background-color: #1b4332;
  border-color: #74c69d;
  box-shadow: 0 0 14px rgba(116, 198, 157, 0.5);
}

.action-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.satellite-map {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.capture-date {
  position: absolute;
  bottom: 12px;
  right: 12px;
  z-index: 5;
  padding: 0.25rem 0.6rem;
  font-size: 0.75rem;
  color: var(--text-cream);
  background-color: rgba(30, 58, 47, 0.85);
  border: 1px solid var(--border-sage);
  border-radius: 4px;
  pointer-events: none;
}

.map-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  padding: 2rem;
}

/* Brush Reticle Cursor */
.brush-reticle-cursor {
  position: absolute;
  pointer-events: none;
  border-radius: 50%;
  border: 2px solid;
  transform: translate(-50%, -50%);
  z-index: 50;
  background-color: rgba(255, 255, 255, 0.12);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.7), 0 0 14px rgba(0, 0, 0, 0.4);
  will-change: left, top, width, height;
}

.reticle-center-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.9);
}

.reticle-size-pill {
  position: absolute;
  top: -19px;
  left: 50%;
  transform: translateX(-50%);
  background-color: rgba(18, 32, 25, 0.9);
  color: #e8f5e9;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  padding: 0 6px;
  font-size: 10px;
  font-weight: 600;
  line-height: 15px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
}
</style>
