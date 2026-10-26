<script setup>
defineProps({
  address: { type: String, default: '' },
  acreage: { type: String, default: null },
})
</script>

<template>
  <div v-if="address" class="map-panel info-panel">
    <div class="panel-heading">Property Info</div>
    <div class="address-text">{{ address }}</div>
    <div v-if="acreage" class="acreage-text">Parcel Size: {{ acreage }}</div>
  </div>
</template>

<style scoped>
.address-text {
  font-size: 0.9rem;
  color: var(--text-cream);
  line-height: 1.35;
}

.acreage-text {
  margin-top: 0.35rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}
</style>
