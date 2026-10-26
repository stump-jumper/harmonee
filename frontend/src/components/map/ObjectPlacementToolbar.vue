<script setup>
import { HABITAT_OBJECT_TYPES, getObjectTypeDef } from '../../constants/mapConstants.js'

defineProps({
  visible: { type: Boolean, default: false },
  activeObjectType: { type: String, default: 'bird_feeder' },
})

const emit = defineEmits(['update:activeObjectType', 'close'])
</script>

<template>
  <div v-if="visible" class="object-floating-toolbar">
    <div class="toolbar-header">
      <div class="toolbar-title-wrap">
        <span class="toolbar-icon">📍</span>
        <span class="toolbar-title">Place Habitat Object</span>
      </div>
      <span class="toolbar-hint">
        Click map to place a {{ getObjectTypeDef(activeObjectType).name }}
      </span>
      <button
        type="button"
        class="toolbar-close-btn"
        title="Exit Placement Mode"
        @click="emit('close')"
      >
        ✕
      </button>
    </div>

    <div class="toolbar-palette">
      <button
        v-for="t in HABITAT_OBJECT_TYPES"
        :key="t.id"
        type="button"
        :class="['palette-chip', { active: activeObjectType === t.id }]"
        :style="{ '--chip-color': t.color }"
        @click="emit('update:activeObjectType', t.id)"
      >
        <span class="chip-swatch" :style="{ backgroundColor: t.color }"></span>
        <span class="chip-icon">{{ t.icon }}</span>
        <span class="chip-name">{{ t.name }}</span>
      </button>
    </div>

    <div class="toolbar-footer">
      <span class="placement-subtext">Click map to place • Drag pin to relocate</span>
      <button type="button" class="action-btn-primary" @click="emit('close')">Done Placing</button>
    </div>
  </div>
</template>

<style scoped>
.object-floating-toolbar {
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
  border: 1px solid #f59e0b;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 16px rgba(245, 158, 11, 0.25);
  max-width: 580px;
  width: calc(100% - 28px);
}

.placement-subtext {
  font-size: 0.72rem;
  color: var(--text-muted);
}
</style>
