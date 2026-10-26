import test from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'

import { useMapLayers } from '../src/composables/useMapLayers.js'
import { useHabitatPaint } from '../src/composables/useHabitatPaint.js'
import { useHabitatObjects } from '../src/composables/useHabitatObjects.js'
import { useAddressAutocomplete } from '../src/composables/useAddressAutocomplete.js'

// Mock global fetch for Node testing environment
globalThis.fetch = async () => ({
  ok: true,
  json: async () => ({ visitors: [], count: 0 }),
})

test('useMapLayers manages layer visibility and registration', () => {
  const mapRef = ref(null)
  const { layers, isLayerVisible, setLayerVisibility, toggleLayer, registerHabitatLayers } =
    useMapLayers(mapRef)

  // Property boundary layer should be visible by default
  assert.equal(isLayerVisible('property-boundary'), true)

  // Toggle boundary layer
  const boundaryLayer = layers.value.find((l) => l.id === 'property-boundary')
  assert.ok(boundaryLayer)
  toggleLayer(boundaryLayer)
  assert.equal(isLayerVisible('property-boundary'), false)

  setLayerVisibility('property-boundary', true)
  assert.equal(isLayerVisible('property-boundary'), true)

  // Register dynamic habitat layers
  registerHabitatLayers({
    layers: [
      {
        id: 'habitat-canopy',
        name: 'Tree Canopy',
        color: '#2d6a4f',
        percentage: 45.2,
      },
    ],
  })

  const dynamic = layers.value.find((l) => l.id === 'habitat-canopy')
  assert.ok(dynamic)
  assert.equal(dynamic.percentage, 45.2)
})

test('useHabitatPaint manages brush selection, paint mode and strokes', () => {
  const mapRef = ref(null)
  let clearedCursor = false
  const {
    isPaintMode,
    activeBrushClass,
    activeBrushColor,
    brushSizeMeters,
    strokes,
    togglePaintMode,
    undoStroke,
    clearAllStrokes,
  } = useHabitatPaint(mapRef, {
    onClearCursor: () => {
      clearedCursor = true
    },
  })

  assert.equal(isPaintMode.value, false)
  togglePaintMode()
  assert.equal(isPaintMode.value, true)

  // Brush class selection
  assert.equal(activeBrushClass.value, 'tree_canopy')
  assert.ok(activeBrushColor.value)

  activeBrushClass.value = 'lawn_grass'
  assert.equal(activeBrushClass.value, 'lawn_grass')

  // Strokes management
  strokes.value.push({ classId: 'tree_canopy', points: [[-75.0, 40.0]], radiusMeters: 6 })
  strokes.value.push({ classId: 'lawn_grass', points: [[-75.0, 40.0]], radiusMeters: 6 })
  assert.equal(strokes.value.length, 2)

  undoStroke()
  assert.equal(strokes.value.length, 1)

  clearAllStrokes()
  assert.equal(strokes.value.length, 0)

  // Exit paint mode clears cursor
  togglePaintMode()
  assert.equal(isPaintMode.value, false)
  assert.equal(clearedCursor, true)
})

test('useAddressAutocomplete manages keyboard navigation and selection', () => {
  const {
    address,
    suggestions,
    showDropdown,
    activeIndex,
    onKeydown,
    closeDropdown,
  } = useAddressAutocomplete()

  suggestions.value = [
    { label: '100 Main St, Allentown, PA', lat: 40.6, lon: -75.48 },
    { label: '200 Main St, Allentown, PA', lat: 40.61, lon: -75.49 },
  ]
  showDropdown.value = true

  // Arrow down
  onKeydown({ key: 'ArrowDown', preventDefault: () => {} })
  assert.equal(activeIndex.value, 0)

  onKeydown({ key: 'ArrowDown', preventDefault: () => {} })
  assert.equal(activeIndex.value, 1)

  // Arrow up
  onKeydown({ key: 'ArrowUp', preventDefault: () => {} })
  assert.equal(activeIndex.value, 0)

  // Enter selects current item
  onKeydown({ key: 'Enter', preventDefault: () => {} })
  assert.equal(address.value, '100 Main St, Allentown, PA')
  assert.equal(showDropdown.value, false)

  // Close dropdown
  closeDropdown()
  assert.equal(showDropdown.value, false)
})

test('useHabitatObjects manages placement mode, active type, and selection', () => {
  const mapRef = ref(null)
  let placementEntered = false
  const {
    habitatObjects,
    isObjectPlacementMode,
    activeObjectType,
    selectedObject,
    toggleObjectPlacementMode,
    openObjectDetails,
    closeObjectDetails,
    toggleFoodSelection,
  } = useHabitatObjects(mapRef, {
    onBeforeEnterPlacementMode: () => {
      placementEntered = true
    },
  })

  assert.equal(isObjectPlacementMode.value, false)
  toggleObjectPlacementMode()
  assert.equal(isObjectPlacementMode.value, true)
  assert.equal(placementEntered, true)

  // Change object type
  activeObjectType.value = 'nest_box'
  assert.equal(activeObjectType.value, 'nest_box')

  // Open modal for an object
  const mockFeeder = {
    id: 'f1',
    type: 'bird_feeder',
    customName: 'Patio Feeder',
    foods: ['sunflower_black_oil'],
  }
  openObjectDetails(mockFeeder)
  assert.ok(selectedObject.value)
  assert.equal(selectedObject.value.id, 'f1')

  assert.deepEqual(selectedObject.value.foods, ['sunflower_black_oil'])

  toggleFoodSelection('suet')
  assert.ok(selectedObject.value.foods.includes('suet'))

  closeObjectDetails()
  assert.equal(selectedObject.value, null)
})
