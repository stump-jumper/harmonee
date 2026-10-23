<script setup>
import { ref, computed, toRaw, onMounted, onBeforeUnmount } from 'vue'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

const currentAddress = ref('')
const captureDate = ref('')
const ecoregions = ref(null)
const parcelFeature = ref(null)
const mapElement = ref(null)
const errorMessage = ref('')
let mapInstance = null

const token = import.meta.env.VITE_MAPBOX_TOKEN

const parcelAcreage = computed(() => {
  const feat = parcelFeature.value
  if (!feat) return null

  const props = feat.properties || {}
  if (props.ACRES && !isNaN(Number(props.ACRES))) {
    return `${Number(props.ACRES).toFixed(2)} acres`
  }

  // Calculate geodesic area from the GeoJSON polygon coordinates (WGS84)
  const geom = feat.geometry
  const ring =
    geom?.type === 'Polygon'
      ? geom.coordinates?.[0]
      : geom?.type === 'MultiPolygon'
        ? geom.coordinates?.[0]?.[0]
        : null

  if (ring && ring.length >= 3) {
    const lat0 = (ring[0][1] * Math.PI) / 180
    const metersPerDegLat = 111132.954
    const metersPerDegLon = 111319.488 * Math.cos(lat0)

    let sum = 0
    for (let i = 0; i < ring.length - 1; i++) {
      const x1 = ring[i][0] * metersPerDegLon
      const y1 = ring[i][1] * metersPerDegLat
      const x2 = ring[i + 1][0] * metersPerDegLon
      const y2 = ring[i + 1][1] * metersPerDegLat
      sum += x1 * y2 - x2 * y1
    }
    const areaSqMeters = Math.abs(sum) / 2
    const acres = areaSqMeters / 4046.8564224
    if (acres > 0) {
      return `${acres.toFixed(2)} acres`
    }
  }

  if (props.Shape_Area && !isNaN(Number(props.Shape_Area))) {
    const acres = Number(props.Shape_Area) / 43560
    return `${acres.toFixed(2)} acres`
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

onMounted(async () => {
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

  mapInstance.addControl(new mapboxgl.NavigationControl(), 'top-right')
  mapInstance.addControl(new mapboxgl.FullscreenControl(), 'top-right')
  mapInstance.addControl(
    new mapboxgl.ScaleControl({ maxWidth: 120, unit: 'imperial' }),
    'bottom-left'
  )

  mapInstance.once('load', () => {
    mapInstance.resize()
    if (rawParcel) {
      const bounds = getParcelBounds(rawParcel)
      if (bounds) {
        mapInstance.fitBounds(bounds, {
          padding: 110,
          maxZoom: 18.5,
          duration: 0,
        })
      }
    }
  })

  mapInstance.on('moveend', () => {
    const center = mapInstance.getCenter()
    refreshCaptureDate(center.lat, center.lng)
  })
})

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
})
</script>

<template>
  <section class="map-page">
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
                :style="{ borderColor: layer.color, backgroundColor: layer.type === 'base' ? layer.color : 'transparent' }"
              ></span>
              <span class="layer-name">{{ layer.name }}</span>
              <span v-if="!layer.toggleable" class="layer-tag">Base</span>
            </label>
          </li>
        </ul>
      </div>
    </div>

    <div v-if="errorMessage" class="map-empty">
      <p>{{ errorMessage }}</p>
    </div>

    <div v-show="!errorMessage" ref="mapElement" class="satellite-map"></div>

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

:deep(.mapboxgl-ctrl-top-right) {
  top: 108px;
  right: 4px;
}

.info-panel,
.layers-panel,
.ecoregion-panel {
  padding: 0.65rem 0.85rem;
  background-color: rgba(30, 58, 47, 0.9);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
  text-align: left;
}

.layers-panel {
  width: 240px;
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
</style>
