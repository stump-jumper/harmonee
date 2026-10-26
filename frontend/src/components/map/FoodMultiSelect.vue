<script setup>
import { FEEDER_FOOD_OPTIONS, getFoodOption } from '../../constants/mapConstants.js'

defineProps({
  selectedFoods: { type: Array, default: () => [] },
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open', 'toggle-food', 'clear-foods'])
</script>

<template>
  <div class="form-group food-multiselect-group">
    <div class="form-label-row">
      <label class="form-label">Foods in Feeder</label>
      <span v-if="selectedFoods && selectedFoods.length" class="selected-count-badge">
        {{ selectedFoods.length }} selected
      </span>
    </div>

    <div
      class="food-multiselect-box"
      :class="{ open }"
      @click="emit('update:open', !open)"
    >
      <div v-if="selectedFoods && selectedFoods.length" class="food-chips-wrap">
        <span
          v-for="foodId in selectedFoods"
          :key="foodId"
          class="food-chip-tag"
          @click.stop
        >
          <span class="chip-food-icon">{{ getFoodOption(foodId).icon }}</span>
          <span class="chip-food-label">{{ getFoodOption(foodId).label }}</span>
          <button
            type="button"
            class="chip-food-remove"
            title="Remove food"
            @click.stop="emit('toggle-food', foodId)"
          >
            ✕
          </button>
        </span>
        <span class="food-add-more-hint">+ Add / edit foods</span>
      </div>
      <div v-else class="food-placeholder">
        <span>Select foods in this feeder (e.g. Sunflower, Suet, Nectar)...</span>
      </div>
      <span class="food-dropdown-arrow">{{ open ? '▴' : '▾' }}</span>
    </div>

    <div v-if="open" class="food-dropdown-panel" @click.stop>
      <div class="dropdown-panel-header">
        <span class="panel-header-title">Select All Applicable Foods</span>
        <button
          v-if="selectedFoods && selectedFoods.length"
          type="button"
          class="dropdown-clear-btn"
          @click="emit('clear-foods')"
        >
          Clear all
        </button>
      </div>

      <div class="dropdown-options-scroll">
        <label
          v-for="opt in FEEDER_FOOD_OPTIONS"
          :key="opt.id"
          class="food-checkbox-item"
          :class="{ active: selectedFoods?.includes(opt.id) }"
        >
          <input
            type="checkbox"
            :checked="selectedFoods?.includes(opt.id)"
            @change="emit('toggle-food', opt.id)"
          />
          <span class="opt-icon">{{ opt.icon }}</span>
          <div class="opt-text-wrap">
            <div class="opt-label">{{ opt.label }}</div>
            <div class="opt-desc">{{ opt.desc }}</div>
          </div>
        </label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.food-multiselect-group {
  position: relative;
}

.form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selected-count-badge {
  font-size: 0.68rem;
  font-weight: 700;
  color: #fcd34d;
  background-color: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.4);
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
}

.food-multiselect-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  min-height: 42px;
  padding: 0.4rem 0.65rem;
  background-color: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.food-multiselect-box:hover,
.food-multiselect-box.open {
  border-color: #52b788;
  background-color: rgba(0, 0, 0, 0.45);
}

.food-multiselect-box.open {
  box-shadow: 0 0 0 2px rgba(82, 183, 136, 0.25);
}

.food-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  flex: 1;
}

.food-chip-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.45rem;
  background-color: rgba(245, 158, 11, 0.18);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #fef3c7;
}

.chip-food-icon {
  font-size: 0.85rem;
}

.chip-food-remove {
  background: none;
  border: none;
  color: #fcd34d;
  font-size: 0.75rem;
  cursor: pointer;
  padding: 0 0.15rem;
  line-height: 1;
  border-radius: 2px;
  transition: all 0.12s ease;
}

.chip-food-remove:hover {
  color: #ef4444;
  background-color: rgba(239, 68, 68, 0.2);
}

.food-add-more-hint {
  font-size: 0.72rem;
  color: #52b788;
  font-weight: 600;
  padding: 0.1rem 0.2rem;
}

.food-placeholder {
  color: var(--text-muted);
  font-size: 0.8rem;
  flex: 1;
}

.food-dropdown-arrow {
  color: var(--text-muted);
  font-size: 0.85rem;
  padding-left: 0.3rem;
}

.food-dropdown-panel {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 120;
  background-color: #12211a;
  border: 1px solid #52b788;
  border-radius: 8px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.7), 0 0 16px rgba(82, 183, 136, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: dropdownFadeIn 0.15s ease-out;
}

@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0.75rem;
  background-color: rgba(0, 0, 0, 0.35);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.panel-header-title {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.dropdown-clear-btn {
  background: none;
  border: none;
  font-size: 0.7rem;
  color: #f87171;
  cursor: pointer;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}

.dropdown-clear-btn:hover {
  background-color: rgba(239, 68, 68, 0.15);
}

.dropdown-options-scroll {
  max-height: 220px;
  overflow-y: auto;
  padding: 0.3rem 0;
  display: flex;
  flex-direction: column;
}

.food-checkbox-item {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  transition: background-color 0.12s ease;
  user-select: none;
}

.food-checkbox-item:hover {
  background-color: rgba(255, 255, 255, 0.06);
}

.food-checkbox-item.active {
  background-color: rgba(245, 158, 11, 0.12);
}

.food-checkbox-item input[type='checkbox'] {
  margin-top: 3px;
  accent-color: #f59e0b;
  cursor: pointer;
}

.opt-icon {
  font-size: 1.05rem;
  line-height: 1.2;
}

.opt-text-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.opt-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #f1f5f9;
}

.opt-desc {
  font-size: 0.67rem;
  color: var(--text-muted);
  line-height: 1.3;
}
</style>
