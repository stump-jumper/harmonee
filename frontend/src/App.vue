<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isFullBleed = computed(() => route.name === 'map')
</script>

<template>
  <div :class="['layout', { 'layout-locked': isFullBleed }]">
    <header class="navbar">
      <RouterLink to="/" class="brand">Harmonee</RouterLink>
      <nav class="nav-links">
        <RouterLink to="/map" class="nav-item">Map</RouterLink>
        <RouterLink to="/monitor" class="nav-item">Monitor</RouterLink>
        <RouterLink to="/plan" class="nav-item">Plan</RouterLink>
        <RouterLink to="/act" class="nav-item">Act</RouterLink>
      </nav>
    </header>

    <main :class="isFullBleed ? 'full-bleed' : 'container'">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.layout-locked {
  height: 100vh;
  overflow: hidden;
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  border-bottom: 1px solid var(--border-sage);
  background-color: var(--bg-green);
  z-index: 10;
}

.brand {
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.nav-links {
  display: flex;
  gap: 0.5rem;
}

.nav-item {
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 0.95rem;
}

.nav-item.router-link-active {
  background-color: var(--surface-green);
  color: var(--text-cream);
  border: 1px solid var(--border-sage);
}

.container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
  text-align: center;
}

.full-bleed {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  overflow: hidden;
}
</style>
