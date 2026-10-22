<script setup>
import { ref, onMounted } from 'vue'

const currentAddress = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/address')
    if (res.ok) {
      const data = await res.json()
      if (data.address) {
        currentAddress.value = data.address
      }
    }
  } catch {
    const local = localStorage.getItem('harmonee_address')
    if (local) currentAddress.value = local
  }
})
</script>

<template>
  <section class="map-view">
    <div v-if="currentAddress" class="address-header">
      <p class="address-label">{{ currentAddress }}</p>
    </div>

    <div class="map-container">
      <div class="satellite-placeholder">
        <svg
          class="satellite-graphic"
          viewBox="0 0 800 500"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="xMidYMid slice"
        >
          <!-- Base ground colors mimicking aerial terrain -->
          <rect width="800" height="500" fill="#2d4233" />
          <polygon points="0,0 350,0 280,240 0,180" fill="#24382a" opacity="0.9" />
          <polygon points="350,0 800,0 800,320 420,270 280,240" fill="#364e3e" opacity="0.8" />
          <polygon points="0,180 280,240 330,500 0,500" fill="#304737" opacity="0.85" />
          <polygon points="280,240 800,320 800,500 330,500" fill="#263b2d" opacity="0.95" />

          <!-- Natural foliage clusters -->
          <circle cx="160" cy="110" r="55" fill="#1b2e20" opacity="0.8" />
          <circle cx="210" cy="130" r="45" fill="#18291d" opacity="0.85" />
          <circle cx="680" cy="140" r="70" fill="#1e3323" opacity="0.75" />
          <circle cx="630" cy="180" r="50" fill="#18291d" opacity="0.8" />
          <circle cx="690" cy="220" r="40" fill="#1b2e20" opacity="0.7" />
          <circle cx="120" cy="400" r="65" fill="#1d3023" opacity="0.8" />

          <!-- Property / Parcel outline -->
          <rect
            x="240"
            y="120"
            width="320"
            height="260"
            fill="none"
            stroke="#e5ecdb"
            stroke-width="2"
            stroke-dasharray="6,4"
            opacity="0.6"
          />

          <!-- Structure / Roof footprint -->
          <rect
            x="330"
            y="200"
            width="140"
            height="100"
            fill="#5a5e55"
            stroke="#73796d"
            stroke-width="2"
            opacity="0.85"
          />
          <polygon points="330,200 400,170 470,200" fill="#696f63" opacity="0.9" />

          <!-- Center marker pin -->
          <circle cx="400" cy="245" r="7" fill="#f4f1ea" />
          <circle cx="400" cy="245" r="14" fill="none" stroke="#f4f1ea" stroke-width="2" opacity="0.6" />
        </svg>

        <div class="map-badge">Satellite Imagery (Placeholder)</div>
      </div>
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
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}

.satellite-placeholder {
  position: relative;
  width: 100%;
  height: 480px;
  display: flex;
}

.satellite-graphic {
  width: 100%;
  height: 100%;
  display: block;
}

.map-badge {
  position: absolute;
  bottom: 16px;
  right: 16px;
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
  background-color: rgba(30, 58, 47, 0.85);
  color: var(--text-cream);
  border: 1px solid var(--border-sage);
  border-radius: 4px;
  backdrop-filter: blur(4px);
  pointer-events: none;
}
</style>
