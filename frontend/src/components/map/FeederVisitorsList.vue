<script setup>
defineProps({
  foods: { type: Array, default: () => [] },
  likelihoodData: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
})
</script>

<template>
  <div class="feeder-likelihood-container">
    <div class="feeder-likelihood-header">
      <div class="flh-title-row">
        <span class="flh-badge">🕊 Expected Feeder Visitors</span>
        <span v-if="likelihoodData?.season" class="flh-season-badge">
          {{ likelihoodData.season.toUpperCase() }} SEASON
        </span>
      </div>
      <p class="flh-subtitle">
        Species predicted to visit based on your local ecoregion, current season, and feeder foods:
      </p>
    </div>

    <div v-if="loading" class="feeder-likelihood-loading">
      <span class="spinner-sm"></span>
      <span>Calculating local visitor probabilities...</span>
    </div>

    <div v-else-if="error" class="feeder-likelihood-error">
      {{ error }}
    </div>

    <div v-else-if="!foods || !foods.length" class="feeder-likelihood-empty">
      <span>🥣 No foods currently selected for this feeder.</span>
      <p>Expand Feeder Settings below and select foods to see which birds will visit.</p>
    </div>

    <div
      v-else-if="likelihoodData?.visitors && likelihoodData.visitors.length"
      class="feeder-visitors-list"
    >
      <div
        v-for="bird in likelihoodData.visitors"
        :key="bird.id"
        class="feeder-visitor-card"
      >
        <div class="visitor-avatar-wrap">
          <img
            v-if="bird.imageUrl || bird.audubonImage"
            :src="bird.imageUrl || bird.audubonImage"
            :alt="bird.commonName"
            class="visitor-avatar-img"
            loading="lazy"
          />
          <div v-else class="visitor-avatar-placeholder">🐦</div>
        </div>

        <div class="visitor-info-wrap">
          <div class="visitor-headline">
            <span class="visitor-name">{{ bird.commonName }}</span>
            <span :class="['visitor-tier-pill', bird.tierCode]">{{ bird.tier }}</span>
          </div>
          <div class="visitor-sci-name">{{ bird.scientificName }}</div>
          <p class="visitor-desc">{{ bird.description }}</p>
          <div class="visitor-meta-row">
            <span class="visitor-meta-item">
              <strong class="meta-label">Primary Attraction:</strong>
              {{ bird.primaryTargetFood }}
            </span>
            <span class="visitor-meta-item visitor-prob-score">
              <strong class="meta-label">Affinity Match:</strong>
              {{ Math.round(bird.probability * 100) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="feeder-likelihood-empty">
      <span>🌾 No strong bird affinities found for the chosen food combination.</span>
    </div>
  </div>
</template>

<style scoped>
.feeder-likelihood-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(82, 183, 136, 0.25);
  border-radius: 8px;
  padding: 0.85rem;
}

.feeder-likelihood-header {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.flh-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.flh-badge {
  font-size: 0.85rem;
  font-weight: 700;
  color: #74c69d;
  letter-spacing: 0.02em;
}

.flh-season-badge {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.18);
  border: 1px solid rgba(245, 158, 11, 0.4);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  letter-spacing: 0.05em;
}

.flh-subtitle {
  font-size: 0.73rem;
  color: var(--text-muted);
  line-height: 1.35;
  margin: 0;
}

.feeder-likelihood-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #94a3af;
  padding: 1rem 0.5rem;
  justify-content: center;
}

.feeder-likelihood-error {
  font-size: 0.75rem;
  color: #f87171;
  background: rgba(239, 68, 68, 0.1);
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
}

.feeder-likelihood-empty {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.2);
  border: 1px dashed rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  padding: 0.85rem;
  text-align: center;
  line-height: 1.4;
}

.feeder-likelihood-empty p {
  margin: 0.3rem 0 0;
  font-size: 0.7rem;
  color: #64748b;
}

.feeder-visitors-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  max-height: 310px;
  overflow-y: auto;
  padding-right: 0.2rem;
}

.feeder-visitor-card {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.65rem;
  background: rgba(18, 33, 26, 0.85);
  border: 1px solid rgba(82, 183, 136, 0.2);
  border-radius: 6px;
  transition: all 0.15s ease;
}

.feeder-visitor-card:hover {
  background: rgba(24, 46, 35, 0.95);
  border-color: rgba(82, 183, 136, 0.45);
  transform: translateY(-1px);
}

.visitor-avatar-wrap {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.visitor-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.visitor-avatar-placeholder {
  font-size: 1.5rem;
}

.visitor-info-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.visitor-headline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
}

.visitor-name {
  font-size: 0.82rem;
  font-weight: 700;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.visitor-tier-pill {
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  white-space: nowrap;
}

.visitor-tier-pill.very_likely {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.4);
}

.visitor-tier-pill.likely {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.4);
}

.visitor-tier-pill.occasional {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.visitor-tier-pill.uncommon {
  background: rgba(148, 163, 184, 0.2);
  color: #94a3af;
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.visitor-sci-name {
  font-size: 0.67rem;
  font-style: italic;
  color: var(--text-muted);
}

.visitor-desc {
  font-size: 0.69rem;
  color: #cbd5e1;
  line-height: 1.3;
  margin: 0.15rem 0;
}

.visitor-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.4rem;
  font-size: 0.67rem;
  color: #94a3af;
  margin-top: 0.2rem;
  padding-top: 0.25rem;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
}

.meta-label {
  color: #6ee7b7;
  font-weight: 600;
}

.visitor-prob-score {
  font-weight: 700;
  color: #e2e8f0;
}
</style>
