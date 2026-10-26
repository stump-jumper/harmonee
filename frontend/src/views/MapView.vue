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

// eBird Sightings State
const ebirdSightingsData = ref(null)
const ebirdLoading = ref(false)
const ebirdActiveTab = ref('recent') // 'recent' | 'closest' | 'common'
const selectedSightingId = ref(null)
const isEbirdCardExpanded = ref(false)
let ebirdMarkers = []
let currentOpenEbirdPopup = null

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
  {
    id: 'habitat-objects-layer',
    name: 'Habitat Objects',
    type: 'overlay',
    visible: true,
    toggleable: true,
    color: '#f59e0b',
    mapLayerIds: [],
  },
  {
    id: 'ebird-sightings-layer',
    name: 'eBird Sightings (1.0 mi)',
    type: 'overlay',
    visible: false,
    toggleable: true,
    color: '#38bdf8',
    mapLayerIds: ['ebird-radius-fill', 'ebird-radius-outline'],
  },
])

const HABITAT_OBJECT_TYPES = [
  {
    id: 'bird_feeder',
    name: 'Bird Feeder',
    icon: '🥣',
    color: '#f59e0b',
    description: 'Supplemental food source for seed, suet, or nectar eating birds',
    defaultVariant: 'Tube / Seed Feeder',
    variants: [
      'Tube / Seed Feeder',
      'Suet Cage Feeder',
      'Hummingbird / Nectar Feeder',
      'Hopper Feeder',
      'Platform / Tray Feeder',
      'Thistle / Finch Feeder',
    ],
  },
  {
    id: 'bird_house',
    name: 'Bird House / Nest Box',
    icon: '🏠',
    color: '#0284c7',
    description: 'Sheltered nesting site for cavity-nesting birds',
    defaultVariant: 'Bluebird Nest Box',
    variants: [
      'Bluebird Nest Box',
      'Chickadee / Titmouse Box',
      'Wren Box',
      'Screech Owl / Kestrel Box',
      'Swallow Box',
      'Custom Nest Box',
    ],
  },
  {
    id: 'bird_bath',
    name: 'Bird Bath / Water Basin',
    icon: '💧',
    color: '#06b6d4',
    description: 'Fresh clean water source for drinking, preening, and bathing',
    defaultVariant: 'Pedestal Bird Bath',
    variants: [
      'Pedestal Bird Bath',
      'Ground Water Basin',
      'Dripper / Mister Feature',
      'Solar Fountain Bird Bath',
      'Heated Winter Bird Bath',
    ],
  },
]

function getObjectTypeDef(typeId) {
  return HABITAT_OBJECT_TYPES.find((t) => t.id === typeId) || HABITAT_OBJECT_TYPES[0]
}

const FEEDER_FOOD_OPTIONS = [
  {
    id: 'sunflower_black_oil',
    label: 'Black-Oil Sunflower Seed',
    icon: '🌻',
    desc: 'High oil & fat content; top favorite of cardinals, chickadees, finches, and nuthatches',
  },
  {
    id: 'sunflower_striped',
    label: 'Striped Sunflower Seed',
    icon: '🌻',
    desc: 'Thicker hull; great for grosbeaks, blue jays, and woodpeckers',
  },
  {
    id: 'sunflower_chips',
    label: 'Sunflower Hearts / Chips (No Shell)',
    icon: '🌻',
    desc: 'No-waste, 100% edible energy accessible to both small and large songbirds',
  },
  {
    id: 'nyjer',
    label: 'Nyjer / Thistle Seed',
    icon: '🌾',
    desc: 'Tiny oil-rich seeds favorite of American goldfinches, siskins, and redpolls',
  },
  {
    id: 'suet',
    label: 'Suet / Suet Cakes',
    icon: '🥩',
    desc: 'Rendered calorie-dense fat cakes; loved by woodpeckers, nuthatches, and wrens',
  },
  {
    id: 'nectar',
    label: 'Sugar Water / Nectar',
    icon: '🌺',
    desc: 'Boiled 4:1 water-to-sugar nectar for hummingbirds and orioles',
  },
  {
    id: 'peanuts_shelled',
    label: 'Peanuts (Shelled / Halves)',
    icon: '🥜',
    desc: 'High-fat protein nuts; beloved by jays, titmice, nuthatches, and woodpeckers',
  },
  {
    id: 'peanuts_in_shell',
    label: 'Peanuts in Shell',
    icon: '🥜',
    desc: 'Whole in-shell nuts; entertaining for jays, crows, and red-bellied woodpeckers',
  },
  {
    id: 'safflower',
    label: 'Safflower Seed',
    icon: '🌱',
    desc: 'Bitter-tasting white seed squirrels and blackbirds dislike; eaten by cardinals and chickadees',
  },
  {
    id: 'mealworms',
    label: 'Mealworms (Dried or Live)',
    icon: '🐛',
    desc: 'High-protein insect treat for bluebirds, wrens, robins, and kinglets',
  },
  {
    id: 'fruit_jelly',
    label: 'Fruit (Oranges/Apples) & Grape Jelly',
    icon: '🍊',
    desc: 'Sweet nectar substitutes for Baltimore orioles, catbirds, and tanagers',
  },
  {
    id: 'millet_white',
    label: 'White Proso Millet',
    icon: '🌾',
    desc: 'Favorite ground-feeding seed for juncos, native sparrows, and mourning doves',
  },
  {
    id: 'cracked_corn',
    label: 'Cracked Corn',
    icon: '🌽',
    desc: 'Hearty grain for mourning doves, towhees, and native ground sparrows',
  },
]

function getFoodOption(id) {
  return FEEDER_FOOD_OPTIONS.find((f) => f.id === id) || { id, label: id, icon: '🥣', desc: '' }
}

const habitatObjects = ref([])
const isObjectPlacementMode = ref(false)
const activeObjectType = ref('bird_feeder')
const selectedObject = ref(null)
const isFoodDropdownOpen = ref(false)
const objectMarkersMap = new Map()

function toggleFoodSelection(foodId) {
  if (!selectedObject.value) return
  if (!Array.isArray(selectedObject.value.foods)) {
    selectedObject.value.foods = []
  }
  const idx = selectedObject.value.foods.indexOf(foodId)
  if (idx === -1) {
    selectedObject.value.foods.push(foodId)
  } else {
    selectedObject.value.foods.splice(idx, 1)
  }
}

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
  if (!isPaintMode.value && !isObjectPlacementMode.value) return
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
  if (!isPaintMode.value && isObjectPlacementMode.value) {
    toggleObjectPlacementMode()
  }
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

function toggleObjectPlacementMode() {
  if (!isObjectPlacementMode.value && isPaintMode.value) {
    togglePaintMode()
  }
  isObjectPlacementMode.value = !isObjectPlacementMode.value
  if (!mapInstance) return

  const canvas = mapInstance.getCanvas()
  if (canvas) {
    canvas.style.cursor = isObjectPlacementMode.value ? 'crosshair' : ''
  }
  if (!isObjectPlacementMode.value) {
    isMouseOnMap.value = false
  }
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

  if (layer.id === 'habitat-objects-layer') {
    updateHabitatObjectMarkersVisibility()
    return
  }

  if (layer.id === 'ebird-sightings-layer') {
    isEbirdCardExpanded.value = layer.visible
    updateEbirdMarkersVisibility()
  }

  const visibility = layer.visible ? 'visible' : 'none'
  for (const mapLayerId of layer.mapLayerIds) {
    if (mapInstance.getLayer(mapLayerId)) {
      mapInstance.setLayoutProperty(mapLayerId, 'visibility', visibility)
    }
  }
}

