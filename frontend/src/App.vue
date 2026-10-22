<template>
  <div class="layout">
    <header class="navbar">
      <RouterLink to="/" class="brand">Harmonee</RouterLink>
      <nav class="nav-links">
        <RouterLink to="/map" class="nav-item">Map</RouterLink>
        <RouterLink to="/monitor" class="nav-item">Monitor</RouterLink>
        <RouterLink to="/plan" class="nav-item">Plan</RouterLink>
        <RouterLink to="/act" class="nav-item">Act</RouterLink>
      </nav>
    </header>

    <main class="container">
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

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  border-bottom: 1px solid var(--border-sage);
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
</style>
