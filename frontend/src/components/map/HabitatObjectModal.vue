<script setup>
import { HABITAT_OBJECT_TYPES, getObjectTypeDef } from '../../constants/mapConstants.js'
import FeederVisitorsList from './FeederVisitorsList.vue'
import FoodMultiSelect from './FoodMultiSelect.vue'

defineProps({
  selectedObject: { type: Object, default: null },
  isEditDetailsCollapsed: { type: Boolean, default: true },
  isFoodDropdownOpen: { type: Boolean, default: false },
  feederLikelihoodData: { type: Object, default: null },
  isFeederLikelihoodLoading: { type: Boolean, default: false },
  feederLikelihoodError: { type: String, default: null },
})

const emit = defineEmits([
  'close',
  'save',
  'delete',
  'change-type',
  'toggle-food',
  'clear-foods',
  'update:isEditDetailsCollapsed',
  'update:isFoodDropdownOpen',
])
</script>

<template>
  <div v-if="selectedObject" class="object-modal-overlay" @click.self="emit('close')">
    <div class="object-modal-card">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <span class="modal-type-icon">{{ getObjectTypeDef(selectedObject.type).icon }}</span>
          <h3>{{ selectedObject.name || 'Habitat Object' }}</h3>
        </div>
        <button class="modal-close-btn" @click="emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <FeederVisitorsList
          v-if="selectedObject.type === 'bird_feeder'"
          :foods="selectedObject.foods"
          :likelihood-data="feederLikelihoodData"
          :loading="isFeederLikelihoodLoading"
          :error="feederLikelihoodError"
        />

        <div class="collapsible-details-section">
          <button
            type="button"
            class="collapsible-toggle-bar"
            :class="{ open: !isEditDetailsCollapsed }"
            @click="emit('update:isEditDetailsCollapsed', !isEditDetailsCollapsed)"
          >
            <div class="toggle-left">
              <span class="toggle-icon">⚙️</span>
              <span class="toggle-title">
                {{
                  selectedObject.type === 'bird_feeder'
                    ? 'Feeder Settings & Foods'
                    : 'Object Settings'
                }}
              </span>
              <span
                v-if="
                  isEditDetailsCollapsed &&
                  selectedObject.type === 'bird_feeder' &&
                  selectedObject.foods?.length
                "
                class="toggle-summary-badge"
              >
                {{ selectedObject.foods.length }} food{{
                  selectedObject.foods.length > 1 ? 's' : ''
                }}
                configured
              </span>
            </div>
            <span class="toggle-arrow">{{ isEditDetailsCollapsed ? '▾' : '▴' }}</span>
          </button>

          <div v-show="!isEditDetailsCollapsed" class="collapsible-content-body">
            <div class="form-group">
              <label class="form-label">Category</label>
              <div class="type-selector-pills">
                <button
                  v-for="t in HABITAT_OBJECT_TYPES"
                  :key="t.id"
                  type="button"
                  :class="['type-pill', { active: selectedObject.type === t.id }]"
                  :style="{ '--type-color': t.color }"
                  @click="emit('change-type', t.id)"
                >
                  <span class="pill-icon">{{ t.icon }}</span>
                  <span>{{ t.name }}</span>
                </button>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Name / Label</label>
              <input
                v-model="selectedObject.name"
                type="text"
                class="form-input"
                placeholder="e.g. Backyard Tube Feeder"
              />
            </div>

            <FoodMultiSelect
              v-if="selectedObject.type === 'bird_feeder'"
              :selected-foods="selectedObject.foods"
              :open="isFoodDropdownOpen"
              @update:open="emit('update:isFoodDropdownOpen', $event)"
              @toggle-food="emit('toggle-food', $event)"
              @clear-foods="emit('clear-foods')"
            />

            <div v-else class="form-group">
              <label class="form-label">Style / Model</label>
              <select v-model="selectedObject.variant" class="form-select">
                <option
                  v-for="v in getObjectTypeDef(selectedObject.type).variants"
                  :key="v"
                  :value="v"
                >
                  {{ v }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Notes &amp; Observations</label>
              <textarea
                v-model="selectedObject.notes"
                class="form-textarea"
                rows="3"
                placeholder="e.g. Filled with black oil sunflower seeds; cleaned bi-weekly. Attracts Chickadees and Nuthatches."
              ></textarea>
            </div>

            <div class="location-hint">
              <span class="hint-icon">💡</span>
              <span>Tip: Drag the pin on the map anytime to reposition it.</span>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn-danger" @click="emit('delete', selectedObject)">
          🗑 Delete Object
        </button>
        <button type="button" class="btn-primary" @click="emit('save')">✓ Save &amp; Close</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.object-modal-overlay {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.object-modal-card {
  background-color: #14241d;
  border: 1px solid var(--border-sage);
  border-radius: 10px;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65), 0 0 20px rgba(82, 183, 136, 0.15);
  max-width: 560px;
  width: 100%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalFadeIn 0.18s ease-out;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(6px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1.2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background-color: rgba(0, 0, 0, 0.2);
}

.modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.modal-type-icon {
  font-size: 1.3rem;
}

.modal-title-wrap h3 {
  font-size: 1rem;
  font-weight: 700;
  color: #e8f5e9;
  margin: 0;
}

.modal-close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
}

.modal-close-btn:hover {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.1);
}

.modal-body {
  padding: 1.1rem 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  overflow-y: auto;
  max-height: 70vh;
}

.type-selector-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.type-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.65rem;
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-cream);
  background-color: rgba(0, 0, 0, 0.35);
  border: 1.5px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.type-pill:hover {
  border-color: var(--type-color);
  background-color: rgba(0, 0, 0, 0.55);
}

.type-pill.active {
  border-color: var(--type-color);
  background-color: rgba(255, 255, 255, 0.12);
  color: #fff;
  box-shadow: 0 0 10px var(--type-color);
}

.location-hint {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  padding: 0.5rem 0.7rem;
  background-color: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 6px;
  font-size: 0.72rem;
  color: #fef3c7;
  line-height: 1.4;
}

.hint-icon {
  font-size: 0.85rem;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background-color: rgba(0, 0, 0, 0.2);
}

.collapsible-details-section {
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
}

.collapsible-toggle-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.65rem 0.85rem;
  background: rgba(0, 0, 0, 0.25);
  border: none;
  color: var(--text-cream);
  cursor: pointer;
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  transition: background-color 0.15s ease;
  user-select: none;
}

.collapsible-toggle-bar:hover,
.collapsible-toggle-bar.open {
  background: rgba(82, 183, 136, 0.12);
  color: #fff;
}

.toggle-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.toggle-icon {
  font-size: 0.95rem;
}

.toggle-title {
  letter-spacing: 0.02em;
}

.toggle-summary-badge {
  font-size: 0.65rem;
  font-weight: 600;
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.18);
  border: 1px solid rgba(245, 158, 11, 0.35);
  padding: 0.08rem 0.45rem;
  border-radius: 999px;
}

.toggle-arrow {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.collapsible-content-body {
  padding: 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.15);
}
</style>