function toggleEbirdCard() {
  isEbirdCardExpanded.value = !isEbirdCardExpanded.value
  const layerConfig = layers.value.find((l) => l.id === 'ebird-sightings-layer')
  if (layerConfig) {
    layerConfig.visible = isEbirdCardExpanded.value
    updateEbirdMarkersVisibility()
    if (mapInstance) {
      const visibility = isEbirdCardExpanded.value ? 'visible' : 'none'
      if (mapInstance.getLayer('ebird-radius-fill')) {
        mapInstance.setLayoutProperty('ebird-radius-fill', 'visibility', visibility)
      }
      if (mapInstance.getLayer('ebird-radius-outline')) {
        mapInstance.setLayoutProperty('ebird-radius-outline', 'visibility', visibility)
      }
    }
  }
}

function updateHabitatObjectMarkersVisibility() {
  const layerConfig = layers.value.find((l) => l.id === 'habitat-objects-layer')
  const visible = layerConfig ? layerConfig.visible : true
  for (const [, marker] of objectMarkersMap) {
    const el = marker.getElement()
    if (el) {
      el.style.display = visible ? '' : 'none'
    }
  }
}

function updateEbirdMarkersVisibility() {
  const layerConfig = layers.value.find((l) => l.id === 'ebird-sightings-layer')
  const visible = layerConfig ? layerConfig.visible : true
  if (!visible && currentOpenEbirdPopup) {
    currentOpenEbirdPopup.remove()
    currentOpenEbirdPopup = null
  }
  for (const marker of ebirdMarkers) {
    const el = marker.getElement()
    if (el) {
      el.style.display = visible ? '' : 'none'
    }
  }
}

function escapeHtml(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function formatSightingDate(dtStr) {
  if (!dtStr) return ''
  try {
    const d = new Date(dtStr.replace(' ', 'T'))
    if (isNaN(d.getTime())) return dtStr
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffHrs = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHrs < 1) return 'Just now'
    if (diffHrs < 24) return `${diffHrs}h ago`
    const diffDays = Math.floor(diffHrs / 24)
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return dtStr
  }
}

const currentTopList = computed(() => {
  if (!ebirdSightingsData.value) return []
  if (ebirdActiveTab.value === 'recent') {
    return ebirdSightingsData.value.topRecent || []
  } else if (ebirdActiveTab.value === 'closest') {
    return ebirdSightingsData.value.topClosest || []
  } else {
    return ebirdSightingsData.value.topCommon || []
  }
})

