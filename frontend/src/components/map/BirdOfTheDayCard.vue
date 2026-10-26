<script setup>
defineProps({
  bird: { type: Object, default: null },
})

const emit = defineEmits(['open-modal'])
</script>

<template>
  <div v-if="bird" class="map-panel bird-panel">
    <div class="panel-heading">Bird of the Day</div>
    <div class="bird-content">
      <button
        type="button"
        class="bird-image-frame"
        title="Click to view full Audubon illustration"
        @click="emit('open-modal')"
      >
        <img
          :src="bird.proxyImageUrl || bird.imageUrl"
          :alt="`${bird.commonName} — Audubon illustration`"
          class="bird-illustration"
        />
      </button>
      <div class="bird-details">
        <div class="bird-name">{{ bird.commonName }}</div>
        <div class="bird-scientific">{{ bird.scientificName }}</div>
        <div v-if="bird.plate" class="bird-plate">{{ bird.plate }} (J.J. Audubon)</div>
        <div v-if="bird.location" class="bird-sighting">
          Spotted nearby on {{ bird.source || 'eBird' }}: {{ bird.location }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
</style>
