import { computed, ref, watch } from 'vue'
import { segmentParcelFromPaint } from '../api/habitatApi.js'
import { BRUSH_CLASSES } from '../constants/mapConstants.js'
import { metersToRadiusPixels } from '../utils/geo.js'

export function useHabitatPaint(
  mapRef,
  { onBeforeEnterPaintMode, onClearCursor, onSegmentationComplete } = {}
) {
  const isPaintMode = ref(false)
  const isSegmenting = ref(false)
  const activeBrushClass = ref('tree_canopy')
  const brushSizeMeters = ref(6.0)
  const strokes = ref([])
  const isDrawing = ref(false)
  const currentStroke = ref(null)
  const brushDiameterPx = ref(20)

  const activeBrushColor = computed(() => {
    const b = BRUSH_CLASSES.find((c) => c.id === activeBrushClass.value)
    return b ? b.color : '#52b788'
  })

  function updateBrushDiameter() {
    const mapInstance = mapRef.value
    if (!mapInstance) return
    const center = mapInstance.getCenter()
    const centerLat = center ? center.lat : 40.5
    const zoom = mapInstance.getZoom() || 18.5
    const radPx = metersToRadiusPixels(brushSizeMeters.value, centerLat, zoom)
    brushDiameterPx.value = radPx * 2
  }

  watch(brushSizeMeters, () => {
    updateBrushDiameter()
  })

  function updatePaintStrokesSource() {
    const mapInstance = mapRef.value
    if (!mapInstance || !mapInstance.getSource('user-paint-strokes')) return

    if (!isPaintMode.value) {
      mapInstance.getSource('user-paint-strokes').setData({
        type: 'FeatureCollection',
        features: [],
      })
      return
    }

    const center = mapInstance.getCenter()
    const centerLat = center ? center.lat : 40.5
    const zoom = mapInstance.getZoom() || 18.5

    const allStrokes = currentStroke.value
      ? [...strokes.value, currentStroke.value]
      : strokes.value
    const features = []

    for (const s of allStrokes) {
      const radM = s.radiusMeters || 6.0
      const radPx = metersToRadiusPixels(radM, centerLat, zoom)
      const widthPx = radPx * 2

      for (const pt of s.coordinates) {
        features.push({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: pt },
          properties: { color: s.color, radiusPx: radPx },
        })
      }

      if (s.coordinates.length >= 2) {
        features.push({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: s.coordinates },
          properties: { color: s.color, widthPx },
        })
      }
    }

    mapInstance.getSource('user-paint-strokes').setData({
      type: 'FeatureCollection',
      features,
    })
  }

  function onMapMouseDown(e) {
    const mapInstance = mapRef.value
    if (!isPaintMode.value || !mapInstance) return
    if (e.originalEvent && e.originalEvent.button !== 0) return
    isDrawing.value = true
    const coords = [e.lngLat.lng, e.lngLat.lat]
    const brush = BRUSH_CLASSES.find((c) => c.id === activeBrushClass.value) || BRUSH_CLASSES[0]

    currentStroke.value = {
      id: Date.now(),
      categoryId: brush.id,
      color: brush.color,
      radiusMeters: brushSizeMeters.value,
      coordinates: [coords],
    }
    updatePaintStrokesSource()
  }

  function onMapMouseMove(e) {
    if (!isPaintMode.value || !isDrawing.value || !currentStroke.value) return
    const coords = [e.lngLat.lng, e.lngLat.lat]
    const last = currentStroke.value.coordinates[currentStroke.value.coordinates.length - 1]
    if (
      !last ||
      Math.abs(coords[0] - last[0]) > 0.000003 ||
      Math.abs(coords[1] - last[1]) > 0.000003
    ) {
      currentStroke.value.coordinates.push(coords)
      updatePaintStrokesSource()
    }
  }

  function onMapMouseUp() {
    if (!isPaintMode.value || !isDrawing.value) return
    isDrawing.value = false
    if (currentStroke.value && currentStroke.value.coordinates.length > 0) {
      strokes.value.push(currentStroke.value)
      currentStroke.value = null
      updatePaintStrokesSource()
    }
  }

  function togglePaintMode() {
    if (!isPaintMode.value && onBeforeEnterPaintMode) {
      onBeforeEnterPaintMode()
    }
    isPaintMode.value = !isPaintMode.value
    const mapInstance = mapRef.value
    if (mapInstance) {
      if (isPaintMode.value) {
        mapInstance.dragPan.disable()
        const canvas = mapInstance.getCanvas()
        if (canvas) canvas.style.cursor = 'none'
        updateBrushDiameter()
      } else {
        mapInstance.dragPan.enable()
        const canvas = mapInstance.getCanvas()
        if (canvas) canvas.style.cursor = ''
        isDrawing.value = false
        currentStroke.value = null
      }
      updatePaintStrokesSource()
    }

    if (!isPaintMode.value) {
      isDrawing.value = false
      currentStroke.value = null
      if (onClearCursor) onClearCursor()
    }
  }

  function undoStroke() {
    strokes.value.pop()
    updatePaintStrokesSource()
  }

  function clearAllStrokes() {
    strokes.value = []
    currentStroke.value = null
    updatePaintStrokesSource()
  }

  async function triggerPaintSegmentation() {
    if (isSegmenting.value) return
    if (!strokes.value.length) {
      if (typeof globalThis.alert === 'function') {
        globalThis.alert(
          'Please paint at least one stroke on your parcel first to indicate a habitat class.'
        )
      }
      return
    }
    isSegmenting.value = true
    try {
      const segData = await segmentParcelFromPaint(strokes.value)
      if (onSegmentationComplete) {
        onSegmentationComplete(segData)
      }
      if (isPaintMode.value) {
        togglePaintMode()
      } else {
        updatePaintStrokesSource()
      }
    } catch (err) {
      console.error('Segmentation error:', err)
    } finally {
      isSegmenting.value = false
    }
  }

  return {
    isPaintMode,
    isSegmenting,
    activeBrushClass,
    brushSizeMeters,
    strokes,
    isDrawing,
    currentStroke,
    brushDiameterPx,
    activeBrushColor,
    updateBrushDiameter,
    updatePaintStrokesSource,
    onMapMouseDown,
    onMapMouseMove,
    onMapMouseUp,
    togglePaintMode,
    undoStroke,
    clearAllStrokes,
    triggerPaintSegmentation,
  }
}
