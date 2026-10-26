<script setup>
import { BRUSH_CLASSES, BRUSH_SIZES_METERS } from '../../constants/mapConstants.js'

defineProps({
  visible: { type: Boolean, default: false },
  activeBrushClass: { type: String, default: 'tree_canopy' },
  brushSizeMeters: { type: Number, default: 6.0 },
  strokesCount: { type: Number, default: 0 },
  isSegmenting: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:activeBrushClass',
  'update:brushSizeMeters',
  'close',
  'undo',
  'clear',
  'segment',
])
</script>

<template>
  <div v-if="visible" class="paint-floating-toolbar">
    <div class="toolbar-header">
      <div class="toolbar-title-wrap">
        <span class="toolbar-icon">🎨</span>
        <span class="toolbar-title">Paint Habitat Seeds</span>
      </div>
      <span class="toolbar-hint">Drag on the map to paint target habitat areas</span>
      <button type="button" class="toolbar-close-btn" title="Exit Paint Mode" @click="emit('close')">
        ✕
      </button>
    </div>

    <div class="toolbar-palette">
      <button
        v-for="b in BRUSH_CLASSES"
        :key="b.id"
        type="button"
        :class="['palette-chip', { active: activeBrushClass === b.id }]"
        :style="{ '--chip-color': b.color }"
        @click="emit('update:activeBrushClass', b.id)"
      >
        <span class="chip-swatch" :style="{ backgroundColor: b.color }"></span>
        <span class="chip-icon">{{ b.icon }}</span>
        <span class="chip-name">{{ b.name }}</span>
      </button>
    </div>

    <div class="toolbar-footer">
      <div class="brush-size-group">
        <span class="size-label">Brush:</span>
        <button
          v-for="sz in BRUSH_SIZES_METERS"
          :key="sz.value"
          type="button"
          :class="['size-btn', { active: brushSizeMeters === sz.value }]"
          @click="emit('update:brushSizeMeters', sz.value)"
        >
          {{ sz.label }}
        </button>
      </div>

      <div class="toolbar-actions">
        <button
          type="button"
          class="action-btn"
          :disabled="!strokesCount"
          title="Undo last stroke"
          @click="emit('undo')"
        >
          ↩ Undo
        </button>
        <button
          type="button"
          class="action-btn"
          :disabled="!strokesCount"
          title="Clear all strokes"
          @click="emit('clear')"
        >
          🗑 Clear
        </button>
        <button
          type="button"
          class="action-btn-primary"
          :disabled="isSegmenting || !strokesCount"
          @click="emit('segment')"
        >
          {{ isSegmenting ? 'Segmenting...' : '🚀 Segment Habitats' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.paint-floating-toolbar {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background-color: rgba(20, 36, 29, 0.94);
  backdrop-filter: blur(12px);
  border: 1px solid #52b788;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 16px rgba(82, 183, 136, 0.25);
  max-width: 620px;
  width: calc(100% - 28px);
}

.brush-size-group {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.size-label {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-right: 0.15rem;
}

.size-btn {
  padding: 0.15rem 0.45rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-sage);
  border-radius: 3px;
  cursor: pointer;
}

.size-btn.active {
  background-color: #2d6a4f;
  border-color: #52b788;
  color: #fff;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
</style>
