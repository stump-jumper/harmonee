import test from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'

import {
  buildObservationPopupHtml,
  useInaturalistObservations,
} from '../src/composables/useInaturalistObservations.js'
import {
  fetchInaturalistObservations,
  fetchInaturalistUsername,
  saveInaturalistUsername,
} from '../src/api/inaturalistApi.js'

test('buildObservationPopupHtml creates formatted html with taxon details', () => {
  const sampleObs = {
    id: 98765,
    speciesGuess: 'Common Milkweed',
    taxon: {
      name: 'Asclepias syriaca',
      preferredCommonName: 'Common Milkweed',
      iconicTaxonName: 'Plantae',
      photoUrl: 'https://example.com/milkweed.jpg',
    },
    qualityGrade: 'research',
    insideProperty: true,
    distanceMiles: 0.01,
    observedOn: '2026-06-15',
    user: { login: 'paden', name: 'Paden T' },
    description: 'Pollinator border planting',
    uri: 'https://www.inaturalist.org/observations/98765',
  }

  const html = buildObservationPopupHtml(sampleObs)
  assert.ok(html.includes('Common Milkweed'))
  assert.ok(html.includes('Asclepias syriaca'))
  assert.ok(html.includes('Research Grade'))
  assert.ok(html.includes('On Property'))
  assert.ok(html.includes('Paden T'))
  assert.ok(html.includes('https://www.inaturalist.org/observations/98765'))
})

test('useInaturalistObservations manages category filtering and scope', () => {
  const mapRef = ref(null)
  let toggledLayerVisibility = null

  const {
    inaturalistData,
    activeCategory,
    propertyOnly,
    scope,
    filteredObservations,
    togglePanel,
    isPanelExpanded,
    syncWithLayerToggle,
  } = useInaturalistObservations(mapRef, {
    isLayerVisible: () => true,
    setLayerVisibility: (layerId, visible) => {
      toggledLayerVisibility = { layerId, visible }
    },
  })

  // Set mock data
  inaturalistData.value = {
    totalObservations: 4,
    observations: [
      {
        id: 1,
        speciesGuess: 'Common Milkweed',
        taxon: { name: 'Asclepias syriaca', iconicTaxonName: 'Plantae' },
      },
      {
        id: 2,
        speciesGuess: 'Monarch',
        taxon: { name: 'Danaus plexippus', iconicTaxonName: 'Insecta' },
      },
      {
        id: 3,
        speciesGuess: 'Northern Cardinal',
        taxon: { name: 'Cardinalis cardinalis', iconicTaxonName: 'Aves' },
      },
      {
        id: 4,
        speciesGuess: 'Eastern Chipmunk',
        taxon: { name: 'Tamias striatus', iconicTaxonName: 'Mammalia' },
      },
    ],
  }

  // All category
  assert.equal(activeCategory.value, 'all')
  assert.equal(scope.value, 'property')
  assert.equal(propertyOnly.value, true)
  assert.equal(filteredObservations.value.length, 4)

  // Plantae category
  activeCategory.value = 'Plantae'
  assert.equal(filteredObservations.value.length, 1)
  assert.equal(filteredObservations.value[0].speciesGuess, 'Common Milkweed')

  // Other category (mammals, etc.)
  activeCategory.value = 'Other'
  assert.equal(filteredObservations.value.length, 1)
  assert.equal(filteredObservations.value[0].speciesGuess, 'Eastern Chipmunk')

  // Toggle panel
  assert.equal(isPanelExpanded.value, false)
  togglePanel()
  assert.equal(isPanelExpanded.value, true)
  assert.deepEqual(toggledLayerVisibility, {
    layerId: 'inaturalist-observations-layer',
    visible: true,
  })

  // Sync with layer toggle
  syncWithLayerToggle(false)
  assert.equal(isPanelExpanded.value, false)
})

test('inaturalistApi query functions build correct endpoints', async () => {
  let capturedUrl = ''
  let capturedOptions = null

  globalThis.fetch = async (url, options) => {
    capturedUrl = url
    capturedOptions = options
    return {
      ok: true,
      json: async () => ({ status: 'ok', username: 'troxellp' }),
    }
  }

  // fetchInaturalistObservations
  await fetchInaturalistObservations({
    username: 'troxellp',
    propertyOnly: true,
    radiusMiles: 0.5,
    scope: 'property',
    lat: 40.63,
    lon: -75.55,
  })
  assert.ok(capturedUrl.includes('/api/inaturalist/observations'))
  assert.ok(capturedUrl.includes('username=troxellp'))
  assert.ok(capturedUrl.includes('property_only=true'))
  assert.ok(capturedUrl.includes('scope=property'))
  assert.ok(capturedUrl.includes('lat=40.63'))
  assert.ok(capturedUrl.includes('lon=-75.55'))

  // saveInaturalistUsername
  await saveInaturalistUsername('steward42')
  assert.equal(capturedUrl, '/api/inaturalist/username')
  assert.equal(capturedOptions.method, 'POST')
  assert.ok(capturedOptions.body.includes('steward42'))

  // fetchInaturalistUsername
  await fetchInaturalistUsername()
  assert.equal(capturedUrl, '/api/inaturalist/username')
})
