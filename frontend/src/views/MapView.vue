<script setup>
import { ref, computed, onMounted } from 'vue'

const currentAddress = ref('')
const coords = ref({ lat: null, lon: null })
const errorMessage = ref('')

const token = import.meta.env.VITE_MAPBOX_TOKEN

const satelliteImageUrl = computed(() => {
  if (!token || coords.value.lat == null || coords.value.lon == null) return ''
  const { lon, lat } = coords.value
  return `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${lon},${lat},19,0/860x500@2x?access_token=${token}`
})

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

  coords.value = { lat, lon }
})
</script>

<template>
  <section class="map-view">
    <div v-if="currentAddress" class="address-header">
      <p class="address-label">{{ currentAddress }}</p>
    </div>

    <div class="map-container">
      <div v-if="errorMessage" class="map-empty">
        <p>{{ errorMessage }}</p>
      </div>
      <img
        v-else-if="satelliteImageUrl"
        :src="satelliteImageUrl"
        :alt="`Satellite view of ${currentAddress}`"
        class="satellite-image"
      />
    </div>
  </section>
</template>

<style scoped>
.map-view {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.address-header {
  margin-bottom: 1rem;
}

.address-label {
  font-size: 1.1rem;
  color: var(--text-muted);
  margin: 0;
}

.map-container {
  width: 100%;
  max-width: 860px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-sage);
  background-color: var(--surface-green);
}

.satellite-image {
  width: 100%;
  height: 500px;
  object-fit: cover;
  display: block;
}

.map-empty {
  height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  padding: 2rem;
}
</style>
