<script setup>
defineProps({
  expanded: { type: Boolean, default: false },
  sources: { type: Array, default: () => [] },
  activeSourceId: { type: String, default: 'mapbox' },
  activeOpacity: { type: Number, default: 1.0 },
  activeSource: { type: Object, default: null },
})

const emit = defineEmits([
  'toggle-expand',
  'select-source',
  'change-opacity',
  'select-wayback-epoch',
])
</script>

<template>
  <div class="map-panel satellite-panel">
    <div
      class="panel-header-row clickable-header"
      title="Click to expand/collapse Satellite Imagery options"
      @click="emit('toggle-expand')"
    >
      <div class="panel-title-wrap">
        <span class="satellite-badge-icon">🛰️</span>
        <div>
          <div class="panel-heading">Satellite Imagery</div>
          <div class="satellite-subtitle">
            {{ activeSource?.name || 'Mapbox Satellite' }}
          </div>
        </div>
      </div>

      <div class="panel-header-actions">
        <span v-if="activeSource?.badge" class="satellite-count-badge">
          {{ activeSource.badge }}
        </span>
        <span class="expand-chevron">{{ expanded ? '▾' : '▸' }}</span>
      </div>
    </div>

    <template v-if="expanded">
      <div class="satellite-body">
        <!-- Source Selector List -->
        <div class="section-label">Select Imagery Feed:</div>
        <ul class="sources-list">
          <li
            v-for="src in sources"
            :key="src.id"
            :class="['source-item', { active: activeSourceId === src.id }]"
            @click="emit('select-source', src.id)"
          >
            <div class="source-top">
              <span
                class="source-color-dot"
                :style="{ backgroundColor: src.color || '#6ee7b7' }"
              ></span>
              <span class="source-name">{{ src.name }}</span>
              <span v-if="src.badge" class="source-badge">{{ src.badge }}</span>
            </div>
            <div v-if="src.description" class="source-desc">
              {{ src.description }}
            </div>

            <!-- Embedded Wayback Epochs selector as part of the Esri Wayback option -->
            <div
              v-if="src.id === 'esri-wayback' && activeSourceId === 'esri-wayback' && src.epochs?.length"
              class="wayback-embedded-section"
              @click.stop
            >
              <div class="wayback-header">
                <span class="wayback-title">Capture Epoch ({{ src.epochs.length }} available):</span>
                <span class="wayback-active-date">
                  {{ src.epochs[src.selectedEpochIndex || 0]?.date }}
                </span>
              </div>
              <div class="wayback-pills">
                <button
                  v-for="(epoch, idx) in src.epochs"
                  :key="epoch.releaseNumber"
                  type="button"
                  :class="['epoch-pill-btn', { active: (src.selectedEpochIndex || 0) === idx }]"
                  :title="epoch.date + ' (Release ' + epoch.releaseNumber + ')'"
                  @click.stop="emit('select-wayback-epoch', idx)"
                >
                  {{ epoch.label.split(' ')[0] }}
                </button>
              </div>
            </div>
          </li>
        </ul>

        <!-- Opacity / Blend Slider -->
        <div class="opacity-section">
          <div class="opacity-header">
            <span class="opacity-label">Layer Opacity:</span>
            <span class="opacity-value">{{ Math.round(activeOpacity * 100) }}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            :value="activeOpacity"
            @input="emit('change-opacity', Number($event.target.value))"
            class="opacity-slider"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.satellite-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-left: 3px solid #10b981;
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
  min-width: 0;
}

.satellite-badge-icon {
  font-size: 1.15rem;
  line-height: 1;
  margin-top: 1px;
  flex-shrink: 0;
}

.satellite-subtitle {
  font-size: 0.7rem;
  color: #a7f3d0;
  opacity: 0.95;
  margin-top: -0.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 175px;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
}

.satellite-count-badge {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  background-color: rgba(16, 185, 129, 0.16);
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: #6ee7b7;
  white-space: nowrap;
}

.expand-chevron {
  font-size: 0.85rem;
  color: var(--text-muted);
  user-select: none;
}

.satellite-body {
  padding-top: 0.35rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.section-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.sources-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.source-item {
  padding: 0.4rem 0.55rem;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.source-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(110, 231, 183, 0.4);
}

.source-item.active {
  background: rgba(110, 231, 183, 0.12);
  border-color: #6ee7b7;
  box-shadow: 0 0 8px rgba(110, 231, 183, 0.25);
}

.source-top {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.source-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.source-name {
  flex: 1;
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-cream);
}

.source-badge {
  font-size: 0.65rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 3px;
  padding: 0.05rem 0.35rem;
  white-space: nowrap;
}

.source-desc {
  margin-top: 0.2rem;
  font-size: 0.66rem;
  color: var(--text-muted);
  line-height: 1.25;
}

.wayback-embedded-section {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: 0.45rem;
  padding: 0.45rem;
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(129, 140, 248, 0.35);
  border-radius: 4px;
}

.wayback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.68rem;
}

.wayback-title {
  color: var(--text-cream);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 0.64rem;
}

.wayback-active-date {
  color: #a5b4fc;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.wayback-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.epoch-pill-btn {
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: var(--text-cream);
  border-radius: 4px;
  font-size: 0.66rem;
  padding: 0.15rem 0.38rem;
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 1.2;
}

.epoch-pill-btn:hover {
  background: rgba(129, 140, 248, 0.2);
  border-color: #818cf8;
}

.epoch-pill-btn.active {
  background: #818cf8;
  color: #0f172a;
  border-color: #818cf8;
  font-weight: 700;
  box-shadow: 0 0 6px rgba(129, 140, 248, 0.5);
}

.opacity-section {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding-top: 0.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.opacity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.7rem;
}

.opacity-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 600;
  color: var(--text-muted);
}

.opacity-value {
  color: #a7f3d0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.opacity-slider {
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.2);
  accent-color: #34d399;
  cursor: pointer;
}
</style>