function createGeoJSONCircle(center, radiusInMiles, points = 64) {
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

function renderEbirdOnMap(data, centerLat, centerLon) {
  if (!mapInstance || !data) return
  if (!mapInstance.isStyleLoaded()) {
    mapInstance.once('style.load', () => renderEbirdOnMap(data, centerLat, centerLon))
    return
  }

  for (const m of ebirdMarkers) {
    m.remove()
  }
  ebirdMarkers = []
  if (currentOpenEbirdPopup) {
    currentOpenEbirdPopup.remove()
    currentOpenEbirdPopup = null
  }

  const circleFeature = createGeoJSONCircle([centerLon, centerLat], 1.0)
  const srcId = 'ebird-radius-source'
  const fillId = 'ebird-radius-fill'
  const outlineId = 'ebird-radius-outline'

  const layerConfig = layers.value.find((l) => l.id === 'ebird-sightings-layer')
  const isVisible = layerConfig ? layerConfig.visible : true
  const visibility = isVisible ? 'visible' : 'none'

  if (mapInstance.getSource(srcId)) {
    mapInstance.getSource(srcId).setData(circleFeature)
  } else {
    mapInstance.addSource(srcId, {
      type: 'geojson',
      data: circleFeature,
    })
    const beforeId = mapInstance.getLayer('user-paint-strokes-lines')
      ? 'user-paint-strokes-lines'
      : undefined
    mapInstance.addLayer(
      {
        id: fillId,
        type: 'fill',
        source: srcId,
        layout: { visibility },
        paint: {
          'fill-color': '#0284c7',
          'fill-opacity': 0.05,
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
          visibility,
          'line-cap': 'round',
          'line-join': 'round',
        },
        paint: {
          'line-color': '#38bdf8',
          'line-width': 1.5,
          'line-dasharray': [3, 2],
          'line-opacity': 0.7,
        },
      },
      beforeId
    )
  }

  const sightings = data.sightings || []
  for (const s of sightings) {
    const el = document.createElement('div')
    el.className = 'ebird-map-marker'
    el.dataset.sightingId = s.id || ''
    el.dataset.speciesCode = s.speciesCode || ''
    if (!isVisible) el.style.display = 'none'

    const markerBody = document.createElement('div')
    markerBody.className = 'marker-body'

    const pin = document.createElement('div')
    pin.className = 'ebird-pin'
    pin.innerHTML = '🪶'
    pin.title = `${s.comName} (${s.distanceMiles} mi)`

    markerBody.appendChild(pin)
    el.appendChild(markerBody)

    const popupHtml = `
      <div class="ebird-popup-content">
        <div class="popup-bird-header">
          <div class="popup-bird-name">${escapeHtml(s.comName)}</div>
          <div class="popup-bird-sci">${escapeHtml(s.sciName)}</div>
        </div>
        <div class="popup-bird-details">
          <div class="popup-tag-row">
            <span class="popup-tag dist-badge">📍 ${s.distanceMiles} mi away</span>
            <span class="popup-tag count-badge">🪶 ${s.howMany ? s.howMany + ' seen' : 'Present'}</span>
          </div>
          <div class="popup-time">🕒 ${escapeHtml(formatSightingDate(s.obsDt))} (${escapeHtml(s.obsDt)})</div>
          <div class="popup-loc">🏡 ${escapeHtml(s.locName || 'Nearby sighting')}</div>
          ${s.subId ? `<div class="popup-sub"><a href="https://ebird.org/checklist/${escapeHtml(s.subId)}" target="_blank" rel="noopener noreferrer">eBird Checklist #${escapeHtml(s.subId)} ↗</a></div>` : ''}
        </div>
      </div>
    `

    const popup = new mapboxgl.Popup({
      offset: 20,
      closeButton: true,
      className: 'ebird-mapbox-popup',
    })
      .setLngLat([s.lng, s.lat])
      .setHTML(popupHtml)

    popup.on('open', () => {
      if (currentOpenEbirdPopup && currentOpenEbirdPopup !== popup) {
        currentOpenEbirdPopup.remove()
      }
      currentOpenEbirdPopup = popup
    })

    popup.on('close', () => {
      el.classList.remove('is-focused')
      if (currentOpenEbirdPopup === popup) {
        currentOpenEbirdPopup = null
      }
      if (selectedSightingId.value === (s.id || s.speciesCode)) {
        selectedSightingId.value = null
      }
    })

    const marker = new mapboxgl.Marker({
      element: el,
      anchor: 'center',
    })
      .setLngLat([s.lng, s.lat])
      .setPopup(popup)
      .addTo(mapInstance)

    // Capture-phase click listener to guarantee toggle behavior and prevent duplicate Mapbox events
    el.addEventListener(
      'click',
      (e) => {
        e.stopImmediatePropagation()
        e.stopPropagation()
        toggleSightingMarker(marker, s)
      },
      true
    )

    ebirdMarkers.push(marker)
  }
}

async function loadEbirdSightings(lat, lon) {
  if (lat == null || lon == null) return
  ebirdLoading.value = true
  try {
    const res = await fetch(`/api/ebird/sightings?lat=${lat}&lon=${lon}&radius_miles=1.0&days=30`)
    if (res.ok) {
      const data = await res.json()
      ebirdSightingsData.value = data
      if (mapInstance) {
        renderEbirdOnMap(data, lat, lon)
      }
    }
  } catch (err) {
    console.error('Failed to load eBird sightings:', err)
  } finally {
    ebirdLoading.value = false
  }
}

function toggleSightingMarker(marker, sighting) {
  const sId = sighting.id || sighting.speciesCode
  const popup = marker.getPopup()
  const isCurrentlyOpen = popup && popup.isOpen()

  if (isCurrentlyOpen) {
    // If popup is already open, clicking the sighting icon closes it
    popup.remove()
    currentOpenEbirdPopup = null
    selectedSightingId.value = null
    for (const m of ebirdMarkers) {
      m.getElement()?.classList.remove('is-focused')
    }
  } else {
    // If another popup was open, close it first
    if (currentOpenEbirdPopup && currentOpenEbirdPopup !== popup) {
      currentOpenEbirdPopup.remove()
      currentOpenEbirdPopup = null
    }

    // Set focus on this marker
    for (const m of ebirdMarkers) {
      m.getElement()?.classList.remove('is-focused')
    }
    marker.getElement()?.classList.add('is-focused')
    selectedSightingId.value = sId

    if (popup) {
      popup.setLngLat([sighting.lng, sighting.lat])
      popup.addTo(mapInstance)
      currentOpenEbirdPopup = popup
    }
  }
}

function focusOnSighting(item) {
  if (!item || !mapInstance) return
  const sId = item.id || item.speciesCode

  // 1. Ensure the eBird layer is visible
  const layerConfig = layers.value.find((l) => l.id === 'ebird-sightings-layer')
  if (layerConfig && !layerConfig.visible) {
    layerConfig.visible = true
    updateEbirdMarkersVisibility()
    if (mapInstance.getLayer('ebird-radius-fill')) {
      mapInstance.setLayoutProperty('ebird-radius-fill', 'visibility', 'visible')
      mapInstance.setLayoutProperty('ebird-radius-outline', 'visibility', 'visible')
    }
  }

  // 2. Find target marker matching exact id, speciesCode, or coordinates
  let targetMarker = ebirdMarkers.find(
    (m) => m.getElement()?.dataset.sightingId === sId
  )
  if (!targetMarker && item.speciesCode) {
    targetMarker = ebirdMarkers.find(
      (m) => m.getElement()?.dataset.speciesCode === item.speciesCode
    )
  }
  if (!targetMarker && item.lng != null && item.lat != null) {
    targetMarker = ebirdMarkers.find((m) => {
      const pos = m.getLngLat()
      return (
        Math.abs(pos.lng - item.lng) < 0.0002 &&
        Math.abs(pos.lat - item.lat) < 0.0002
      )
    })
  }

  const popup = targetMarker?.getPopup()
  if (selectedSightingId.value === sId && popup && popup.isOpen()) {
    popup.remove()
    currentOpenEbirdPopup = null
    selectedSightingId.value = null
    targetMarker?.getElement()?.classList.remove('is-focused')
    return
  }

  selectedSightingId.value = sId

  // 3. Highlight target marker with pulsing beacon and high z-index
  for (const m of ebirdMarkers) {
    m.getElement()?.classList.remove('is-focused')
  }
  if (targetMarker) {
    const el = targetMarker.getElement()
    if (el) {
      el.classList.add('is-focused')
    }
  }

  // 4. Smoothly fly map to coordinates
  const targetLng = item.lng ?? targetMarker?.getLngLat().lng
  const targetLat = item.lat ?? targetMarker?.getLngLat().lat
  if (targetLng != null && targetLat != null) {
    mapInstance.flyTo({
      center: [targetLng, targetLat],
      zoom: Math.max(mapInstance.getZoom(), 17.5),
      speed: 1.4,
      essential: true,
    })
  }

  // 5. Open popup explicitly (closing any previous popup)
  if (targetMarker) {
    const popup = targetMarker.getPopup()
    if (popup) {
      if (currentOpenEbirdPopup && currentOpenEbirdPopup !== popup) {
        currentOpenEbirdPopup.remove()
      }
      popup.addTo(mapInstance)
      currentOpenEbirdPopup = popup
    }
  }
}

function renderHabitatObjectMarkers() {
  if (!mapInstance) return

  const activeIds = new Set(habitatObjects.value.map((o) => o.id))
  for (const [id, marker] of objectMarkersMap) {
    if (!activeIds.has(id)) {
      marker.remove()
      objectMarkersMap.delete(id)
    }
  }

  const layerConfig = layers.value.find((l) => l.id === 'habitat-objects-layer')
  const isLayerVisible = layerConfig ? layerConfig.visible : true

  for (const obj of habitatObjects.value) {
    const typeDef = getObjectTypeDef(obj.type)
    let marker = objectMarkersMap.get(obj.id)

    if (marker) {
      marker.setLngLat(obj.coordinates)
      const el = marker.getElement()
      if (el) {
        el.style.display = isLayerVisible ? '' : 'none'
        const pin = el.querySelector('.marker-pin')
        if (pin) pin.style.setProperty('--marker-color', typeDef.color)
        const iconSpan = el.querySelector('.marker-icon')
        if (iconSpan) iconSpan.textContent = typeDef.icon
        const label = el.querySelector('.marker-label')
        if (label) label.textContent = obj.name || typeDef.name
        const subInfo =
          obj.type === 'bird_feeder' && obj.foods && obj.foods.length
            ? obj.foods.map((f) => getFoodOption(f).label).join(', ')
            : obj.variant || ''
        el.setAttribute('title', `${obj.name}${subInfo ? ` (${subInfo})` : ''}`)
      }
    } else {
      const el = document.createElement('div')
      el.className = 'habitat-object-marker'
      el.setAttribute('data-id', obj.id)
      const subInfo =
        obj.type === 'bird_feeder' && obj.foods && obj.foods.length
          ? obj.foods.map((f) => getFoodOption(f).label).join(', ')
          : obj.variant || ''
      el.setAttribute('title', `${obj.name}${subInfo ? ` (${subInfo})` : ''}`)
      if (!isLayerVisible) el.style.display = 'none'

      const pin = document.createElement('div')
      pin.className = 'marker-pin'
      pin.style.setProperty('--marker-color', typeDef.color)

      const iconSpan = document.createElement('span')
      iconSpan.className = 'marker-icon'
      iconSpan.textContent = typeDef.icon
      pin.appendChild(iconSpan)

      const label = document.createElement('div')
      label.className = 'marker-label'
      label.textContent = obj.name || typeDef.name

      const body = document.createElement('div')
      body.className = 'marker-body'
      body.appendChild(pin)
      body.appendChild(label)

      el.appendChild(body)

      marker = new mapboxgl.Marker({
        element: el,
        draggable: true,
        anchor: 'bottom',
      })
        .setLngLat(obj.coordinates)
        .addTo(mapInstance)

      marker.on('dragend', () => {
        const lngLat = marker.getLngLat()
        obj.coordinates = [lngLat.lng, lngLat.lat]
        saveHabitatObjects()
      })

      el.addEventListener('click', (e) => {
        e.stopPropagation()
        openObjectDetails(obj)
      })

      objectMarkersMap.set(obj.id, marker)
    }
  }
}

async function saveHabitatObjects() {
  try {
    await fetch('/api/habitat-objects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ objects: habitatObjects.value }),
    })
  } catch (err) {
    console.error('Failed to save habitat objects:', err)
  }
}

function onMapClick(e) {
  if (!isObjectPlacementMode.value) return
  const coords = [e.lngLat.lng, e.lngLat.lat]
  const typeDef = getObjectTypeDef(activeObjectType.value)
  const newObj = {
    id: `obj-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    type: typeDef.id,
    name: typeDef.name,
    foods: typeDef.id === 'bird_feeder' ? ['sunflower_black_oil'] : [],
    variant: typeDef.defaultVariant,
    notes: '',
    coordinates: coords,
    dateAdded: new Date().toISOString().slice(0, 10),
  }
  habitatObjects.value.push(newObj)
  renderHabitatObjectMarkers()
  saveHabitatObjects()
  openObjectDetails(newObj)
}

function openObjectDetails(obj) {
  selectedObject.value = JSON.parse(JSON.stringify(obj))
  if (!Array.isArray(selectedObject.value.foods)) {
    selectedObject.value.foods =
      selectedObject.value.type === 'bird_feeder' ? ['sunflower_black_oil'] : []
  }
  isFoodDropdownOpen.value = false
}

function closeObjectDetails() {
  selectedObject.value = null
  isFoodDropdownOpen.value = false
}

function saveAndCloseObjectDetails() {
  if (!selectedObject.value) return
  const idx = habitatObjects.value.findIndex((o) => o.id === selectedObject.value.id)
  if (idx !== -1) {
    habitatObjects.value[idx] = { ...selectedObject.value }
    renderHabitatObjectMarkers()
    saveHabitatObjects()
  }
  selectedObject.value = null
  isFoodDropdownOpen.value = false
}

function changeSelectedObjectType(typeId) {
  if (!selectedObject.value) return
  const prevTypeDef = getObjectTypeDef(selectedObject.value.type)
  const newTypeDef = getObjectTypeDef(typeId)
  selectedObject.value.type = typeId
  if (!selectedObject.value.name || selectedObject.value.name === prevTypeDef.name) {
    selectedObject.value.name = newTypeDef.name
  }
  if (!newTypeDef.variants.includes(selectedObject.value.variant)) {
    selectedObject.value.variant = newTypeDef.defaultVariant
  }
  if (typeId === 'bird_feeder' && (!selectedObject.value.foods || !selectedObject.value.foods.length)) {
    selectedObject.value.foods = ['sunflower_black_oil']
  }
}

function deleteObject(obj) {
  if (!obj) return
  habitatObjects.value = habitatObjects.value.filter((o) => o.id !== obj.id)
  renderHabitatObjectMarkers()
  saveHabitatObjects()
  selectedObject.value = null
}

function focusOnObject(obj) {
  if (!mapInstance || !obj.coordinates) return
  mapInstance.flyTo({
    center: obj.coordinates,
    zoom: Math.max(mapInstance.getZoom(), 19),
    duration: 800,
  })
  openObjectDetails(obj)
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
  if (e.key === 'Escape') {
    if (selectedObject.value) {
      closeObjectDetails()
    } else if (isObjectPlacementMode.value) {
      toggleObjectPlacementMode()
    } else if (isPaintMode.value) {
      togglePaintMode()
    } else if (showBirdModal.value) {
      showBirdModal.value = false
    }
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
      if (Array.isArray(data.habitatObjects) && data.habitatObjects.length > 0) {
        habitatObjects.value = data.habitatObjects
      }
      if (data.habitatSegmentation) {
        registerHabitatLayers(data.habitatSegmentation)
      }
      if (lat != null && lon != null) {
        loadEbirdSightings(lat, lon)
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
    if (habitatObjects.value.length > 0) {
      renderHabitatObjectMarkers()
    }
    if (ebirdSightingsData.value && lat != null && lon != null) {
      renderEbirdOnMap(ebirdSightingsData.value, lat, lon)
    } else if (lat != null && lon != null) {
      loadEbirdSightings(lat, lon)
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

  mapInstance.on('click', onMapClick)
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
  for (const [, marker] of objectMarkersMap) {
    marker.remove()
  }
  objectMarkersMap.clear()
  for (const m of ebirdMarkers) {
    m.remove()
  }
  ebirdMarkers = []
  if (currentOpenEbirdPopup) {
    currentOpenEbirdPopup.remove()
    currentOpenEbirdPopup = null
  }
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

      <!-- eBird Local Sightings Card (Positioned directly below Property Info for high visibility) -->
      <div v-if="currentAddress" class="ebird-panel">
        <div
          class="panel-header-row clickable-header"
          title="Click to expand/collapse local bird sightings"
          @click="toggleEbirdCard"
        >
          <div class="panel-title-wrap">
            <span class="ebird-badge-icon">🪶</span>
            <div>
              <div class="panel-heading">Local Bird Sightings</div>
              <div class="ebird-subtitle">eBird • 1.0 mi radius • Last 30 days</div>
            </div>
          </div>
          <div class="panel-header-actions">
            <span v-if="ebirdLoading" class="ebird-count-badge loading">
              Loading...
            </span>
            <span v-else-if="ebirdSightingsData" class="ebird-count-badge">
              {{ ebirdSightingsData.totalSightings }} spotted
            </span>
            <span class="expand-chevron">
              {{ isEbirdCardExpanded ? '▾' : '▸' }}
            </span>
          </div>
        </div>

        <template v-if="isEbirdCardExpanded">
          <!-- 3 Tabs: Top 5 Recent, Closest, Most Common -->
          <div class="ebird-tabs-nav">
            <button
              type="button"
              :class="['ebird-tab-btn', { active: ebirdActiveTab === 'recent' }]"
              @click="ebirdActiveTab = 'recent'"
            >
              🕒 Recent
            </button>
            <button
              type="button"
              :class="['ebird-tab-btn', { active: ebirdActiveTab === 'closest' }]"
              @click="ebirdActiveTab = 'closest'"
            >
              📍 Closest
            </button>
            <button
              type="button"
              :class="['ebird-tab-btn', { active: ebirdActiveTab === 'common' }]"
              @click="ebirdActiveTab = 'common'"
            >
              📊 Common
            </button>
          </div>

          <div v-if="ebirdLoading" class="ebird-loading-state">
            <span class="ebird-spinner"></span>
            <span>Loading local sightings...</span>
          </div>

          <div v-else-if="currentTopList.length > 0" class="ebird-items-list">
            <div
              v-for="(item, idx) in currentTopList"
              :key="item.id || item.speciesCode || idx"
              :class="[
                'ebird-item-card',
                { active: selectedSightingId === (item.id || item.speciesCode) },
              ]"
              title="Click to view on map"
              @click="focusOnSighting(item)"
            >
              <div class="card-item-rank">#{{ idx + 1 }}</div>
              <div class="card-item-body">
                <div class="card-item-header">
                  <span class="card-item-name">{{ item.comName }}</span>
                  <span class="card-item-dist-pill">
                    {{ (item.minDistanceMiles ?? item.distanceMiles)?.toFixed(2) }} mi
                  </span>
                </div>
                <div class="card-item-sci">{{ item.sciName }}</div>
                <div class="card-item-details">
                  <template v-if="ebirdActiveTab === 'common'">
                    <span class="detail-badge common-badge">
                      {{ item.observationCount }} reports ({{ item.totalIndividuals }} birds)
                    </span>
                    <span class="detail-badge loc-badge" :title="item.locName">{{ item.locName }}</span>
                  </template>
                  <template v-else-if="ebirdActiveTab === 'closest'">
                    <span class="detail-badge dist-badge">
                      {{ item.distanceMiles }} mi away
                    </span>
                    <span class="detail-badge date-badge">{{ formatSightingDate(item.obsDt) }}</span>
                    <span class="detail-badge loc-badge" :title="item.locName">{{ item.locName }}</span>
                  </template>
                  <template v-else>
                    <span class="detail-badge date-badge">
                      {{ formatSightingDate(item.obsDt) }}
                    </span>
                    <span v-if="item.howMany" class="detail-badge count-badge">
                      ×{{ item.howMany }}
                    </span>
                    <span class="detail-badge loc-badge" :title="item.locName">{{ item.locName }}</span>
                  </template>
                </div>
              </div>
              <div class="card-locate-icon" title="Pan to marker on map">
                🎯
              </div>
            </div>
          </div>

          <div v-else class="ebird-empty-state">
            No sightings recorded within 1.0 mile in the last 30 days.
          </div>
        </template>
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
              <span v-else-if="layer.id === 'habitat-objects-layer'" class="layer-tag count-tag">
                {{ habitatObjects.length }}
              </span>
              <span v-else-if="layer.id === 'ebird-sightings-layer'" class="layer-tag count-tag">
                {{ ebirdSightingsData?.totalSightings || 0 }}
              </span>
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

        <!-- Habitat Objects Section -->
        <div v-if="parcelFeature" class="habitat-objects-section">
          <div class="section-divider"></div>
          <div class="objects-section-header">
            <div class="section-title-wrap">
              <span class="section-title">Habitat Features</span>
              <span class="objects-count-badge">{{ habitatObjects.length }}</span>
            </div>
            <button
              type="button"
              :class="['add-object-btn', { active: isObjectPlacementMode }]"
              @click="toggleObjectPlacementMode"
            >
              <span class="btn-icon">{{ isObjectPlacementMode ? '✕' : '📍' }}</span>
              <span>{{ isObjectPlacementMode ? 'Cancel' : 'Add Object' }}</span>
            </button>
          </div>

          <!-- Placed Objects List -->
          <div v-if="habitatObjects.length > 0" class="placed-objects-list">
            <div
              v-for="obj in habitatObjects"
              :key="obj.id"
              class="placed-object-card"
              @click="focusOnObject(obj)"
            >
              <div
                class="obj-card-icon"
                :style="{
                  backgroundColor: `${getObjectTypeDef(obj.type).color}25`,
                  borderColor: getObjectTypeDef(obj.type).color,
                }"
              >
                {{ getObjectTypeDef(obj.type).icon }}
              </div>
              <div class="obj-card-info">
                <div class="obj-card-title">{{ obj.name }}</div>
                <div class="obj-card-variant">
                  <template v-if="obj.type === 'bird_feeder' && obj.foods && obj.foods.length">
                    {{ obj.foods.map((f) => getFoodOption(f).label).join(', ') }}
                  </template>
                  <template v-else-if="obj.type === 'bird_feeder'">
                    No food specified
                  </template>
                  <template v-else>
                    {{ getObjectTypeDef(obj.type).name }}
                  </template>
                </div>
              </div>
              <button
                type="button"
                class="obj-card-delete-btn"
                title="Delete object"
                @click.stop="deleteObject(obj)"
              >
                🗑
              </button>
            </div>
          </div>
          <div v-else class="empty-objects-hint">
            Place bird feeders, nest boxes, or water baths on your map.
          </div>
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

    <!-- Floating Habitat Object Placement Toolbar -->
    <div v-if="isObjectPlacementMode" class="object-floating-toolbar">
      <div class="toolbar-header">
        <div class="toolbar-title-wrap">
          <span class="toolbar-icon">📍</span>
          <span class="toolbar-title">Place Habitat Object</span>
        </div>
        <span class="toolbar-hint">
          Click map to place a {{ getObjectTypeDef(activeObjectType).name }}
        </span>
        <button
          type="button"
          class="toolbar-close-btn"
          title="Exit Placement Mode"
          @click="toggleObjectPlacementMode"
        >
          ✕
        </button>
      </div>

      <div class="toolbar-palette">
        <button
          v-for="t in HABITAT_OBJECT_TYPES"
          :key="t.id"
          type="button"
          :class="['palette-chip', { active: activeObjectType === t.id }]"
          :style="{ '--chip-color': t.color }"
          @click="activeObjectType = t.id"
        >
          <span class="chip-swatch" :style="{ backgroundColor: t.color }"></span>
          <span class="chip-icon">{{ t.icon }}</span>
          <span class="chip-name">{{ t.name }}</span>
        </button>
      </div>

      <div class="toolbar-footer">
        <span class="placement-subtext">Click map to place • Drag pin to relocate</span>
        <button type="button" class="action-btn-primary" @click="toggleObjectPlacementMode">
          Done Placing
        </button>
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

    <!-- Real-time Object Placement Cursor -->
    <div
      v-if="isObjectPlacementMode && isMouseOnMap"
      class="object-placement-cursor"
      :style="{
        left: `${cursorPos.x}px`,
        top: `${cursorPos.y}px`,
        '--cursor-color': getObjectTypeDef(activeObjectType).color,
      }"
    >
      <div class="cursor-pin">
        <span class="cursor-icon">{{ getObjectTypeDef(activeObjectType).icon }}</span>
      </div>
      <div class="cursor-label">Click to place</div>
    </div>

    <!-- Object Edit & Details Modal -->
    <div v-if="selectedObject" class="object-modal-overlay" @click.self="closeObjectDetails">
      <div class="object-modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <span class="modal-type-icon">{{ getObjectTypeDef(selectedObject.type).icon }}</span>
            <h3>{{ selectedObject.name || 'Habitat Object' }}</h3>
          </div>
          <button class="modal-close-btn" @click="closeObjectDetails">✕</button>
        </div>

        <div class="modal-body">
          <!-- Type selector pills -->
          <div class="form-group">
            <label class="form-label">Category</label>
            <div class="type-selector-pills">
              <button
                v-for="t in HABITAT_OBJECT_TYPES"
                :key="t.id"
                type="button"
                :class="['type-pill', { active: selectedObject.type === t.id }]"
                :style="{ '--type-color': t.color }"
                @click="changeSelectedObjectType(t.id)"
              >
                <span class="pill-icon">{{ t.icon }}</span>
                <span>{{ t.name }}</span>
              </button>
            </div>
          </div>

          <!-- Object Name -->
          <div class="form-group">
            <label class="form-label">Name / Label</label>
            <input
              v-model="selectedObject.name"
              type="text"
              class="form-input"
              placeholder="e.g. Backyard Tube Feeder"
            />
          </div>

          <!-- Feeder Foods Multi-Select Dropdown -->
          <div v-if="selectedObject.type === 'bird_feeder'" class="form-group food-multiselect-group">
            <div class="form-label-row">
              <label class="form-label">Foods in Feeder</label>
              <span v-if="selectedObject.foods && selectedObject.foods.length" class="selected-count-badge">
                {{ selectedObject.foods.length }} selected
              </span>
            </div>

            <!-- Multi-select trigger & selected chips -->
            <div
              class="food-multiselect-box"
              :class="{ open: isFoodDropdownOpen }"
              @click="isFoodDropdownOpen = !isFoodDropdownOpen"
            >
              <div v-if="selectedObject.foods && selectedObject.foods.length" class="food-chips-wrap">
                <span
                  v-for="foodId in selectedObject.foods"
                  :key="foodId"
                  class="food-chip-tag"
                  @click.stop
                >
                  <span class="chip-food-icon">{{ getFoodOption(foodId).icon }}</span>
                  <span class="chip-food-label">{{ getFoodOption(foodId).label }}</span>
                  <button
                    type="button"
                    class="chip-food-remove"
                    title="Remove food"
                    @click.stop="toggleFoodSelection(foodId)"
                  >
                    ✕
                  </button>
                </span>
                <span class="food-add-more-hint">+ Add / edit foods</span>
              </div>
              <div v-else class="food-placeholder">
                <span>Select foods in this feeder (e.g. Sunflower, Suet, Nectar)...</span>
              </div>
              <span class="food-dropdown-arrow">{{ isFoodDropdownOpen ? '▴' : '▾' }}</span>
            </div>

            <!-- Dropdown Menu -->
            <div v-if="isFoodDropdownOpen" class="food-dropdown-panel" @click.stop>
              <div class="dropdown-panel-header">
                <span class="panel-header-title">Select All Applicable Foods</span>
                <button
                  v-if="selectedObject.foods && selectedObject.foods.length"
                  type="button"
                  class="dropdown-clear-btn"
                  @click="selectedObject.foods = []"
                >
                  Clear all
                </button>
              </div>

              <div class="dropdown-options-scroll">
                <label
                  v-for="opt in FEEDER_FOOD_OPTIONS"
                  :key="opt.id"
                  class="food-checkbox-item"
                  :class="{ active: selectedObject.foods?.includes(opt.id) }"
                >
                  <input
                    type="checkbox"
                    :checked="selectedObject.foods?.includes(opt.id)"
                    @change="toggleFoodSelection(opt.id)"
                  />
                  <span class="opt-icon">{{ opt.icon }}</span>
                  <div class="opt-text-wrap">
                    <div class="opt-label">{{ opt.label }}</div>
                    <div class="opt-desc">{{ opt.desc }}</div>
                  </div>
                </label>
              </div>
            </div>
          </div>

          <!-- Non-feeder Style / Variant (for Bird House & Bird Bath) -->
          <div v-else class="form-group">
            <label class="form-label">Style / Model</label>
            <select v-model="selectedObject.variant" class="form-select">
              <option
                v-for="v in getObjectTypeDef(selectedObject.type).variants"
                :key="v"
                :value="v"
              >
                {{ v }}
              </option>
            </select>
          </div>

          <!-- Notes / Specs -->
          <div class="form-group">
            <label class="form-label">Notes & Observations</label>
            <textarea
              v-model="selectedObject.notes"
              class="form-textarea"
              rows="3"
              placeholder="e.g. Filled with black oil sunflower seeds; cleaned bi-weekly. Attracts Chickadees and Nuthatches."
            ></textarea>
          </div>

          <div class="location-hint">
            <span class="hint-icon">💡</span>
            <span>Tip: Drag the pin on the map anytime to reposition it.</span>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn-danger" @click="deleteObject(selectedObject)">
            🗑 Delete Object
          </button>
          <button type="button" class="btn-primary" @click="saveAndCloseObjectDetails">
            ✓ Save & Close
          </button>
        </div>
      </div>
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
  z-index: 20;
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
  z-index: 20;
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
.ebird-panel,
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
  z-index: 1;
}

.capture-date {
  position: absolute;
  bottom: 12px;
  right: 12px;
  z-index: 20;
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

/* Layer Count Tag */
.count-tag {
  background-color: rgba(245, 158, 11, 0.2) !important;
  color: #fcd34d !important;
  border: 1px solid rgba(245, 158, 11, 0.4) !important;
  font-weight: 700 !important;
}

/* Habitat Objects Sidebar Section */
.habitat-objects-section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.objects-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.section-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-cream);
}

