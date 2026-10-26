<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useAddressAutocomplete } from '../../composables/useAddressAutocomplete.js'

const emit = defineEmits(['submitted'])

const wrapperRef = ref(null)
const {
  address,
  savedAddress,
  statusMessage,
  suggestions,
  showDropdown,
  activeIndex,
  isLoadingSuggestions,
  loadInitialAddress,
  onInput,
  selectSuggestion,
  onKeydown,
  submitAddress,
  closeDropdown,
  cleanup,
} = useAddressAutocomplete()

function handleOutsideClick(event) {
  if (wrapperRef.value && !wrapperRef.value.contains(event.target)) {
    closeDropdown()
  }
}

async function handleSubmit() {
  const ok = await submitAddress()
  if (ok) {
    emit('submitted', savedAddress.value)
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
  loadInitialAddress()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
  cleanup()
})
</script>

<template>
  <div>
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
          v-else-if="
            showDropdown &&
            !isLoadingSuggestions &&
            address.trim().length >= 3 &&
            suggestions.length === 0
          "
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
  </div>
</template>

<style scoped>
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
