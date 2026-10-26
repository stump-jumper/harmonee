import { ref } from 'vue'
import {
  fetchAddressSuggestions,
  fetchPropertyData,
  savePropertyAddress,
} from '../api/propertyApi.js'

export function useAddressAutocomplete({ debounceMs = 250 } = {}) {
  const address = ref('')
  const selectedCoords = ref({ lat: null, lon: null })
  const savedAddress = ref('')
  const statusMessage = ref('')

  const suggestions = ref([])
  const showDropdown = ref(false)
  const activeIndex = ref(-1)
  const isLoadingSuggestions = ref(false)

  let debounceTimer = null

  async function loadInitialAddress() {
    try {
      const data = await fetchPropertyData()
      if (data.address) {
        address.value = data.address
        savedAddress.value = data.address
        selectedCoords.value = { lat: data.lat ?? null, lon: data.lon ?? null }
      }
    } catch {
      const local = globalThis.localStorage?.getItem('harmonee_address')
      if (local) {
        address.value = local
        savedAddress.value = local
      }
    }
  }

  async function loadSuggestions(query) {
    isLoadingSuggestions.value = true
    try {
      const list = await fetchAddressSuggestions(query)
      suggestions.value = list
      showDropdown.value = true
      activeIndex.value = -1
    } catch {
      suggestions.value = []
      showDropdown.value = false
    } finally {
      isLoadingSuggestions.value = false
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
      loadSuggestions(query)
    }, debounceMs)
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

  async function submitAddress() {
    const trimmed = address.value.trim()
    if (!trimmed) return false

    showDropdown.value = false
    globalThis.localStorage?.setItem('harmonee_address', trimmed)

    try {
      const data = await savePropertyAddress({
        address: trimmed,
        lat: selectedCoords.value.lat,
        lon: selectedCoords.value.lon,
      })
      savedAddress.value = data.address || trimmed
    } catch {
      savedAddress.value = trimmed
    }
    return true
  }

  function closeDropdown() {
    showDropdown.value = false
  }

  function cleanup() {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
  }

  return {
    address,
    selectedCoords,
    savedAddress,
    statusMessage,
    suggestions,
    showDropdown,
    activeIndex,
    isLoadingSuggestions,
    loadInitialAddress,
    loadSuggestions,
    onInput,
    selectSuggestion,
    onKeydown,
    submitAddress,
    closeDropdown,
    cleanup,
  }
}