.objects-count-badge {
  background-color: rgba(245, 158, 11, 0.2);
  color: #fcd34d;
  border: 1px solid rgba(245, 158, 11, 0.4);
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0 0.4rem;
  border-radius: 999px;
  line-height: 1.25;
}

.add-object-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.65rem;
  font-size: 0.74rem;
  font-weight: 600;
  color: #fcd34d;
  background-color: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.add-object-btn:hover {
  background-color: rgba(245, 158, 11, 0.28);
  border-color: #f59e0b;
}

.add-object-btn.active {
  background-color: #f59e0b;
  color: #1f1b0a;
  border-color: #f59e0b;
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.4);
}

.placed-objects-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 0.2rem;
}

.placed-object-card {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.6rem;
  background-color: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.placed-object-card:hover {
  background-color: rgba(255, 255, 255, 0.08);
  border-color: rgba(245, 158, 11, 0.5);
}

.obj-card-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  flex-shrink: 0;
}

.obj-card-info {
  flex: 1;
  min-width: 0;
}

.obj-card-title {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-cream);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.obj-card-variant {
  font-size: 0.68rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.obj-card-delete-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0.2rem 0.3rem;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.obj-card-delete-btn:hover {
  color: #f87171;
  background-color: rgba(239, 68, 68, 0.15);
}

.empty-objects-hint {
  font-size: 0.73rem;
  color: var(--text-muted);
  font-style: italic;
  padding: 0.2rem 0;
  line-height: 1.4;
}

/* Floating Habitat Object Placement Toolbar */
.object-floating-toolbar {
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
  border: 1px solid #f59e0b;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 16px rgba(245, 158, 11, 0.25);
  max-width: 580px;
  width: calc(100% - 28px);
}

.placement-subtext {
  font-size: 0.72rem;
  color: var(--text-muted);
}

/* Real-time Object Placement Cursor Preview */
.object-placement-cursor {
  position: absolute;
  pointer-events: none;
  transform: translate(-50%, -100%);
  z-index: 50;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  will-change: left, top;
}

.cursor-pin {
  width: 32px;
  height: 32px;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  background-color: var(--cursor-color, #f59e0b);
  border: 2px solid #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5), 0 0 12px var(--cursor-color, #f59e0b);
  display: flex;
  align-items: center;
  justify-content: center;
}

.cursor-icon {
  transform: rotate(45deg);
  font-size: 15px;
}

.cursor-label {
  background-color: rgba(18, 32, 25, 0.92);
  color: #e8f5e9;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  padding: 0 6px;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
}

/* Object Edit & Details Modal */
.object-modal-overlay {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.object-modal-card {
  background-color: #14241d;
  border: 1px solid var(--border-sage);
  border-radius: 10px;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65), 0 0 20px rgba(82, 183, 136, 0.15);
  max-width: 480px;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalFadeIn 0.18s ease-out;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(6px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1.2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background-color: rgba(0, 0, 0, 0.2);
}

.modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.modal-type-icon {
  font-size: 1.3rem;
}

.modal-title-wrap h3 {
  font-size: 1rem;
  font-weight: 700;
  color: #e8f5e9;
  margin: 0;
}

.modal-close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
}

.modal-close-btn:hover {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.1);
}

.modal-body {
  padding: 1.1rem 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  overflow-y: auto;
  max-height: 70vh;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

/* Feeder Foods Multi-Select Component */
.food-multiselect-group {
  position: relative;
}

.form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selected-count-badge {
  font-size: 0.68rem;
  font-weight: 700;
  color: #fcd34d;
  background-color: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.4);
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
}

.food-multiselect-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  min-height: 42px;
  padding: 0.4rem 0.65rem;
  background-color: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.food-multiselect-box:hover,
.food-multiselect-box.open {
  border-color: #52b788;
  background-color: rgba(0, 0, 0, 0.45);
}

.food-multiselect-box.open {
  box-shadow: 0 0 0 2px rgba(82, 183, 136, 0.25);
}

.food-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  flex: 1;
}

