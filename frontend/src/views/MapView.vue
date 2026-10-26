<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, toRaw } from 'vue'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

import { fetchImageryCaptureDate, fetchPropertyData } from '../api/propertyApi.js'
import BirdOfTheDayCard from '../components/map/BirdOfTheDayCard.vue'
import BirdOfTheDayModal from '../components/map/BirdOfTheDayModal.vue'
import EbirdSightingsPanel from '../components/map/EbirdSightingsPanel.vue'
import EcoregionCard from '../components/map/EcoregionCard.vue'
import HabitatObjectModal from '../components/map/HabitatObjectModal.vue'
import KeystonePlantsCard from '../components/map/KeystonePlantsCard.vue'
import MapCursorOverlay from '../components/map/MapCursorOverlay.vue'
import MapLayersPanel from '../components/map/MapLayersPanel.vue'
import ObjectPlacementToolbar from '../components/map/ObjectPlacementToolbar.vue'
import PaintToolbar from '../components/map/PaintToolbar.vue'
import PropertyInfoCard from '../components/map/PropertyInfoCard.vue'
import { useEbirdSightings } from '../composables/useEbirdSightings.js'
import { useHabitatObjects } from '../composables/useHabitatObjects.js'
import { useHabitatPaint } from '../composables/useHabitatPaint.js'
import { useMapLayers } from '../composables/useMapLayers.js'
import { calculateParcelAcreage, getParcelCoordinatesBounds } from '../utils/geo.js'

const token = import.meta.env?.VITE_MAPBOX_TOKEN || ''

const mapElement = ref(null)
const mapRef = shallowRef(null)
const errorMessage = ref('')

const currentAddress = ref('')
const captureDate = ref('')
const ecoregions = ref(null)
const birdOfTheDay = ref(null)
const keystonePlants = ref(null)
const habitatSegmentation = ref(null)
const parcelFeature = ref(null)
const showBirdModal = ref(false)

const isMouseOnMap = ref(false)
const cursorPos = ref({ x: -1000, y: -1000 })

const parcelAcreage = computed(() => calculateParcelAcreage(parcelFeature.value))

// Layer management composable
const { layers, isLayerVisible, setLayerVisibility, toggleLayer, registerHabitatLayers } =
  useMapLayers(mapRef, {
    onLayerToggle: (layer) => {
      if (layer.id === 'habitat-objects-layer') {
        updateHabitatObjectMarkersVisibility()
      } else if (layer.id === 'ebird-sightings-layer') {
        syncWithLayerToggle(layer.visible)
      }
    },
  })

// Habitat paint composable
const {
  isPaintMode,
  isSegmenting,
  activeBrushClass,
  brushSizeMeters,
  strokes,
  brushDiameterPx,
  activeBrushColor,
  updateBrushDiameter,
  updatePaintStrokesSource,
  onMapMouseDown,
  onMapMouseMove,
  onMapMouseUp,
  togglePaintMode,
  undoStroke,
  clearAllStrokes,
  triggerPaintSegmentation,
} = useHabitatPaint(mapRef, {
  onBeforeEnterPaintMode: () => {
    if (isObjectPlacementMode.value) {
      toggleObjectPlacementMode()
    }
  },
  onClearCursor: () => {
    isMouseOnMap.value = false
  },
  onSegmentationComplete: (segData) => {
    habitatSegmentation.value = segData
    registerHabitatLayers(segData)
  },
})

// Habitat objects composable
const {
  habitatObjects,
  isObjectPlacementMode,
  activeObjectType,
  selectedObject,
  isFoodDropdownOpen,
  isEditDetailsCollapsed,
  feederLikelihoodData,
  isFeederLikelihoodLoading,
  feederLikelihoodError,
  toggleObjectPlacementMode,
  updateHabitatObjectMarkersVisibility,
  renderHabitatObjectMarkers,
  openObjectDetails,
  closeObjectDetails,
  saveAndCloseObjectDetails,
  changeSelectedObjectType,
  deleteObject,
  focusOnObject,
  onMapClick,
  toggleFoodSelection,
  clearSelectedFoods,
  cleanupObjectMarkers,
} = useHabitatObjects(mapRef, {
  isLayerVisible,
  onBeforeEnterPlacementMode: () => {
    if (isPaintMode.value) {
      togglePaintMode()
    }
  },
  onClearCursor: () => {
    isMouseOnMap.value = false
  },
})

