<script setup>
import { computed, ref, watch } from 'vue'
import { INATURALIST_TAXA, getIconicTaxonIcon } from '../../constants/mapConstants.js'
import { formatSightingDate } from '../../utils/formatters.js'

const props = defineProps({
  loading: { type: Boolean, default: false },
  observationsData: { type: Object, default: null },
  expanded: { type: Boolean, default: false },
  activeCategory: { type: String, default: 'all' },
  scope: { type: String, default: 'property' },
  filteredList: { type: Array, default: () => [] },
  selectedObservationId: { type: [Number, String], default: null },
})

const emit = defineEmits([
  'toggle-expand',
  'update:activeCategory',
  'update:scope',
  'select-observation',
  'update-username',
  'refresh',
])

const isEditingUser = ref(false)
const localUsernameInput = ref('')

const observerLogin = computed(() => {
  return props.observationsData?.observer?.login || 'troxellp'
})

watch(
  () => props.observationsData?.observer?.login,
  (newVal) => {
    if (newVal) localUsernameInput.value = newVal
  },
  { immediate: true }
)

function startEditing() {
  localUsernameInput.value = observerLogin.value
  isEditingUser.value = true
}

function cancelEditing() {
  isEditingUser.value = false
  localUsernameInput.value = observerLogin.value
}

function submitUsername() {
  if (localUsernameInput.value.trim()) {
    emit('update-username', localUsernameInput.value.trim())
    isEditingUser.value = false
  }
}

function getTaxonCount(taxaId) {
  if (!props.observationsData) return 0
  if (taxaId === 'all') {
    return props.observationsData.totalObservations || 0
  }
  const counts = props.observationsData.iconicTaxaCounts || {}
  return counts[taxaId] || 0
}
</script>