.food-chip-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.45rem;
  background-color: rgba(245, 158, 11, 0.18);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #fef3c7;
}

.chip-food-icon {
  font-size: 0.85rem;
}

.chip-food-remove {
  background: none;
  border: none;
  color: #fcd34d;
  font-size: 0.75rem;
  cursor: pointer;
  padding: 0 0.15rem;
  line-height: 1;
  border-radius: 2px;
  transition: all 0.12s ease;
}

.chip-food-remove:hover {
  color: #ef4444;
  background-color: rgba(239, 68, 68, 0.2);
}

.food-add-more-hint {
  font-size: 0.72rem;
  color: #52b788;
  font-weight: 600;
  padding: 0.1rem 0.2rem;
}

.food-placeholder {
  color: var(--text-muted);
  font-size: 0.8rem;
  flex: 1;
}

.food-dropdown-arrow {
  color: var(--text-muted);
  font-size: 0.85rem;
  padding-left: 0.3rem;
}

.food-dropdown-panel {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 120;
  background-color: #12211a;
  border: 1px solid #52b788;
  border-radius: 8px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.7), 0 0 16px rgba(82, 183, 136, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: dropdownFadeIn 0.15s ease-out;
}

@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0.75rem;
  background-color: rgba(0, 0, 0, 0.35);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.panel-header-title {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.dropdown-clear-btn {
  background: none;
  border: none;
  font-size: 0.7rem;
  color: #f87171;
  cursor: pointer;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}

.dropdown-clear-btn:hover {
  background-color: rgba(239, 68, 68, 0.15);
}

.dropdown-options-scroll {
  max-height: 220px;
  overflow-y: auto;
  padding: 0.3rem 0;
  display: flex;
  flex-direction: column;
}

.food-checkbox-item {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  transition: background-color 0.12s ease;
  user-select: none;
}

.food-checkbox-item:hover {
  background-color: rgba(255, 255, 255, 0.06);
}

.food-checkbox-item.active {
  background-color: rgba(245, 158, 11, 0.12);
}

.food-checkbox-item input[type='checkbox'] {
  margin-top: 3px;
  accent-color: #f59e0b;
  cursor: pointer;
}

.opt-icon {
  font-size: 1.05rem;
  line-height: 1.2;
}

.opt-text-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.opt-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #f1f5f9;
}

