<script setup>
import { getFoodOption, getObjectTypeDef } from '../../constants/mapConstants.js'

defineProps({
  layers: { type: Array, default: () => [] },
  hasParcel: { type: Boolean, default: false },
  isPaintMode: { type: Boolean, default: false },
  strokesCount: { type: Number, default: 0 },
  isSegmenting: { type: Boolean, default: false },
  habitatObjects: { type: Array, default: () => [] },
  isObjectPlacementMode: { type: Boolean, default: false },
  ebirdTotalSightings: { type: Number, default: 0 },
})

const emit = defineEmits([
  'toggle-layer',
  'toggle-paint-mode',
  'undo-stroke',
  'clear-strokes',
  'segment-paint',
  'toggle-placement-mode',
  'focus-object',
  'delete-object',
])
</script>

<template>
  <div class="map-panel layers-panel">
    <div class="panel-heading">Layers</div>
    <ul class="layers-list">
      <li v-for="layer in layers" :key="layer.id" class="layer-item">
        <label
          :class="['layer-row', { locked: !layer.toggleable }]"
          @click.prevent="layer.toggleable && emit('toggle-layer', layer)"
        >
          <input
            v-if="layer.toggleable"
            type="checkbox"
            :checked="layer.visible"
            @change="emit('toggle-layer', layer)"
            @click.stop
          />
          <span v-else class="base-indicator" title="Base layer (always active)"></span>
          <span
            class="layer-swatch"
            :style="{
              borderColor: layer.color,
              backgroundColor: layer.type !== 'overlay' ? layer.color : 'transparent',
            }"
          ></span>
          <span class="layer-name">{{ layer.name }}</span>
          <span v-if="!layer.toggleable" class="layer-tag">Base</span>
          <span v-else-if="layer.id === 'habitat-objects-layer'" class="layer-tag count-tag">
            {{ habitatObjects.length }}
          </span>
          <span v-else-if="layer.id === 'ebird-sightings-layer'" class="layer-tag count-tag">
            {{ ebirdTotalSightings }}
          </span>
          <span v-else-if="layer.percentage != null" class="layer-tag">
            {{ layer.percentage }}%
          </span>
        </label>
      </li>
    </ul>

    <div v-if="hasParcel" class="paint-controls-section">
      <div class="section-divider"></div>
      <button
        type="button"
        :class="['paint-toggle-btn', { active: isPaintMode }]"
        @click="emit('toggle-paint-mode')"
      >
        <span class="btn-icon">{{ isPaintMode ? '✕' : '🎨' }}</span>
        <span>{{ isPaintMode ? 'Exit Paint Mode' : 'Paint Habitat Seeds' }}</span>
      </button>

      <div v-if="strokesCount > 0" class="strokes-status-bar">
        <span class="strokes-badge">
          {{ strokesCount }} stroke{{ strokesCount === 1 ? '' : 's' }}
        </span>
        <div class="tool-btn-group">
          <button
            type="button"
            class="tool-btn-sm"
            title="Undo last stroke"
            @click="emit('undo-stroke')"
          >
            ↩
          </button>
          <button
            type="button"
            class="tool-btn-sm"
            title="Clear all strokes"
            @click="emit('clear-strokes')"
          >
            🗑
          </button>
        </div>
      </div>

      <button
        type="button"
        class="segment-btn"
        :disabled="isSegmenting || !strokesCount"
        @click="emit('segment-paint')"
      >
        <span v-if="isSegmenting">Segmenting from Paint...</span>
        <span v-else-if="strokesCount">🚀 Segment from Paint</span>
        <span v-else>Paint seeds to segment</span>
      </button>
    </div>

    <div v-if="hasParcel" class="habitat-objects-section">
      <div class="section-divider"></div>
      <div class="objects-section-header">
        <div class="section-title-wrap">
          <span class="section-title">Habitat Features</span>
          <span class="objects-count-badge">{{ habitatObjects.length }}</span>
        </div>
        <button
          type="button"
          :class="['add-object-btn', { active: isObjectPlacementMode }]"
          @click="emit('toggle-placement-mode')"
        >
          <span class="btn-icon">{{ isObjectPlacementMode ? '✕' : '📍' }}</span>
          <span>{{ isObjectPlacementMode ? 'Cancel' : 'Add Object' }}</span>
        </button>
      </div>

      <div v-if="habitatObjects.length > 0" class="placed-objects-list">
        <div
          v-for="obj in habitatObjects"
          :key="obj.id"
          class="placed-object-card"
          @click="emit('focus-object', obj)"
        >
          <div
            class="obj-card-icon"
            :style="{
              backgroundColor: `${getObjectTypeDef(obj.type).color}25`,
              borderColor: getObjectTypeDef(obj.type).color,
            }"
          >
            {{ getObjectTypeDef(obj.type).icon }}
          </div>
          <div class="obj-card-info">
            <div class="obj-card-title">{{ obj.name }}</div>
            <div class="obj-card-variant">
              <template v-if="obj.type === 'bird_feeder' && obj.foods && obj.foods.length">
                {{ obj.foods.map((f) => getFoodOption(f).label).join(', ') }}
              </template>
              <template v-else-if="obj.type === 'bird_feeder'">No food specified</template>
              <template v-else>{{ getObjectTypeDef(obj.type).name }}</template>
            </div>
          </div>
          <button
            type="button"
            class="obj-card-delete-btn"
            title="Delete object"
            @click.stop="emit('delete-object', obj)"
          >
            🗑
          </button>
        </div>
      </div>
      <div v-else class="empty-objects-hint">
        Place bird feeders, nest boxes, or water baths on your map.
      </div>
    </div>
  </div>