<template>
  <div class="map-panel inat-panel">
    <div
      class="panel-header-row clickable-header"
      title="Click to expand/collapse iNaturalist observations"
      @click="emit('toggle-expand')"
    >
      <div class="panel-title-wrap">
        <span class="inat-badge-icon">🌿</span>
        <div>
          <div class="panel-heading">iNaturalist Observations</div>
          <div class="inat-subtitle">
            <span v-if="scope === 'property'">Property boundary records</span>
            <span v-else-if="scope === 'vicinity'">Property & vicinity (0.5 mi)</span>
            <span v-else>All observer records</span>
            • @{{ observerLogin }}
          </div>
        </div>
      </div>
      <div class="panel-header-actions">
        <button
          type="button"
          class="panel-refresh-btn"
          title="Refresh iNaturalist observations"
          :disabled="loading"
          @click.stop="emit('refresh')"
        >
          <span :class="['refresh-icon', { spinning: loading }]">↻</span>
        </button>
        <span v-if="loading" class="inat-count-badge loading">Loading...</span>
        <span v-else-if="observationsData" class="inat-count-badge">
          {{ observationsData.totalObservations }} records
        </span>
        <span class="expand-chevron">{{ expanded ? '▾' : '▸' }}</span>
      </div>
    </div>

    <template v-if="expanded">
      <!-- Observer Account Bar -->
      <div class="inat-user-bar">
        <div v-if="!isEditingUser" class="inat-user-display">
          <span class="inat-user-label">
            Observer:
            <strong class="inat-username-tag">@{{ observerLogin }}</strong>
            <span v-if="observationsData?.observer?.tokenConfigured" class="inat-auth-pill">
              API Token Active
            </span>
          </span>
          <button
            type="button"
            class="inat-edit-user-btn"
            title="Link another iNaturalist username"
            @click="startEditing"
          >
            ✏️ Change
          </button>
        </div>
        <div v-else class="inat-user-form">
          <input
            v-model="localUsernameInput"
            type="text"
            class="inat-user-input"
            placeholder="iNaturalist username"
            @keydown.enter.prevent="submitUsername"
            @keydown.esc="cancelEditing"
          />
          <button type="button" class="inat-save-btn" @click="submitUsername">Save</button>
          <button type="button" class="inat-cancel-btn" @click="cancelEditing">✕</button>
        </div>
      </div>

      <!-- Scope Toggle Bar: On Property vs Vicinity vs All User Obs -->
      <div class="inat-scope-nav">
        <button
          type="button"
          :class="['inat-scope-btn', { active: scope === 'property' }]"
          @click="emit('update:scope', 'property')"
        >
          🏡 On Property
        </button>
        <button
          type="button"
          :class="['inat-scope-btn', { active: scope === 'vicinity' }]"
          @click="emit('update:scope', 'vicinity')"
        >
          🌐 Vicinity (0.5 mi)
        </button>
        <button
          type="button"
          :class="['inat-scope-btn', { active: scope === 'all_user' }]"
          @click="emit('update:scope', 'all_user')"
        >
          👤 All Records
        </button>
      </div>

      <!-- Summary Stats Metrics -->
      <div v-if="observationsData" class="inat-stats-grid">
        <div class="inat-stat-cell">
          <span class="inat-stat-val">{{ observationsData.totalObservations }}</span>
          <span class="inat-stat-lbl">Observations</span>
        </div>
        <div class="inat-stat-cell">
          <span class="inat-stat-val">{{ observationsData.speciesCount }}</span>
          <span class="inat-stat-lbl">Species</span>
        </div>
        <div class="inat-stat-cell">
          <span class="inat-stat-val highlight">{{ observationsData.researchGradePercent }}%</span>
          <span class="inat-stat-lbl">Research Grade</span>
        </div>
      </div>

      <!-- Category Filter Pills -->
      <div class="inat-taxa-nav">
        <button
          v-for="t in INATURALIST_TAXA"
          :key="t.id"
          type="button"
          :class="['inat-taxa-pill', { active: activeCategory === t.id }]"
          @click="emit('update:activeCategory', t.id)"
        >
          <span>{{ t.icon }} {{ t.label }}</span>
          <span v-if="getTaxonCount(t.id) > 0" class="inat-taxa-count">
            {{ getTaxonCount(t.id) }}
          </span>
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="inat-loading-state">
        <span class="inat-spinner"></span>
        <span>Loading observations...</span>
      </div>

      <!-- Observations List -->
      <div v-else-if="filteredList.length > 0" class="inat-items-list">
        <div
          v-for="obs in filteredList"
          :key="obs.id"
          :class="[
            'inat-item-card',
            { active: selectedObservationId === obs.id },
          ]"
          title="Click to view observation on map"
          @click="emit('select-observation', obs)"
        >
          <div class="inat-thumb-container">
            <img
              v-if="obs.taxon?.photoUrl || obs.photos?.[0]?.url"
              :src="obs.taxon?.photoUrl || obs.photos?.[0]?.url"
              :alt="obs.speciesGuess"
              class="inat-card-thumb"
              loading="lazy"
              onerror="this.style.display='none'; if(this.nextElementSibling) this.nextElementSibling.style.display='flex';"
            />
            <div class="inat-card-thumb-fallback">
              {{ getIconicTaxonIcon(obs.taxon?.iconicTaxonName) }}
            </div>
          </div>

          <div class="inat-item-body">
            <div class="inat-item-header">
              <span class="inat-item-name" :title="obs.speciesGuess">
                {{ obs.speciesGuess || obs.taxon?.preferredCommonName }}
              </span>
              <span v-if="obs.insideProperty" class="inat-pill-tag prop-pill">On Property</span>
              <span v-else class="inat-pill-tag dist-pill">
                {{ (obs.distanceMiles ?? 0).toFixed(2) }} mi
              </span>
            </div>

            <div class="inat-item-sci" :title="obs.taxon?.name">
              {{ obs.taxon?.name }}
            </div>

            <div class="inat-item-badges">
              <span
                :class="[
                  'inat-quality-badge',
                  obs.isResearchGrade ? 'badge-research' : 'badge-needs-id',
                ]"
              >
                {{ obs.isResearchGrade ? '✓ Research Grade' : 'Needs ID' }}
              </span>
              <span class="inat-date-badge">{{ formatSightingDate(obs.observedOn) }}</span>
            </div>
          </div>

          <div class="inat-item-actions">
            <span class="inat-locate-btn" title="Pan to observation on map">🎯</span>
            <a
              v-if="obs.uri"
              :href="obs.uri"
              target="_blank"
              rel="noopener noreferrer"
              class="inat-link-btn"
              title="Open observation on iNaturalist"
              @click.stop
            >
              ↗
            </a>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="inat-empty-state">
        No iNaturalist records found for this category on the property.
      </div>
    </template>
  </div>
