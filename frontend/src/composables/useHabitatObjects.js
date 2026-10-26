import { ref } from 'vue'
import mapboxgl from 'mapbox-gl'
import { calculateFeederVisitors } from '../api/birdsApi.js'
import { persistHabitatObjects } from '../api/habitatApi.js'
import { getFoodOption, getObjectTypeDef } from '../constants/mapConstants.js'

export function useHabitatObjects(
  mapRef,
  {
    isLayerVisible,
    onBeforeEnterPlacementMode,
    onClearCursor,
    mapboxLib = mapboxgl,
    doc = globalThis.document,
  } = {}
) {
  const habitatObjects = ref([])
  const isObjectPlacementMode = ref(false)
  const activeObjectType = ref('bird_feeder')
  const selectedObject = ref(null)
  const isFoodDropdownOpen = ref(false)
  const isEditDetailsCollapsed = ref(true)
  const feederLikelihoodData = ref(null)
  const isFeederLikelihoodLoading = ref(false)
  const feederLikelihoodError = ref(null)

  const objectMarkersMap = new Map()

  function toggleObjectPlacementMode() {
    if (!isObjectPlacementMode.value && onBeforeEnterPlacementMode) {
      onBeforeEnterPlacementMode()
    }
    isObjectPlacementMode.value = !isObjectPlacementMode.value
    const mapInstance = mapRef.value
    if (!mapInstance) return

    const canvas = mapInstance.getCanvas()
    if (canvas) {
      canvas.style.cursor = isObjectPlacementMode.value ? 'crosshair' : ''
    }
    if (!isObjectPlacementMode.value && onClearCursor) {
      onClearCursor()
    }
  }

  function updateHabitatObjectMarkersVisibility() {
    const visible = isLayerVisible ? isLayerVisible('habitat-objects-layer') : true
    for (const [, marker] of objectMarkersMap) {
      const el = marker.getElement()
      if (el) {
        el.style.display = visible ? '' : 'none'
      }
    }
  }

  async function saveHabitatObjects() {
    try {
      await persistHabitatObjects(habitatObjects.value)
    } catch (err) {
      console.error('Failed to save habitat objects:', err)
    }
  }

  function getMarkerSubInfo(obj) {
    if (obj.type === 'bird_feeder' && obj.foods && obj.foods.length) {
      return obj.foods.map((f) => getFoodOption(f).label).join(', ')
    }
    return obj.variant || ''
  }

  function renderHabitatObjectMarkers() {
    const mapInstance = mapRef.value
    if (!mapInstance || !doc) return

    const activeIds = new Set(habitatObjects.value.map((o) => o.id))
    for (const [id, marker] of objectMarkersMap) {
      if (!activeIds.has(id)) {
        marker.remove()
        objectMarkersMap.delete(id)
      }
    }

    const visible = isLayerVisible ? isLayerVisible('habitat-objects-layer') : true

    for (const obj of habitatObjects.value) {
      const typeDef = getObjectTypeDef(obj.type)
      let marker = objectMarkersMap.get(obj.id)
      const subInfo = getMarkerSubInfo(obj)
      const titleText = `${obj.name}${subInfo ? ` (${subInfo})` : ''}`

      if (marker) {
        marker.setLngLat(obj.coordinates)
        const el = marker.getElement()
        if (el) {
          el.style.display = visible ? '' : 'none'
          const pin = el.querySelector('.marker-pin')
          if (pin) pin.style.setProperty('--marker-color', typeDef.color)
          const iconSpan = el.querySelector('.marker-icon')
          if (iconSpan) iconSpan.textContent = typeDef.icon
          const label = el.querySelector('.marker-label')
          if (label) label.textContent = obj.name || typeDef.name
          el.setAttribute('title', titleText)
        }
      } else {
        const el = doc.createElement('div')
        el.className = 'habitat-object-marker'
        el.setAttribute('data-id', obj.id)
        el.setAttribute('title', titleText)
        if (!visible) el.style.display = 'none'

        const pin = doc.createElement('div')
        pin.className = 'marker-pin'
        pin.style.setProperty('--marker-color', typeDef.color)

        const iconSpan = doc.createElement('span')
        iconSpan.className = 'marker-icon'
        iconSpan.textContent = typeDef.icon
        pin.appendChild(iconSpan)

        const label = doc.createElement('div')
        label.className = 'marker-label'
        label.textContent = obj.name || typeDef.name

        const body = doc.createElement('div')
        body.className = 'marker-body'
        body.appendChild(pin)
        body.appendChild(label)
        el.appendChild(body)

        marker = new mapboxLib.Marker({
          element: el,
          draggable: true,
          anchor: 'bottom',
        })
          .setLngLat(obj.coordinates)
          .addTo(mapInstance)

        marker.on('dragend', () => {
          const lngLat = marker.getLngLat()
          obj.coordinates = [lngLat.lng, lngLat.lat]
          saveHabitatObjects()
        })

        el.addEventListener('click', (e) => {
          e.stopPropagation()
          openObjectDetails(obj)
        })

        el.addEventListener('mouseenter', () => {
          el.style.zIndex = '100'
        })

        el.addEventListener('mouseleave', () => {
          el.style.zIndex = ''
        })

        objectMarkersMap.set(obj.id, marker)
      }
    }
  }

  async function fetchFeederLikelihood() {
    if (!selectedObject.value || selectedObject.value.type !== 'bird_feeder') {
      feederLikelihoodData.value = null
      return
    }
    const foods = selectedObject.value.foods || []
    if (!foods.length) {
      feederLikelihoodData.value = { visitors: [], foods: [] }
      return
    }
    isFeederLikelihoodLoading.value = true
    feederLikelihoodError.value = null
    try {
      const coords = selectedObject.value.coordinates || []
      const data = await calculateFeederVisitors({
        foods,
        lon: coords[0] ?? null,
        lat: coords[1] ?? null,
      })
      feederLikelihoodData.value = data
    } catch (err) {
      console.error('Failed to fetch feeder likelihood:', err)
      feederLikelihoodError.value = 'Failed to calculate visitor likelihood.'
    } finally {
      isFeederLikelihoodLoading.value = false
    }
  }

  function toggleFoodSelection(foodId) {
    if (!selectedObject.value) return
    if (!Array.isArray(selectedObject.value.foods)) {
      selectedObject.value.foods = []
    }
    const idx = selectedObject.value.foods.indexOf(foodId)
    if (idx === -1) {
      selectedObject.value.foods.push(foodId)
    } else {
      selectedObject.value.foods.splice(idx, 1)
    }
    if (selectedObject.value.type === 'bird_feeder') {
      fetchFeederLikelihood()
    }
  }

  function clearSelectedFoods() {
    if (!selectedObject.value) return
    selectedObject.value.foods = []
    fetchFeederLikelihood()
  }

  function openObjectDetails(obj) {
    selectedObject.value = JSON.parse(JSON.stringify(obj))
    if (!Array.isArray(selectedObject.value.foods)) {
      selectedObject.value.foods =
        selectedObject.value.type === 'bird_feeder' ? ['sunflower_black_oil'] : []
    }
    isFoodDropdownOpen.value = false
    isEditDetailsCollapsed.value = selectedObject.value.type === 'bird_feeder'
    if (selectedObject.value.type === 'bird_feeder') {
      fetchFeederLikelihood()
    } else {
      feederLikelihoodData.value = null
    }
  }

  function closeObjectDetails() {
    selectedObject.value = null
    isFoodDropdownOpen.value = false
    feederLikelihoodData.value = null
  }

  function saveAndCloseObjectDetails() {
    if (!selectedObject.value) return
    const idx = habitatObjects.value.findIndex((o) => o.id === selectedObject.value.id)
    if (idx !== -1) {
      habitatObjects.value[idx] = { ...selectedObject.value }
      renderHabitatObjectMarkers()
      saveHabitatObjects()
    }
    closeObjectDetails()
  }

  function changeSelectedObjectType(typeId) {
    if (!selectedObject.value) return
    const prevTypeDef = getObjectTypeDef(selectedObject.value.type)
    const newTypeDef = getObjectTypeDef(typeId)
    selectedObject.value.type = typeId
    if (!selectedObject.value.name || selectedObject.value.name === prevTypeDef.name) {
      selectedObject.value.name = newTypeDef.name
    }
    if (!newTypeDef.variants.includes(selectedObject.value.variant)) {
      selectedObject.value.variant = newTypeDef.defaultVariant
    }
    if (
      typeId === 'bird_feeder' &&
      (!selectedObject.value.foods || !selectedObject.value.foods.length)
    ) {
      selectedObject.value.foods = ['sunflower_black_oil']
    }
    if (typeId === 'bird_feeder') {
      fetchFeederLikelihood()
    } else {
      feederLikelihoodData.value = null
    }
  }

  function deleteObject(obj) {
    if (!obj) return
    habitatObjects.value = habitatObjects.value.filter((o) => o.id !== obj.id)
    renderHabitatObjectMarkers()
    saveHabitatObjects()
    selectedObject.value = null
  }

  function focusOnObject(obj) {
    const mapInstance = mapRef.value
    if (!mapInstance || !obj.coordinates) return
    mapInstance.flyTo({
      center: obj.coordinates,
      zoom: Math.max(mapInstance.getZoom(), 19),
      duration: 800,
    })
    openObjectDetails(obj)
  }

  function onMapClick(e) {
    if (!isObjectPlacementMode.value) return
    const coords = [e.lngLat.lng, e.lngLat.lat]
    const typeDef = getObjectTypeDef(activeObjectType.value)
    const newObj = {
      id: `obj-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      type: typeDef.id,
      name: typeDef.name,
      foods: typeDef.id === 'bird_feeder' ? ['sunflower_black_oil'] : [],
      variant: typeDef.defaultVariant,
      notes: '',
      coordinates: coords,
      dateAdded: new Date().toISOString().slice(0, 10),
    }
    habitatObjects.value.push(newObj)
    renderHabitatObjectMarkers()
    saveHabitatObjects()
    openObjectDetails(newObj)
  }

  function cleanupObjectMarkers() {
    for (const [, marker] of objectMarkersMap) {
      marker.remove()
    }
    objectMarkersMap.clear()
  }

  return {
    habitatObjects,
    isObjectPlacementMode,
    activeObjectType,
    selectedObject,
    isFoodDropdownOpen,
    isEditDetailsCollapsed,
    feederLikelihoodData,
    isFeederLikelihoodLoading,
    feederLikelihoodError,
    toggleObjectPlacementMode,
    updateHabitatObjectMarkersVisibility,
    renderHabitatObjectMarkers,
    saveHabitatObjects,
    fetchFeederLikelihood,
    toggleFoodSelection,
    clearSelectedFoods,
    openObjectDetails,
    closeObjectDetails,
    saveAndCloseObjectDetails,
    changeSelectedObjectType,
    deleteObject,
    focusOnObject,
    onMapClick,
    cleanupObjectMarkers,
  }
}
