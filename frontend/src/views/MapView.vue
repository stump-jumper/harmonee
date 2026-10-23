<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

const currentAddress = ref('')
const captureDate = ref('')
const mapElement = ref(null)
const errorMessage = ref('')
let mapInstance = null

const token = import.meta.env.VITE_MAPBOX_TOKEN

async function refreshCaptureDate(lat, lon) {
  try {
    const res = await fetch(`/api/imagery-date?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`)
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

  mapboxgl.accessToken = token
  mapInstance = new mapboxgl.Map({
    container: mapElement.value,
    style: {
      version: 8,
      sources: {
        'mapbox-satellite-tiles': {
          type: 'raster',
          tiles: [
            `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/512/{z}/{x}/{y}@2x?access_token=${token}`,
          ],
          tileSize: 512,
          maxzoom: 22,
        },
      },
      layers: [
        {
          id: 'satellite-layer',
          type: 'raster',
          source: 'mapbox-satellite-tiles',
          minzoom: 0,
          maxzoom: 22,
        },
      ],
    },
    center: [lon, lat],
    zoom: 19,
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
    <div v-if="currentAddress" class="address-overlay">
      {{ currentAddress }}
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

.address-overlay {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 5;
  padding: 0.5rem 0.9rem;
  font-size: 0.95rem;
  color: var(--text-cream);
  background-color: rgba(30, 58, 47, 0.88);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
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
