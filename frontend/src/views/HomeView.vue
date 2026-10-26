<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const address = ref('')
const selectedCoords = ref({ lat: null, lon: null })
const savedAddress = ref('')
const statusMessage = ref('')

const suggestions = ref([])
const showDropdown = ref(false)
const activeIndex = ref(-1)
const isLoadingSuggestions = ref(false)
const wrapperRef = ref(null)

let debounceTimer = null

onMounted(async () => {
  document.addEventListener('click', handleOutsideClick)
  try {
    const res = await fetch('/api/address')
    if (res.ok) {
      const data = await res.json()
      if (data.address) {
        address.value = data.address
        savedAddress.value = data.address
        selectedCoords.value = { lat: data.lat ?? null, lon: data.lon ?? null }
      }
    }
  } catch {
    const local = localStorage.getItem('harmonee_address')
    if (local) {
      address.value = local
      savedAddress.value = local
    }
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
  if (debounceTimer) clearTimeout(debounceTimer)
})

function handleOutsideClick(event) {
  if (wrapperRef.value && !wrapperRef.value.contains(event.target)) {
    showDropdown.value = false
  }
}

function onInput() {
  statusMessage.value = ''
  selectedCoords.value = { lat: null, lon: null }
  const query = address.value.trim()

  if (debounceTimer) clearTimeout(debounceTimer)
  if (query.length < 3) {
    suggestions.value = []
    showDropdown.value = false
    activeIndex.value = -1
    return
  }

  debounceTimer = setTimeout(() => {
    fetchSuggestions(query)
  }, 250)
}

async function fetchSuggestions(query) {
  isLoadingSuggestions.value = true
  try {
    const res = await fetch(`/api/address/autocomplete?q=${encodeURIComponent(query)}`)
    if (res.ok) {
      const data = await res.json()
      suggestions.value = data.suggestions || []
      showDropdown.value = true
      activeIndex.value = -1
    }
  } catch {
    suggestions.value = []
    showDropdown.value = false
  } finally {
    isLoadingSuggestions.value = false
  }
}

function selectSuggestion(item) {
  address.value = item.label
  selectedCoords.value = { lat: item.lat ?? null, lon: item.lon ?? null }
  suggestions.value = []
  showDropdown.value = false
  activeIndex.value = -1
}

function onKeydown(event) {
  if (!showDropdown.value || suggestions.value.length === 0) return

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % suggestions.value.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value =
      activeIndex.value <= 0 ? suggestions.value.length - 1 : activeIndex.value - 1
  } else if (event.key === 'Enter' && activeIndex.value >= 0) {
    event.preventDefault()
    selectSuggestion(suggestions.value[activeIndex.value])
  } else if (event.key === 'Escape') {
    showDropdown.value = false
    activeIndex.value = -1
  }
}

async function handleSubmit() {
  const trimmed = address.value.trim()
  if (!trimmed) return

  showDropdown.value = false
  localStorage.setItem('harmonee_address', trimmed)
  try {
    const res = await fetch('/api/address', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address: trimmed,
        lat: selectedCoords.value.lat,
        lon: selectedCoords.value.lon,
      }),
    })
    if (res.ok) {
      const data = await res.json()
      savedAddress.value = data.address
    } else {
      savedAddress.value = trimmed
    }
  } catch {
    savedAddress.value = trimmed
  }

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

    <form class="address-form" @submit.prevent="handleSubmit">
      <div ref="wrapperRef" class="autocomplete-wrapper">
        <label for="home-address" class="sr-only">Enter your home address</label>
        <input
          id="home-address"
          v-model="address"
          type="text"
          autocomplete="off"
          placeholder="Enter an address in Lehigh or Montgomery County..."
          required
          @input="onInput"
          @keydown="onKeydown"
          @focus="suggestions.length > 0 && (showDropdown = true)"
        />

        <ul v-if="showDropdown && suggestions.length > 0" class="suggestions-list" role="listbox">
          <li
            v-for="(item, index) in suggestions"
            :key="item.label"
            :class="['suggestion-item', { active: index === activeIndex }]"
            role="option"
            :aria-selected="index === activeIndex"
            @mousedown.prevent="selectSuggestion(item)"
            @mouseenter="activeIndex = index"
          >
            <div class="suggestion-main">
              <span class="suggestion-label">{{ item.label }}</span>
              <span v-if="item.county" class="suggestion-county">{{ item.county }}</span>
            </div>
          </li>
        </ul>

        <ul
          v-else-if="showDropdown && !isLoadingSuggestions && address.trim().length >= 3 && suggestions.length === 0"
          class="suggestions-list"
        >
          <li class="no-suggestions">
            No matching addresses found in Lehigh or Montgomery County
          </li>
        </ul>
      </div>

      <button type="submit">Get Started</button>
    </form>

    <p v-if="statusMessage" class="saved-note">
      {{ statusMessage }} ({{ savedAddress }})
    </p>
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

.address-form {
  display: flex;
  gap: 0.5rem;
  width: 100%;
  align-items: flex-start;
}

.autocomplete-wrapper {
  position: relative;
  flex: 1;
}

.autocomplete-wrapper input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  font-family: inherit;
  color: var(--text-cream);
  background-color: var(--surface-green);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
  outline: none;
}

.autocomplete-wrapper input::placeholder {
  color: var(--text-muted);
  opacity: 0.75;
}

.autocomplete-wrapper input:focus {
  border-color: var(--text-cream);
}

.suggestions-list {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  margin: 0;
  padding: 0.25rem 0;
  list-style: none;
  background-color: var(--surface-green);
  border: 1px solid var(--border-sage);
  border-radius: 6px;
  text-align: left;
  z-index: 20;
  max-height: 240px;
  overflow-y: auto;
}

.suggestion-item {
  padding: 0.65rem 1rem;
  font-size: 0.95rem;
  color: var(--text-cream);
  cursor: pointer;
  border-bottom: 1px solid rgba(61, 102, 86, 0.4);
}

.suggestion-item:last-child {
  border-bottom: none;
}

.suggestion-item.active,
.suggestion-item:hover {
  background-color: var(--bg-green);
}

.suggestion-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
}

.suggestion-label {
  flex: 1;
  text-align: left;
  line-height: 1.35;
}

.suggestion-county {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--accent-earth);
  background-color: rgba(212, 163, 115, 0.15);
  border: 1px solid rgba(212, 163, 115, 0.35);
  border-radius: 4px;
  padding: 0.15rem 0.45rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.no-suggestions {
  padding: 0.85rem 1rem;
  font-size: 0.9rem;
  color: var(--text-muted);
  font-style: italic;
  text-align: center;
}

.address-form button {
  padding: 0.75rem 1.25rem;
  font-size: 1rem;
  font-weight: 600;
  font-family: inherit;
  color: var(--bg-green);
  background-color: var(--text-cream);
  border: 1px solid var(--text-cream);
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}

.address-form button:hover {
  opacity: 0.92;
}

.saved-note {
  margin-top: 1rem;
  font-size: 0.95rem;
  color: var(--text-muted);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}
</style>
