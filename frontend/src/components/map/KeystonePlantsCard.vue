<script setup>
defineProps({
  keystonePlants: { type: Object, default: null },
})
</script>

<template>
  <div v-if="keystonePlants" class="map-panel keystone-panel">
    <div class="panel-heading">Keystone Native Plants</div>
    <div class="keystone-subtitle">Ranked by butterfly &amp; moth species supported</div>

    <div v-if="keystonePlants.treesAndShrubs?.length" class="keystone-group">
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

    <div v-if="keystonePlants.flowersAndGrasses?.length" class="keystone-group">
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
</template>

<style scoped>
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
</style>
