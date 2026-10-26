import { ref, toRaw } from 'vue'
import { createInitialMapLayers } from '../constants/mapConstants.js'

export function useMapLayers(mapRef, { onLayerToggle } = {}) {
  const layers = ref(createInitialMapLayers())

  function isLayerVisible(layerId) {
    const layerConfig = layers.value.find((l) => l.id === layerId)
    return layerConfig ? layerConfig.visible : true
  }

  function applyMapLayerVisibility(layer) {
    const mapInstance = mapRef.value
    if (!mapInstance) return
    const visibility = layer.visible ? 'visible' : 'none'
    for (const mapLayerId of layer.mapLayerIds || []) {
      if (mapInstance.getLayer(mapLayerId)) {
        mapInstance.setLayoutProperty(mapLayerId, 'visibility', visibility)
      }
    }
  }

  function setLayerVisibility(layerId, visible) {
    const layer = layers.value.find((l) => l.id === layerId)
    if (!layer) return
    layer.visible = visible
    applyMapLayerVisibility(layer)
  }

  function toggleLayer(layer) {
    if (!layer.toggleable) return
    layer.visible = !layer.visible
    applyMapLayerVisibility(layer)
    if (onLayerToggle) {
      onLayerToggle(layer)
    }
  }

  function registerHabitatLayers(segData) {
    const segLayers = segData?.layers || []
    const coreLayers = layers.value.filter((l) => l.type !== 'habitat')
    const dynamicLayers = segLayers.map((seg) => ({
      id: seg.id,
      name: seg.name,
      type: 'habitat',
      visible: true,
      toggleable: true,
      color: seg.color,
      percentage: seg.percentage,
      feature: seg.feature,
      mapLayerIds: [`${seg.id}-fill`, `${seg.id}-outline`],
    }))
    layers.value = [...coreLayers, ...dynamicLayers]

    const mapInstance = mapRef.value
    if (!mapInstance || !mapInstance.isStyleLoaded()) return

    const activeHabitatIds = new Set(dynamicLayers.map((l) => l.id))
    const currentLayers = mapInstance.getStyle()?.layers || []
    for (const mLayer of currentLayers) {
      if (mLayer.id.startsWith('habitat-')) {
        const baseId = mLayer.id.replace(/-fill$|-outline$/, '')
        if (!activeHabitatIds.has(baseId)) {
          if (mapInstance.getLayer(mLayer.id)) mapInstance.removeLayer(mLayer.id)
          const srcId = `${baseId}-source`
          if (mapInstance.getSource(srcId)) mapInstance.removeSource(srcId)
        }
      }
    }

    const beforeId = mapInstance.getLayer('parcel-boundary-outline')
      ? 'parcel-boundary-outline'
      : undefined

    for (const hLayer of dynamicLayers) {
      const srcId = `${hLayer.id}-source`
      const fillId = `${hLayer.id}-fill`
      const outlineId = `${hLayer.id}-outline`
      const rawFeature = JSON.parse(JSON.stringify(toRaw(hLayer.feature)))

      if (mapInstance.getSource(srcId)) {
        mapInstance.getSource(srcId).setData(rawFeature)
      } else {
        mapInstance.addSource(srcId, {
          type: 'geojson',
          data: rawFeature,
        })
        mapInstance.addLayer(
          {
            id: fillId,
            type: 'fill',
            source: srcId,
            layout: { visibility: hLayer.visible ? 'visible' : 'none' },
            paint: {
              'fill-color': hLayer.color,
              'fill-opacity': 0.52,
            },
          },
          beforeId
        )
        mapInstance.addLayer(
          {
            id: outlineId,
            type: 'line',
            source: srcId,
            layout: {
              visibility: hLayer.visible ? 'visible' : 'none',
              'line-join': 'round',
              'line-cap': 'round',
            },
            paint: {
              'line-color': hLayer.color,
              'line-width': 1.5,
              'line-opacity': 0.9,
            },
          },
          beforeId
        )
      }
    }
  }

  return {
    layers,
    isLayerVisible,
    setLayerVisibility,
    toggleLayer,
    registerHabitatLayers,
  }
}
