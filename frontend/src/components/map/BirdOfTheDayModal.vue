<script setup>
defineProps({
  show: { type: Boolean, default: false },
  bird: { type: Object, default: null },
})

const emit = defineEmits(['close'])
</script>

<template>
  <div v-if="show && bird" class="bird-modal-backdrop" @click="emit('close')">
    <div class="bird-modal" @click.stop>
      <div class="bird-modal-header">
        <div class="bird-modal-titles">
          <span class="bird-modal-name">{{ bird.commonName }}</span>
          <span class="bird-modal-scientific">{{ bird.scientificName }}</span>
        </div>
        <button
          type="button"
          class="bird-modal-close"
          aria-label="Close full image"
          @click="emit('close')"
        >
          ✕
        </button>
      </div>
      <div class="bird-modal-image-wrap">
        <img
          :src="bird.proxyImageUrl || bird.imageUrl"
          :alt="`${bird.commonName} — Full Audubon illustration`"
          class="bird-modal-image"
        />
      </div>
      <div class="bird-modal-footer">
        <span v-if="bird.plate">{{ bird.plate }} — John James Audubon</span>
        <span v-if="bird.location">
          Spotted nearby on {{ bird.source || 'eBird' }}: {{ bird.location }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
</style>
