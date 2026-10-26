<script setup>
import { formatSightingDate } from '../../utils/formatters.js'

defineProps({
  loading: { type: Boolean, default: false },
  sightingsData: { type: Object, default: null },
  expanded: { type: Boolean, default: false },
  activeTab: { type: String, default: 'recent' },
  topList: { type: Array, default: () => [] },
  selectedSightingId: { type: String, default: null },
})

const emit = defineEmits(['toggle-expand', 'update:activeTab', 'select-sighting'])
</script>

<template>
  <div class="map-panel ebird-panel">
    <div
      class="panel-header-row clickable-header"
      title="Click to expand/collapse local bird sightings"
      @click="emit('toggle-expand')"
    >
      <div class="panel-title-wrap">
        <span class="ebird-badge-icon">🪶</span>
        <div>
          <div class="panel-heading">Local Bird Sightings</div>
          <div class="ebird-subtitle">eBird • 1.0 mi radius • Last 30 days</div>
        </div>
      </div>
      <div class="panel-header-actions">
        <span v-if="loading" class="ebird-count-badge loading">Loading...</span>
        <span v-else-if="sightingsData" class="ebird-count-badge">
          {{ sightingsData.totalSightings }} spotted
        </span>
        <span class="expand-chevron">{{ expanded ? '▾' : '▸' }}</span>
      </div>
    </div>

    <template v-if="expanded">
      <div class="ebird-tabs-nav">
        <button
          type="button"
          :class="['ebird-tab-btn', { active: activeTab === 'recent' }]"
          @click="emit('update:activeTab', 'recent')"
        >
          🕒 Recent
        </button>
        <button
          type="button"
          :class="['ebird-tab-btn', { active: activeTab === 'closest' }]"
          @click="emit('update:activeTab', 'closest')"
        >
          📍 Closest
        </button>
        <button
          type="button"
          :class="['ebird-tab-btn', { active: activeTab === 'common' }]"
          @click="emit('update:activeTab', 'common')"
        >
          📊 Common
        </button>
      </div>

      <div v-if="loading" class="ebird-loading-state">
        <span class="ebird-spinner"></span>
        <span>Loading local sightings...</span>
      </div>

      <div v-else-if="topList.length > 0" class="ebird-items-list">
        <div
          v-for="(item, idx) in topList"
          :key="item.id || item.speciesCode || idx"
          :class="[
            'ebird-item-card',
            { active: selectedSightingId === (item.id || item.speciesCode) },
          ]"
          title="Click to view on map"
          @click="emit('select-sighting', item)"
        >
          <div class="card-item-rank">#{{ idx + 1 }}</div>
          <div class="card-item-body">
            <div class="card-item-header">
              <span class="card-item-name">{{ item.comName }}</span>
              <span class="card-item-dist-pill">
                {{ (item.minDistanceMiles ?? item.distanceMiles)?.toFixed(2) }} mi
              </span>
            </div>
            <div class="card-item-sci">{{ item.sciName }}</div>
            <div class="card-item-details">
              <template v-if="activeTab === 'common'">
                <span class="detail-badge common-badge">
                  {{ item.observationCount }} reports ({{ item.totalIndividuals }} birds)
                </span>
                <span class="detail-badge loc-badge" :title="item.locName">{{ item.locName }}</span>
              </template>
              <template v-else-if="activeTab === 'closest'">
                <span class="detail-badge dist-badge">{{ item.distanceMiles }} mi away</span>
                <span class="detail-badge date-badge">{{ formatSightingDate(item.obsDt) }}</span>
                <span class="detail-badge loc-badge" :title="item.locName">{{ item.locName }}</span>
              </template>
              <template v-else>
                <span class="detail-badge date-badge">{{ formatSightingDate(item.obsDt) }}</span>
                <span v-if="item.howMany" class="detail-badge count-badge">×{{ item.howMany }}</span>
                <span class="detail-badge loc-badge" :title="item.locName">{{ item.locName }}</span>
              </template>
            </div>
          </div>
          <div class="card-locate-icon" title="Pan to marker on map">🎯</div>
        </div>
      </div>

      <div v-else class="ebird-empty-state">
        No sightings recorded within 1.0 mile in the last 30 days.
      </div>
    </template>
  </div>
</template>