</template>

<style scoped>
.inat-panel {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  position: relative;
  z-index: 25;
}

.panel-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.panel-header-row.clickable-header {
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
  padding: 2px 3px;
  margin: -2px -3px;
  transition: opacity 0.15s ease, background-color 0.15s ease;
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

.inat-badge-icon {
  font-size: 1.15rem;
  line-height: 1;
  margin-top: 1px;
}

.inat-subtitle {
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
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.45);
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

.inat-count-badge {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  background-color: rgba(34, 197, 94, 0.16);
  border: 1px solid rgba(34, 197, 94, 0.4);
  color: #4ade80;
  white-space: nowrap;
}

.inat-count-badge.loading {
  background-color: rgba(245, 158, 11, 0.16);
  border-color: rgba(245, 158, 11, 0.4);
  color: #fbbf24;
}

.expand-chevron {
  font-size: 0.85rem;
  font-weight: 700;
  color: #4ade80;
  transition: transform 0.2s ease;
  line-height: 1;
}

/* User Linking Bar */
.inat-user-bar {
  background-color: rgba(18, 36, 29, 0.7);
  border: 1px solid rgba(61, 102, 86, 0.4);
  border-radius: 6px;
  padding: 0.35rem 0.55rem;
}

.inat-user-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.74rem;
}

.inat-user-label {
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.inat-username-tag {
  color: #4ade80;
  font-weight: 600;
}

.inat-auth-pill {
  font-size: 0.62rem;
  color: #38bdf8;
  background-color: rgba(56, 189, 248, 0.14);
  padding: 1px 5px;
  border-radius: 6px;
  font-weight: 600;
}

.inat-edit-user-btn {
  background: transparent;
  border: none;
  color: var(--text-cream);
  font-size: 0.7rem;
  cursor: pointer;
  padding: 2px 5px;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}

.inat-edit-user-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #4ade80;
}

.inat-user-form {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.inat-user-input {
  flex: 1;
  background-color: rgba(10, 24, 18, 0.9);
  border: 1px solid #22c55e;
  border-radius: 4px;
  color: var(--text-cream);
  font-size: 0.74rem;
  padding: 3px 6px;
  outline: none;
}

.inat-save-btn {
  background-color: #16a34a;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}

.inat-save-btn:hover {
  background-color: #22c55e;
}

.inat-cancel-btn {
  background: transparent;
  color: var(--text-muted);
  border: none;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 2px 4px;
}

.inat-cancel-btn:hover {
  color: var(--text-cream);
}

/* Scope Toggle: On Property vs Vicinity vs All */
.inat-scope-nav {
  display: flex;
  gap: 0.25rem;
  background-color: rgba(18, 36, 29, 0.75);
  padding: 3px;
  border-radius: 6px;
  border: 1px solid rgba(61, 102, 86, 0.45);
}

.inat-scope-btn {
  flex: 1;
  padding: 4px 4px;
  font-size: 0.69rem;
  font-weight: 600;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: center;
  white-space: nowrap;
}

.inat-scope-btn:hover {
  color: var(--text-cream);
  background-color: rgba(255, 255, 255, 0.06);
}

.inat-scope-btn.active {
  background-color: #15803d;
  color: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
}

/* Stats Grid */
.inat-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.35rem;
  background-color: rgba(18, 36, 29, 0.6);
  padding: 0.45rem;
  border-radius: 6px;
  border: 1px solid rgba(61, 102, 86, 0.35);
}

.inat-stat-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.inat-stat-val {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-cream);
  line-height: 1.1;
}

