<script setup>
defineProps({
  loading: { type: Boolean, default: false },
  soilData: { type: Object, default: null },
  expanded: { type: Boolean, default: false },
  selectedSymbol: { type: String, default: null },
})

const emit = defineEmits(['toggle-expand', 'focus-unit', 'refresh'])
</script>

<template>
  <div class="map-panel soil-panel">
    <div
      class="panel-header-row clickable-header"
      title="Click to expand/collapse USDA soil survey"
      @click="emit('toggle-expand')"
    >
      <div class="panel-title-wrap">
        <span class="soil-badge-icon">🌾</span>
        <div>
          <div class="panel-heading">Soil Survey</div>
          <div class="soil-subtitle">USDA Web Soil Survey • Property Parcel AOI</div>
        </div>
      </div>

      <div class="panel-header-actions">
        <button
          type="button"
          class="panel-refresh-btn"
          title="Refresh USDA soil survey"
          :disabled="loading"
          @click.stop="emit('refresh')"
        >
          <span :class="['refresh-icon', { spinning: loading }]">↻</span>
        </button>
        <span v-if="loading" class="soil-count-badge loading">Loading...</span>
        <span v-else-if="soilData?.summary" class="soil-count-badge">
          {{ soilData.summary.length }} units
        </span>
        <span class="expand-chevron">{{ expanded ? '▾' : '▸' }}</span>
      </div>
    </div>

    <template v-if="expanded">
      <div v-if="loading" class="soil-loading-state">
        <span class="soil-spinner"></span>
        <span>Loading USDA soil survey...</span>
      </div>

      <template v-else-if="soilData?.summary && soilData.summary.length > 0">
        <ul class="soil-unit-list">
          <li
            v-for="unit in soilData.summary"
            :key="unit.musym"
            class="soil-unit-item"
            :class="{ selected: selectedSymbol === unit.musym }"
            title="Click to locate on map"
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
      </template>

      <div v-else class="soil-empty-state">
        <p>No USDA soil survey data available for this parcel.</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.soil-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.panel-header-row.clickable-header {
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
  padding: 2px 3px;
  margin: -2px -3px;
  transition: opacity 0.15s ease, background-color 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header-row.clickable-header:hover {
  opacity: 0.95;
  background-color: rgba(255, 255, 255, 0.04);
}

.panel-title-wrap {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
}

.soil-badge-icon {
  font-size: 1.15rem;
  line-height: 1;
  margin-top: 1px;
}

.soil-subtitle {
  font-size: 0.7rem;
  color: var(--text-muted);
  opacity: 0.9;
  margin-top: -0.2rem;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.panel-refresh-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 4px;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.85rem;
  line-height: 1;
  transition: all 0.15s ease;
}

.panel-refresh-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.14);
  color: #f2cc8f;
  border-color: rgba(242, 204, 143, 0.45);
  transform: scale(1.08);
}

.panel-refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-icon {
  display: inline-block;
  transition: transform 0.2s ease;
}

.refresh-icon.spinning {
  animation: refresh-spin 0.8s linear infinite;
}

@keyframes refresh-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.soil-count-badge {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  background-color: rgba(194, 139, 94, 0.16);
  border: 1px solid rgba(194, 139, 94, 0.4);
  color: #f6d5b8;
  white-space: nowrap;
}

.soil-count-badge.loading {
  background-color: rgba(245, 158, 11, 0.16);
  border-color: rgba(245, 158, 11, 0.4);
  color: #fbbf24;
}

.expand-chevron {
  font-size: 0.85rem;
  color: var(--text-muted);
  user-select: none;
}

.soil-loading-state,
.soil-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 0.5rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  font-style: italic;
}

.soil-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(242, 204, 143, 0.25);
  border-top-color: #f2cc8f;
  border-radius: 50%;
  animation: refresh-spin 0.8s linear infinite;
}

.soil-unit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.soil-unit-item {
  padding: 0.4rem 0.45rem;
  border-radius: 5px;
  background: rgba(0, 0, 0, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.1s ease;
}

.soil-unit-item:hover {
  background: rgba(0, 0, 0, 0.38);
  border-color: rgba(194, 139, 94, 0.45);
  transform: translateY(-1px);
}

.soil-unit-item.selected {
  background: rgba(194, 139, 94, 0.2);
  border-color: rgba(194, 139, 94, 0.8);
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
  padding-top: 0.3rem;
  border-top: 1px solid rgba(61, 102, 86, 0.45);
}

.footer-note {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-style: italic;
}
</style>