.opt-desc {
  font-size: 0.67rem;
  color: var(--text-muted);
  line-height: 1.3;
}

.form-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-cream);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.type-selector-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.type-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.65rem;
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: rgba(0, 0, 0, 0.35);
  border: 1.5px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.type-pill:hover {
  border-color: var(--type-color);
  background-color: rgba(0, 0, 0, 0.55);
}

.type-pill.active {
  border-color: var(--type-color);
  background-color: rgba(255, 255, 255, 0.12);
  color: #fff;
  box-shadow: 0 0 10px var(--type-color);
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 0.45rem 0.65rem;
  background-color: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
  color: #f1f5f9;
  font-size: 0.82rem;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: #52b788;
  box-shadow: 0 0 0 2px rgba(82, 183, 136, 0.25);
}

.form-textarea {
  resize: vertical;
  min-height: 60px;
}

.location-hint {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  padding: 0.5rem 0.7rem;
  background-color: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 6px;
  font-size: 0.72rem;
  color: #fef3c7;
  line-height: 1.4;
}

.hint-icon {
  font-size: 0.85rem;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background-color: rgba(0, 0, 0, 0.2);
}

.btn-danger {
  padding: 0.4rem 0.75rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: #f87171;
  background-color: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.35);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-danger:hover {
  background-color: #ef4444;
  color: #fff;
}