.inat-stat-val.highlight {
  color: #4ade80;
}

.inat-stat-lbl {
  font-size: 0.65rem;
  color: var(--text-muted);
  margin-top: 1px;
}

/* Taxa Nav Pills */
.inat-taxa-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.inat-taxa-pill {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 3px 6px;
  font-size: 0.68rem;
  font-weight: 600;
  border: 1px solid rgba(61, 102, 86, 0.45);
  border-radius: 12px;
  background-color: rgba(18, 36, 29, 0.65);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.inat-taxa-pill:hover {
  color: var(--text-cream);
  border-color: #22c55e;
}

.inat-taxa-pill.active {
  background-color: rgba(34, 197, 94, 0.22);
  border-color: #22c55e;
  color: #ffffff;
}

.inat-taxa-count {
  font-size: 0.62rem;
  background-color: rgba(255, 255, 255, 0.15);
  padding: 1px 4px;
  border-radius: 6px;
}

/* Loading */
.inat-loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 0.75rem 0;
}

.inat-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(34, 197, 94, 0.3);
  border-top-color: #22c55e;
  border-radius: 50%;
  animation: inat-spin 0.8s linear infinite;
}

@keyframes inat-spin {
  to {
    transform: rotate(360deg);
  }
}

/* Items List */
.inat-items-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-height: 290px;
  overflow-y: auto;
  padding-right: 2px;
}

.inat-item-card {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.55rem;
  background-color: rgba(22, 44, 35, 0.75);
  border: 1px solid rgba(61, 102, 86, 0.5);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.inat-item-card:hover {
  background-color: rgba(30, 60, 48, 0.95);
  border-color: #22c55e;
  transform: translateY(-1px);
}

.inat-item-card.active {
  background-color: rgba(34, 197, 94, 0.2);
  border-color: #22c55e;
  box-shadow: 0 0 0 1px #22c55e;
}

.inat-thumb-container {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  overflow: hidden;
  background-color: rgba(10, 24, 18, 0.9);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.inat-card-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.inat-card-thumb-fallback {
  font-size: 1.1rem;
}

.inat-item-body {
  flex: 1;
  min-width: 0;
}

.inat-item-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.3rem;
}

.inat-item-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-cream);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.inat-pill-tag {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 8px;
  flex-shrink: 0;
}

.prop-pill {
  color: #4ade80;
  background-color: rgba(34, 197, 94, 0.15);
}

.dist-pill {
  color: #38bdf8;
  background-color: rgba(56, 189, 248, 0.12);
}

.inat-item-sci {
  font-size: 0.7rem;
  font-style: italic;
  color: var(--text-muted);
  margin-bottom: 0.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.inat-item-badges {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.inat-quality-badge {
  font-size: 0.62rem;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 4px;
}

.badge-research {
  background-color: rgba(34, 197, 94, 0.18);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.35);
}

.badge-needs-id {
  background-color: rgba(245, 158, 11, 0.18);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.35);
}

.inat-date-badge {
  font-size: 0.65rem;
  color: var(--text-muted);
}

.inat-item-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  flex-shrink: 0;
}

.inat-locate-btn {
  font-size: 0.85rem;
  cursor: pointer;
  opacity: 0.8;
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.inat-locate-btn:hover {
  opacity: 1;
  transform: scale(1.15);
}

.inat-link-btn {
  font-size: 0.75rem;
  color: #4ade80;
  text-decoration: none;
  opacity: 0.8;
  padding: 1px 3px;
  border-radius: 3px;
}

.inat-link-btn:hover {
  opacity: 1;
  background-color: rgba(34, 197, 94, 0.2);
}

.inat-empty-state {
  text-align: center;
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 1rem 0.5rem;
  font-style: italic;
}
</style>
