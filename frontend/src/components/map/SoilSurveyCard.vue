<script setup>
defineProps({
  soilData: { type: Object, default: null },
  isLayerVisible: { type: Boolean, default: true },
  selectedSymbol: { type: String, default: null },
})

const emit = defineEmits(['toggle-layer', 'focus-unit'])
</script>

<template>
  <div v-if="soilData && soilData.summary && soilData.summary.length > 0" class="map-panel soil-panel">
    <div class="soil-header">
      <div class="panel-heading">Soil Survey</div>
      <button
        type="button"
        class="soil-layer-toggle-btn"
        :class="{ active: isLayerVisible }"
        :title="isLayerVisible ? 'Hide soil map layer' : 'Show soil map layer'"
        @click="emit('toggle-layer')"
      >
        <span class="toggle-icon">{{ isLayerVisible ? '👁️' : '👁️‍🗨️' }}</span>
        <span>{{ isLayerVisible ? 'Layer On' : 'Layer Off' }}</span>
      </button>
    </div>

    <div class="soil-source-tag">USDA Web Soil Survey • Property Parcel AOI</div>

    <ul class="soil-unit-list">
      <li
        v-for="unit in soilData.summary"
        :key="unit.musym"
        class="soil-unit-item"
        :class="{ selected: selectedSymbol === unit.musym }"
        @click="emit('focus-unit', unit)"
      >
        <div class="soil-unit-top">
          <span
            class="soil-symbol-badge"
            :style="{ backgroundColor: unit.color, borderColor: unit.color }"
          >
            {{ unit.musym }}
          </span>
          <div class="soil-unit-meta">
            <div class="soil-unit-name" :title="unit.muname">
              {{ unit.muname }}
            </div>
            <div class="soil-unit-pct">
              <strong>{{ unit.percentage }}%</strong>
              <span class="pct-label">of property</span>
            </div>
          </div>
        </div>

        <div class="soil-bar-track">
          <div
            class="soil-bar-fill"
            :style="{ width: `${unit.percentage}%`, backgroundColor: unit.color }"
          ></div>
        </div>
      </li>
    </ul>

    <div class="soil-card-footer">
      <span class="footer-note">Total property coverage: 100%</span>
    </div>
  </div>
</template>

<style scoped>
.soil-panel {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.soil-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.soil-header .panel-heading {
  margin-bottom: 0;
}

.soil-layer-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  color: var(--text-muted);
  font-size: 0.72rem;
  padding: 2px 7px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.soil-layer-toggle-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-cream);
}

.soil-layer-toggle-btn.active {
  background: rgba(194, 139, 94, 0.22);
  border-color: rgba(194, 139, 94, 0.55);
  color: #f6d5b8;
}

.soil-source-tag {
  font-size: 0.7rem;
  color: var(--text-muted);
  opacity: 0.85;
}

.soil-unit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.soil-unit-item {
  padding: 0.4rem 0.45rem;
  border-radius: 5px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.1s ease;
}

.soil-unit-item:hover {
  background: rgba(0, 0, 0, 0.32);
  border-color: rgba(194, 139, 94, 0.4);
  transform: translateY(-1px);
}

.soil-unit-item.selected {
  background: rgba(194, 139, 94, 0.18);
  border-color: rgba(194, 139, 94, 0.7);
}

.soil-unit-top {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.soil-symbol-badge {
  flex-shrink: 0;
  font-weight: 800;
  font-size: 0.74rem;
  color: #ffffff;
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.04em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  border: 1px solid transparent;
}

.soil-unit-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.soil-unit-name {
  font-size: 0.8rem;
  color: var(--text-cream);
  line-height: 1.3;
  white-space: normal;
  word-break: break-word;
}

.soil-unit-pct {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
  font-size: 0.82rem;
  color: #f2cc8f;
}

.soil-unit-pct strong {
  font-weight: 700;
}

.soil-unit-pct .pct-label {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.soil-bar-track {
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  margin-top: 0.35rem;
  overflow: hidden;
}

.soil-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.soil-card-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.25rem;
  border-top: 1px solid rgba(61, 102, 86, 0.45);
}

.footer-note {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-style: italic;
}
</style>
