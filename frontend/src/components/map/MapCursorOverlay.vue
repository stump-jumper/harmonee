<script setup>
import { getObjectTypeDef } from '../../constants/mapConstants.js'

defineProps({
  isPaintMode: { type: Boolean, default: false },
  isObjectPlacementMode: { type: Boolean, default: false },
  isMouseOnMap: { type: Boolean, default: false },
  cursorPos: { type: Object, default: () => ({ x: -1000, y: -1000 }) },
  brushDiameterPx: { type: Number, default: 20 },
  activeBrushColor: { type: String, default: '#52b788' },
  brushSizeMeters: { type: Number, default: 6.0 },
  activeObjectType: { type: String, default: 'bird_feeder' },
})
</script>

<template>
  <div
    v-if="isPaintMode && isMouseOnMap"
    class="brush-reticle-cursor"
    :style="{
      left: `${cursorPos.x}px`,
      top: `${cursorPos.y}px`,
      width: `${brushDiameterPx}px`,
      height: `${brushDiameterPx}px`,
      borderColor: activeBrushColor,
    }"
  >
    <span class="reticle-center-dot" :style="{ backgroundColor: activeBrushColor }"></span>
    <span class="reticle-size-pill">{{ brushSizeMeters }}m</span>
  </div>

  <div
    v-if="isObjectPlacementMode && isMouseOnMap"
    class="object-placement-cursor"
    :style="{
      left: `${cursorPos.x}px`,
      top: `${cursorPos.y}px`,
      '--cursor-color': getObjectTypeDef(activeObjectType).color,
    }"
  >
    <div class="cursor-pin">
      <span class="cursor-icon">{{ getObjectTypeDef(activeObjectType).icon }}</span>
    </div>
    <div class="cursor-label">Click to place</div>
  </div>
</template>

<style scoped>
.brush-reticle-cursor {
  position: absolute;
  pointer-events: none;
  border-radius: 50%;
  border: 2px solid;
  transform: translate(-50%, -50%);
  z-index: 50;
  background-color: rgba(255, 255, 255, 0.12);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.7), 0 0 14px rgba(0, 0, 0, 0.4);
  will-change: left, top, width, height;
}

.reticle-center-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.9);
}

.reticle-size-pill {
  position: absolute;
  top: -19px;
  left: 50%;
  transform: translateX(-50%);
  background-color: rgba(18, 32, 25, 0.9);
  color: #e8f5e9;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  padding: 0 6px;
  font-size: 10px;
  font-weight: 600;
  line-height: 15px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
}

.object-placement-cursor {
  position: absolute;
  pointer-events: none;
  transform: translate(-50%, -100%);
  z-index: 50;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  will-change: left, top;
}

.cursor-pin {
  width: 32px;
  height: 32px;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  background-color: var(--cursor-color, #f59e0b);
  border: 2px solid #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5), 0 0 12px var(--cursor-color, #f59e0b);
  display: flex;
  align-items: center;
  justify-content: center;
}

.cursor-icon {
  transform: rotate(45deg);
  font-size: 15px;
}

.cursor-label {
  background-color: rgba(18, 32, 25, 0.92);
  color: #e8f5e9;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  padding: 0 6px;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
}
</style>