<style scoped>
.ebird-panel {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  border-left: 3px solid #38bdf8;
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

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.expand-chevron {
  font-size: 0.85rem;
  font-weight: 700;
  color: #38bdf8;
  transition: transform 0.2s ease;
  line-height: 1;
}

.panel-title-wrap {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
}

.ebird-badge-icon {
  font-size: 1.15rem;
  line-height: 1;
  margin-top: 1px;
}

.ebird-subtitle {
  font-size: 0.7rem;
  color: var(--text-muted);
  opacity: 0.9;
  margin-top: -0.2rem;
}

.ebird-count-badge {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  background-color: rgba(56, 189, 248, 0.16);
  border: 1px solid rgba(56, 189, 248, 0.4);
  color: #38bdf8;
  white-space: nowrap;
}

.ebird-count-badge.loading {
  background-color: rgba(245, 158, 11, 0.16);
  border-color: rgba(245, 158, 11, 0.4);
  color: #fbbf24;
}

.ebird-tabs-nav {
  display: flex;
  gap: 0.25rem;
  background-color: rgba(18, 36, 29, 0.75);
  padding: 3px;
  border-radius: 6px;
  border: 1px solid rgba(61, 102, 86, 0.45);
}

.ebird-tab-btn {
  flex: 1;
  padding: 4px 5px;
  font-size: 0.7rem;
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

.ebird-tab-btn:hover {
  color: var(--text-cream);
  background-color: rgba(255, 255, 255, 0.06);
}

.ebird-tab-btn.active {
  background-color: #0284c7;
  color: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
}

.ebird-loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 0.75rem 0;
}

.ebird-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(56, 189, 248, 0.3);
  border-top-color: #38bdf8;
  border-radius: 50%;
  animation: ebird-spin 0.8s linear infinite;
}

@keyframes ebird-spin {
  to {
    transform: rotate(360deg);
  }
}

.ebird-items-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-height: 275px;
  overflow-y: auto;
  padding-right: 2px;
}

.ebird-item-card {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  padding: 0.45rem 0.55rem;
  background-color: rgba(22, 44, 35, 0.75);
  border: 1px solid rgba(61, 102, 86, 0.5);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.ebird-item-card:hover {
  background-color: rgba(30, 60, 48, 0.95);
  border-color: #38bdf8;
  transform: translateY(-1px);
}

.ebird-item-card.active {
  background-color: rgba(2, 132, 199, 0.22);
  border-color: #38bdf8;
  box-shadow: 0 0 0 1px #38bdf8;
}

.card-item-rank {
  font-size: 0.68rem;
  font-weight: 700;
  color: #f2cc8f;
  background-color: rgba(242, 204, 143, 0.15);
  border-radius: 3px;
  padding: 1px 4px;
  line-height: 1.2;
  margin-top: 1px;
  flex-shrink: 0;
}

.card-item-body {
  flex: 1;
  min-width: 0;
}

.card-item-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.3rem;
}

.card-item-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-cream);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-item-dist-pill {
  font-size: 0.68rem;
  font-weight: 600;
  color: #38bdf8;
  background-color: rgba(56, 189, 248, 0.12);
  padding: 1px 5px;
  border-radius: 8px;
  flex-shrink: 0;
}

.card-item-sci {
  font-size: 0.7rem;
  font-style: italic;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-item-details {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.detail-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.67rem;
  background-color: rgba(18, 36, 29, 0.8);
  color: var(--text-muted);
  border: 1px solid rgba(61, 102, 86, 0.4);
}

.detail-badge.common-badge {
  color: #f2cc8f;
  border-color: rgba(242, 204, 143, 0.35);
  background-color: rgba(242, 204, 143, 0.1);
}

.detail-badge.dist-badge {
  color: #38bdf8;
  border-color: rgba(56, 189, 248, 0.3);
  background-color: rgba(56, 189, 248, 0.1);
}

.detail-badge.date-badge {
  color: #a7f3d0;
  border-color: rgba(167, 243, 208, 0.3);
  background-color: rgba(16, 185, 129, 0.1);
}

.detail-badge.count-badge {
  color: #f472b6;
  border-color: rgba(244, 114, 182, 0.35);
  background-color: rgba(244, 114, 182, 0.1);
}

.detail-badge.loc-badge {
  max-width: 140px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-locate-icon {
  font-size: 0.85rem;
  opacity: 0.45;
  transition: opacity 0.15s ease;
  align-self: center;
  flex-shrink: 0;
}

.ebird-item-card:hover .card-locate-icon {
  opacity: 1;
}

.ebird-empty-state {
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 0.6rem 0;
  text-align: center;
  line-height: 1.35;
}
</style>
