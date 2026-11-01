import { computed, ref } from 'vue'
import { SATELLITE_SOURCES } from '../constants/mapConstants.js'

export function useSatelliteImagery(
  mapRef,
  {
    token = '',
    initialExpanded = true,
    onSourceChange,
    onVisibilityChange,
  } = {}
) {
  const isSatellitePanelExpanded = ref(initialExpanded)
  const activeSourceId = ref('mapbox')
  const activeOpacity = ref(1.0)
  const activeWaybackEpochIndex = ref(0)
  const isBaseLayerVisible = ref(true)

  // Clone sources list so epochs/badges can be dynamically updated if needed
  const sources = ref(
    SATELLITE_SOURCES.map((s) => ({
      ...s,
      epochs: s.epochs ? s.epochs.map((e) => ({ ...e })) : undefined,
    }))
  )

  function getActiveSource() {
    return sources.value.find((s) => s.id === activeSourceId.value) || sources.value[0]
  }

  const activeSource = computed(() => getActiveSource())

  function formatIsoDate(dateStr) {
    if (!dateStr) return ''
    const parts = String(dateStr).split('-')
    if (parts.length === 3) {
      const months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
      ]
      const year = parts[0]
      const month = months[parseInt(parts[1], 10) - 1]
      const day = parseInt(parts[2], 10)
      if (month && !isNaN(day)) {
        return `${month} ${day}, ${year}`
      }
    }
    return dateStr
  }

  function getActiveCaptureDate(mapboxDate = '') {
    const source = getActiveSource()
    if (source.id === 'mapbox') {
      return mapboxDate || ''
    }
    if (source.id === 'esri-wayback') {
      const epochs = source.epochs || []
      const epoch = epochs[activeWaybackEpochIndex.value] || epochs[0]
      return epoch ? formatIsoDate(epoch.date) : ''
    }
    return source.captureDate || ''
  }


  function getActiveTileUrl(source = getActiveSource()) {
    if (source.id === 'esri-wayback') {
      const epochs = source.epochs || []
      const epoch = epochs[activeWaybackEpochIndex.value] || epochs[0]
      return epoch ? epoch.tileUrl : ''
    }
    if (typeof source.tiles === 'function') {
      const tiles = source.tiles(token)
      return tiles[0]
    }
    return ''
  }

  function applyActiveSourceToMap() {
    const mapInstance = mapRef.value
    if (!mapInstance || !mapInstance.isStyleLoaded()) return

    const source = getActiveSource()
    const tileUrl = getActiveTileUrl(source)
    const layerId = 'active-satellite-layer'
    const sourceId = 'active-satellite-source'

    const visibility = isBaseLayerVisible.value ? 'visible' : 'none'
    const opacity = activeOpacity.value

    // If source exists, try setTiles (standard Mapbox GL RasterTileSource method)
    const existingSource = mapInstance.getSource(sourceId)
    if (existingSource && typeof existingSource.setTiles === 'function') {
      existingSource.setTiles([tileUrl])
    } else {
      // Re-create source and layer before property-boundary
      if (mapInstance.getLayer(layerId)) {
        mapInstance.removeLayer(layerId)
      }
      if (mapInstance.getSource(sourceId)) {
        mapInstance.removeSource(sourceId)
      }

      mapInstance.addSource(sourceId, {
        type: 'raster',
        tiles: [tileUrl],
        tileSize: source.tileSize || 256,
        maxzoom: source.maxzoom || 22,
      })

      const beforeId = mapInstance.getLayer('parcel-boundary-fill')
        ? 'parcel-boundary-fill'
        : undefined

      mapInstance.addLayer(
        {
          id: layerId,
          type: 'raster',
          source: sourceId,
          minzoom: 0,
          maxzoom: source.maxzoom || 22,
          layout: { visibility },
          paint: { 'raster-opacity': opacity },
        },
        beforeId
      )
    }

    if (mapInstance.getLayer(layerId)) {
      mapInstance.setLayoutProperty(layerId, 'visibility', visibility)
      mapInstance.setPaintProperty(layerId, 'raster-opacity', opacity)
    }
  }

  function selectSource(sourceId) {
    if (activeSourceId.value === sourceId) return
    activeSourceId.value = sourceId
    applyActiveSourceToMap()
    if (onSourceChange) {
      onSourceChange(getActiveSource(), getActiveCaptureDate())
    }
  }

  function setOpacity(val) {
    activeOpacity.value = val
    const mapInstance = mapRef.value
    if (!mapInstance) return
    if (mapInstance.getLayer('active-satellite-layer')) {
      try {
        mapInstance.setPaintProperty('active-satellite-layer', 'raster-opacity', val)
      } catch {
        // ignore
      }
    }
  }

  function selectWaybackEpoch(index) {
    const wayback = sources.value.find((s) => s.id === 'esri-wayback')
    if (!wayback || !wayback.epochs || !wayback.epochs[index]) return
    activeWaybackEpochIndex.value = index
    wayback.selectedEpochIndex = index
    const epoch = wayback.epochs[index]
    wayback.badge = `0.5m • ${epoch.label.split(' ')[0]}`

    applyActiveSourceToMap()
    if (onSourceChange) {
      onSourceChange(wayback, getActiveCaptureDate())
    }
  }

  function toggleVisibility(visible) {
    const nextVal = typeof visible === 'boolean' ? visible : !isBaseLayerVisible.value
    isBaseLayerVisible.value = nextVal
    const mapInstance = mapRef.value
    if (mapInstance && mapInstance.getLayer('active-satellite-layer')) {
      mapInstance.setLayoutProperty(
        'active-satellite-layer',
        'visibility',
        nextVal ? 'visible' : 'none'
      )
    }
    if (onVisibilityChange) {
      onVisibilityChange(nextVal)
    }
  }

  function syncWithLayerToggle(visible) {
    isBaseLayerVisible.value = visible
    const mapInstance = mapRef.value
    if (!mapInstance) return
    if (mapInstance.getLayer('active-satellite-layer')) {
      mapInstance.setLayoutProperty(
        'active-satellite-layer',
        'visibility',
        visible ? 'visible' : 'none'
      )
    }
  }

  function toggleExpand() {
    isSatellitePanelExpanded.value = !isSatellitePanelExpanded.value
  }

  return {
    isSatellitePanelExpanded,
    activeSourceId,
    activeOpacity,
    activeWaybackEpochIndex,
    isBaseLayerVisible,
    sources,
    activeSource,
    getActiveSource,
    getActiveTileUrl,
    getActiveCaptureDate,
    selectSource,
    setOpacity,
    selectWaybackEpoch,
    toggleVisibility,
    syncWithLayerToggle,
    toggleExpand,
    applyActiveSourceToMap,
  }
}
