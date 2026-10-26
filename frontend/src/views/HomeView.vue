<script setup>
import { useRouter } from 'vue-router'
import AddressAutocomplete from '../components/home/AddressAutocomplete.vue'

const router = useRouter()

function onAddressSubmitted() {
  router.push('/map')
}
</script>

<template>
  <section class="home">
    <h1>Hello, World!</h1>
    <p class="subtitle">Welcome to Harmonee.</p>

    <div class="supported-counties-note">
      <span class="note-badge">Supported Areas</span>
      <p class="note-text">
        Harmonee currently supports properties in <strong>Lehigh County</strong> and <strong>Montgomery County</strong>, PA.
      </p>
    </div>

    <AddressAutocomplete @submitted="onAddressSubmitted" />
  </section>
</template>

<style scoped>
.home {
  width: 100%;
  max-width: 560px;
}

h1 {
  font-size: 3rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
}

.subtitle {
  font-size: 1.25rem;
  color: var(--text-muted);
  margin: 0 0 1.5rem 0;
}

.supported-counties-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  background-color: rgba(38, 72, 59, 0.75);
  border: 1px solid var(--border-sage);
  border-radius: 8px;
  padding: 0.65rem 1rem;
  margin: 0 auto 1.75rem auto;
  text-align: left;
}

.note-badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  background-color: rgba(212, 163, 115, 0.18);
  border: 1px solid rgba(212, 163, 115, 0.4);
  color: var(--accent-earth);
  white-space: nowrap;
}

.note-text {
  margin: 0;
  font-size: 0.92rem;
  color: var(--text-cream);
  line-height: 1.4;
}

.note-text strong {
  color: #ffffff;
  font-weight: 600;
}
</style>
