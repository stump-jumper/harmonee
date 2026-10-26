<script setup>
defineProps({
  ecoregions: { type: Object, default: null },
})
</script>

<template>
  <div v-if="ecoregions" class="map-panel ecoregion-panel">
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
</template>

<style scoped>
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
</style>