.btn-primary {
  padding: 0.4rem 0.95rem;
  font-size: 0.78rem;
  font-weight: 700;
  color: #fff;
  background-color: #2d6a4f;
  border: 1px solid #52b788;
  border-radius: 5px;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(82, 183, 136, 0.3);
  transition: all 0.15s ease;
}

.btn-primary:hover {
  background-color: #1b4332;
  border-color: #74c69d;
}
</style>

<!-- Global Mapbox Marker Styles -->
<style>
.habitat-object-marker {
  cursor: grab;
  user-select: none;
  will-change: transform;
  z-index: 2;
  /* Crucial: NO CSS transition or transform overrides on this root marker element.
     Mapbox GL manages style.transform synchronously on every animation frame during pan/zoom. */
}

.habitat-object-marker:active {
  cursor: grabbing;
}

.habitat-object-marker .marker-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.15s ease, filter 0.15s ease;
  pointer-events: auto;
}

.habitat-object-marker:hover .marker-body {
  transform: scale(1.15) translateY(-3px);
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.45));
  z-index: 5;
}

.habitat-object-marker .marker-pin {
  width: 32px;
  height: 32px;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  background-color: var(--marker-color, #f59e0b);
  border: 2px solid #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5), 0 0 10px var(--marker-color, #f59e0b);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.habitat-object-marker .marker-icon {
  transform: rotate(45deg);
  font-size: 15px;
  line-height: 1;
}

.habitat-object-marker .marker-label {
  margin-top: 3px;
  background-color: rgba(18, 32, 25, 0.92);
  color: #f1f5f9;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
}

/* =====================================================================
   eBird Local Sightings Card & Map Styling
   ===================================================================== */
.ebird-panel {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  border-left: 3px solid #38bdf8;
  position: relative;
  z-index: 25;
}

.panel-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.panel-header-row.clickable-header {
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
  padding: 2px 3px;
  margin: -2px -3px;
  transition: opacity 0.15s ease, background-color 0.15s ease;
}

.panel-header-row.clickable-header:hover {
  opacity: 0.95;
  background-color: rgba(255, 255, 255, 0.04);
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.expand-chevron {
  font-size: 0.85rem;
  font-weight: 700;
  color: #38bdf8;
  transition: transform 0.2s ease;
  line-height: 1;
}

.panel-title-wrap {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
}

.ebird-badge-icon {
  font-size: 1.15rem;
  line-height: 1;
  margin-top: 1px;
}

.ebird-subtitle {
  font-size: 0.7rem;
  color: var(--text-muted);
  opacity: 0.9;
  margin-top: -0.2rem;
}

.ebird-count-badge {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  background-color: rgba(56, 189, 248, 0.16);
  border: 1px solid rgba(56, 189, 248, 0.4);
  color: #38bdf8;
  white-space: nowrap;
}

.ebird-count-badge.loading {
  background-color: rgba(245, 158, 11, 0.16);
  border-color: rgba(245, 158, 11, 0.4);
  color: #fbbf24;
}

.ebird-tabs-nav {
  display: flex;
  gap: 0.25rem;
  background-color: rgba(18, 36, 29, 0.75);
  padding: 3px;
  border-radius: 6px;
  border: 1px solid rgba(61, 102, 86, 0.45);
}

.ebird-tab-btn {
  flex: 1;
  padding: 4px 5px;
  font-size: 0.7rem;
  font-weight: 600;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: center;
  white-space: nowrap;
}

.ebird-tab-btn:hover {
  color: var(--text-cream);
  background-color: rgba(255, 255, 255, 0.06);
}

.ebird-tab-btn.active {
  background-color: #0284c7;
  color: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
}

.ebird-loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 0.75rem 0;
}

.ebird-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(56, 189, 248, 0.3);
  border-top-color: #38bdf8;
  border-radius: 50%;
  animation: ebird-spin 0.8s linear infinite;
}