// eBird sightings composable
const {
  ebirdSightingsData,
  ebirdLoading,
  ebirdActiveTab,
  selectedSightingId,
  isEbirdCardExpanded,
  currentTopList,
  syncWithLayerToggle,
  toggleEbirdCard,
  renderEbirdOnMap,
  loadEbirdSightings,
  focusOnSighting,
  cleanupEbirdMarkers,
} = useEbirdSightings(mapRef, {
  isLayerVisible,
  setLayerVisibility,
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

async function refreshCaptureDate(lat, lon) {
  try {
    const date = await fetchImageryCaptureDate(lat, lon)
    if (date) {
      captureDate.value = date
    }
  } catch {
    // Ignore imagery date lookup error
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
    const data = await fetchPropertyData()
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

  const initialBoundaryVisibility = isLayerVisible('property-boundary') ? 'visible' : 'none'

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
        layout: { visibility: initialBoundaryVisibility },
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
          visibility: initialBoundaryVisibility,
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
  const instance = new mapboxgl.Map({
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

  instance.addControl(new mapboxgl.NavigationControl(), 'bottom-right')
  instance.addControl(new mapboxgl.FullscreenControl(), 'bottom-right')
  instance.addControl(new mapboxgl.ScaleControl({ maxWidth: 120, unit: 'imperial' }), 'bottom-left')

  instance.once('load', () => {
    instance.resize()
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
      const bounds = getParcelCoordinatesBounds(rawParcel)
      if (bounds) {
        instance.fitBounds(bounds, {
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

  instance.on('click', onMapClick)
  instance.on('mousedown', onMapMouseDown)
  instance.on('mousemove', onMapMouseMove)
  instance.on('mouseup', onMapMouseUp)
  instance.on('zoom', () => {
    updateBrushDiameter()
    updatePaintStrokesSource()
  })
  instance.on('move', () => {
    updateBrushDiameter()
    updatePaintStrokesSource()
  })
  instance.on('moveend', () => {
    const center = instance.getCenter()
    refreshCaptureDate(center.lat, center.lng)
  })

  mapRef.value = instance
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  cleanupObjectMarkers()
  cleanupEbirdMarkers()
  if (mapRef.value) {
    mapRef.value.remove()
    mapRef.value = null
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
      <PropertyInfoCard :address="currentAddress" :acreage="parcelAcreage" />

      <EbirdSightingsPanel
        v-if="currentAddress"
        :loading="ebirdLoading"
        :sightings-data="ebirdSightingsData"
        :expanded="isEbirdCardExpanded"
        :active-tab="ebirdActiveTab"
        :top-list="currentTopList"
        :selected-sighting-id="selectedSightingId"
        @toggle-expand="toggleEbirdCard"
        @update:active-tab="ebirdActiveTab = $event"
        @select-sighting="focusOnSighting"
      />

      <EcoregionCard :ecoregions="ecoregions" />
      <BirdOfTheDayCard :bird="birdOfTheDay" @open-modal="showBirdModal = true" />
      <KeystonePlantsCard :keystone-plants="keystonePlants" />
    </div>

    <BirdOfTheDayModal
      :show="showBirdModal"
      :bird="birdOfTheDay"
      @close="showBirdModal = false"
    />

    <div class="map-sidebar-right">
      <MapLayersPanel
        :layers="layers"
        :has-parcel="Boolean(parcelFeature)"
        :is-paint-mode="isPaintMode"
        :strokes-count="strokes.length"
        :is-segmenting="isSegmenting"
        :habitat-objects="habitatObjects"
        :is-object-placement-mode="isObjectPlacementMode"
        :ebird-total-sightings="ebirdSightingsData?.totalSightings || 0"
        @toggle-layer="toggleLayer"
        @toggle-paint-mode="togglePaintMode"
        @undo-stroke="undoStroke"
        @clear-strokes="clearAllStrokes"
        @segment-paint="triggerPaintSegmentation"
        @toggle-placement-mode="toggleObjectPlacementMode"
        @focus-object="focusOnObject"
        @delete-object="deleteObject"
      />
    </div>

    <PaintToolbar
      :visible="isPaintMode"
      :active-brush-class="activeBrushClass"
      :brush-size-meters="brushSizeMeters"
      :strokes-count="strokes.length"
      :is-segmenting="isSegmenting"
      @update:active-brush-class="activeBrushClass = $event"
      @update:brush-size-meters="brushSizeMeters = $event"
      @close="togglePaintMode"
      @undo="undoStroke"
      @clear="clearAllStrokes"
      @segment="triggerPaintSegmentation"
    />

    <ObjectPlacementToolbar
      :visible="isObjectPlacementMode"
      :active-object-type="activeObjectType"
      @update:active-object-type="activeObjectType = $event"
      @close="toggleObjectPlacementMode"
    />

    <div v-if="errorMessage" class="map-empty">
      <p>{{ errorMessage }}</p>
    </div>

    <div v-show="!errorMessage" ref="mapElement" class="satellite-map"></div>

    <MapCursorOverlay
      :is-paint-mode="isPaintMode"
      :is-object-placement-mode="isObjectPlacementMode"
      :is-mouse-on-map="isMouseOnMap"
      :cursor-pos="cursorPos"
      :brush-diameter-px="brushDiameterPx"
      :active-brush-color="activeBrushColor"
      :brush-size-meters="brushSizeMeters"
      :active-object-type="activeObjectType"
    />

    <HabitatObjectModal
      :selected-object="selectedObject"
      :is-edit-details-collapsed="isEditDetailsCollapsed"
      :is-food-dropdown-open="isFoodDropdownOpen"
      :feeder-likelihood-data="feederLikelihoodData"
      :is-feeder-likelihood-loading="isFeederLikelihoodLoading"
      :feeder-likelihood-error="feederLikelihoodError"
      @close="closeObjectDetails"
      @save="saveAndCloseObjectDetails"
      @delete="deleteObject"
      @change-type="changeSelectedObjectType"
      @toggle-food="toggleFoodSelection"
      @clear-foods="clearSelectedFoods"
      @update:is-edit-details-collapsed="isEditDetailsCollapsed = $event"
      @update:is-food-dropdown-open="isFoodDropdownOpen = $event"
    />

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
</style>