</template>

<style scoped>
.layers-panel {
  width: 280px;
}

.layers-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.layer-item {
  margin: 0;
}

.layer-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
  color: var(--text-cream);
  cursor: pointer;
  user-select: none;
  padding: 0.2rem 0;
}

.layer-row.locked {
  cursor: default;
  opacity: 0.9;
}

.base-indicator {
  width: 14px;
  height: 14px;
  display: inline-block;
  border-radius: 3px;
  background-color: rgba(200, 214, 206, 0.25);
  border: 1px solid var(--border-sage);
}

.layer-swatch {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  border: 2px solid;
  display: inline-block;
  flex-shrink: 0;
}

.layer-name {
  flex: 1;
}

.layer-tag {
  font-size: 0.7rem;
  color: var(--text-muted);
  padding: 0.05rem 0.35rem;
  border: 1px solid var(--border-sage);
  border-radius: 3px;
}

.count-tag {
  background-color: rgba(245, 158, 11, 0.2) !important;
  color: #fcd34d !important;
  border: 1px solid rgba(245, 158, 11, 0.4) !important;
  font-weight: 700 !important;
}

.segment-btn {
  margin-top: 0.55rem;
  width: 100%;
  padding: 0.4rem 0.6rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: var(--bg-forest-light);
  border: 1px solid var(--border-sage);
  border-radius: 4px;
  cursor: pointer;
}

.segment-btn:hover:not(:disabled) {
  border-color: var(--text-cream);
}

.segment-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.paint-toggle-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.45rem 0.6rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: var(--bg-forest-light);
  border: 1px solid var(--border-sage);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.paint-toggle-btn:hover {
  border-color: var(--color-leaf-bright);
}

.paint-toggle-btn.active {
  background-color: #2d6a4f;
  border-color: #52b788;
  color: #fff;
  box-shadow: 0 0 10px rgba(82, 183, 136, 0.4);
}

.strokes-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.4rem;
  padding: 0.2rem 0.3rem;
  font-size: 0.74rem;
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.strokes-badge {
  color: #a7f3d0;
  font-weight: 600;
}

.tool-btn-group {
  display: flex;
  gap: 0.3rem;
}

.tool-btn-sm {
  background: none;
  border: 1px solid var(--border-sage);
  color: var(--text-cream);
  border-radius: 3px;
  font-size: 0.72rem;
  padding: 0.1rem 0.35rem;
  cursor: pointer;
}

.tool-btn-sm:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-color: var(--text-cream);
}

.habitat-objects-section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.objects-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.section-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-cream);
}

.objects-count-badge {
  background-color: rgba(245, 158, 11, 0.2);
  color: #fcd34d;
  border: 1px solid rgba(245, 158, 11, 0.4);
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0 0.4rem;
  border-radius: 999px;
  line-height: 1.25;
}

.add-object-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.65rem;
  font-size: 0.74rem;
  font-weight: 600;
  color: #fcd34d;
  background-color: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.add-object-btn:hover {
  background-color: rgba(245, 158, 11, 0.28);
  border-color: #f59e0b;
}

.add-object-btn.active {
  background-color: #f59e0b;
  color: #1f1b0a;
  border-color: #f59e0b;
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.4);
}

.placed-objects-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 0.2rem;
}

.placed-object-card {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.6rem;
  background-color: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.placed-object-card:hover {
  background-color: rgba(255, 255, 255, 0.08);
  border-color: rgba(245, 158, 11, 0.5);
}

.obj-card-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  flex-shrink: 0;
}

.obj-card-info {
  flex: 1;
  min-width: 0;
}

.obj-card-title {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-cream);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.obj-card-variant {
  font-size: 0.68rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.obj-card-delete-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0.2rem 0.3rem;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.obj-card-delete-btn:hover {
  color: #f87171;
  background-color: rgba(239, 68, 68, 0.15);
}

.empty-objects-hint {
  font-size: 0.73rem;
  color: var(--text-muted);
  font-style: italic;
  padding: 0.2rem 0;
  line-height: 1.4;
}
</style>