@keyframes ebird-spin {
  to {
    transform: rotate(360deg);
  }
}

.ebird-items-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-height: 275px;
  overflow-y: auto;
  padding-right: 2px;
}

.ebird-item-card {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  padding: 0.45rem 0.55rem;
  background-color: rgba(22, 44, 35, 0.75);
  border: 1px solid rgba(61, 102, 86, 0.5);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.ebird-item-card:hover {
  background-color: rgba(30, 60, 48, 0.95);
  border-color: #38bdf8;
  transform: translateY(-1px);
}

.ebird-item-card.active {
  background-color: rgba(2, 132, 199, 0.22);
  border-color: #38bdf8;
  box-shadow: 0 0 0 1px #38bdf8;
}

.card-item-rank {
  font-size: 0.68rem;
  font-weight: 700;
  color: #f2cc8f;
  background-color: rgba(242, 204, 143, 0.15);
  border-radius: 3px;
  padding: 1px 4px;
  line-height: 1.2;
  margin-top: 1px;
  flex-shrink: 0;
}

.card-item-body {
  flex: 1;
  min-width: 0;
}

.card-item-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.3rem;
}

.card-item-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-cream);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-item-dist-pill {
  font-size: 0.68rem;
  font-weight: 600;
  color: #38bdf8;
  background-color: rgba(56, 189, 248, 0.12);
  padding: 1px 5px;
  border-radius: 8px;
  flex-shrink: 0;
}

.card-item-sci {
  font-size: 0.7rem;
  font-style: italic;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-item-details {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.detail-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.67rem;
  background-color: rgba(18, 36, 29, 0.8);
  color: var(--text-muted);
  border: 1px solid rgba(61, 102, 86, 0.4);
}

.detail-badge.common-badge {
  color: #f2cc8f;
  border-color: rgba(242, 204, 143, 0.35);
  background-color: rgba(242, 204, 143, 0.1);
}

.detail-badge.dist-badge {
  color: #38bdf8;
  border-color: rgba(56, 189, 248, 0.3);
  background-color: rgba(56, 189, 248, 0.1);
}

.detail-badge.date-badge {
  color: #a7f3d0;
  border-color: rgba(167, 243, 208, 0.3);
  background-color: rgba(16, 185, 129, 0.1);
}

.detail-badge.count-badge {
  color: #f472b6;
  border-color: rgba(244, 114, 182, 0.35);
  background-color: rgba(244, 114, 182, 0.1);
}

.detail-badge.loc-badge {
  max-width: 140px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-locate-icon {
  font-size: 0.85rem;
  opacity: 0.45;
  transition: opacity 0.15s ease;
  align-self: center;
  flex-shrink: 0;
}

.ebird-item-card:hover .card-locate-icon {
  opacity: 1;
}

.ebird-empty-state {
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 0.6rem 0;
  text-align: center;
  line-height: 1.35;
}

/* Map Markers & Popups */
.ebird-map-marker {
  cursor: pointer;
  user-select: none;
  will-change: transform;
  z-index: 2;
  /* Crucial: NO CSS transition or transform overrides on this root marker element.
     Mapbox GL manages style.transform synchronously on every animation frame during pan/zoom. */
}

.ebird-map-marker .marker-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.15s ease, filter 0.15s ease;
  pointer-events: auto;
}

.ebird-pin {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #0284c7;
  border: 2px solid #38bdf8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
  position: relative;
}

.ebird-map-marker:hover .marker-body {
  transform: scale(1.22);
  filter: drop-shadow(0 4px 12px rgba(56, 189, 248, 0.65));
}

.ebird-map-marker:hover .ebird-pin {
  border-color: #ffffff;
}

/* Focused sighting selected from card */
.ebird-map-marker.is-focused {
  z-index: 5 !important;
}

.ebird-map-marker.is-focused .marker-body {
  transform: scale(1.42) !important;
  filter: drop-shadow(0 6px 18px rgba(0, 0, 0, 0.7)) !important;
}

.ebird-map-marker.is-focused .ebird-pin {
  background: #0284c7 !important;
  border: 3px solid #f2cc8f !important;
  box-shadow: 0 0 0 4px rgba(242, 204, 143, 0.4), 0 6px 20px rgba(0, 0, 0, 0.6) !important;
}

:deep(.ebird-mapbox-popup .mapboxgl-popup-content) {
  background-color: rgba(18, 36, 29, 0.96) !important;
  border: 1px solid #38bdf8 !important;
  border-radius: 8px !important;
  color: #f4f1ea !important;
  padding: 0.75rem 0.95rem !important;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6) !important;
  font-family: inherit !important;
  min-width: 210px !important;
}

:deep(.ebird-mapbox-popup .mapboxgl-popup-close-button) {
  color: #94a3b8 !important;
  font-size: 16px !important;
  padding: 3px 7px !important;
  outline: none !important;
}

:deep(.ebird-mapbox-popup .mapboxgl-popup-close-button:hover) {
  color: #ffffff !important;
  background: transparent !important;
}

:deep(.ebird-popup-content) {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

:deep(.popup-bird-header) {
  border-bottom: 1px solid rgba(56, 189, 248, 0.25);
  padding-bottom: 0.35rem;
}

:deep(.popup-bird-name) {
  font-size: 0.92rem;
  font-weight: 700;
  color: #f4f1ea;
}

:deep(.popup-bird-sci) {
  font-size: 0.74rem;
  font-style: italic;
  color: #94a3b8;
}

:deep(.popup-tag-row) {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 0.25rem;
}

:deep(.popup-tag) {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}

:deep(.popup-tag.dist-badge) {
  background: rgba(56, 189, 248, 0.18);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.4);
}

:deep(.popup-tag.count-badge) {
  background: rgba(244, 114, 182, 0.18);
  color: #f472b6;
  border: 1px solid rgba(244, 114, 182, 0.4);
}

:deep(.popup-time),
:deep(.popup-loc) {
  font-size: 0.72rem;
  color: #cbd5e1;
  line-height: 1.35;
}

:deep(.popup-sub a) {
  color: #38bdf8;
  font-size: 0.7rem;
  text-decoration: underline;
  display: inline-block;
  margin-top: 0.2rem;
}
</style>
