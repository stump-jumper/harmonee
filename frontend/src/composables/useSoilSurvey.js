import { ref } from 'vue'
import mapboxgl from 'mapbox-gl'
import { fetchSoilSurvey } from '../api/propertyApi.js'
import { escapeHtml } from '../utils/formatters.js'

export function useSoilSurvey(
  mapRef,
  {
    isLayerVisible,
    setLayerVisibility,
    mapboxLib = mapboxgl,
    doc = globalThis.document,
  } = {}
) {
  const soilSurveyData = ref(null)
  const soilLoading = ref(false)
  const soilError = ref('')
  const selectedSoilSymbol = ref(null)
  const isPanelExpanded = ref(false)

  const soilMarkers = []
  let soilPopup = null

  function updateSoilMarkersVisibility() {
    const visible = isLayerVisible ? isLayerVisible('soil-survey-layer') : false
    if (!visible && soilPopup) {
      soilPopup.remove()
      soilPopup = null
      selectedSoilSymbol.value = null
    }
    for (const marker of soilMarkers) {
      const el = marker.getElement()
      if (el) {
        el.style.display = visible ? '' : 'none'
      }
    }
    const mapInstance = mapRef.value
    if (mapInstance && mapInstance.setLayoutProperty) {
      const visibility = visible ? 'visible' : 'none'
      if (mapInstance.getLayer('soil-survey-fill')) {
        mapInstance.setLayoutProperty('soil-survey-fill', 'visibility', visibility)
      }
      if (mapInstance.getLayer('soil-survey-outline')) {
        mapInstance.setLayoutProperty('soil-survey-outline', 'visibility', visibility)
      }
    }
  }

  function syncWithLayerToggle(visible) {
    isPanelExpanded.value = visible
    updateSoilMarkersVisibility()
  }

  function togglePanel() {
    isPanelExpanded.value = !isPanelExpanded.value
    if (setLayerVisibility) {
      setLayerVisibility('soil-survey-layer', isPanelExpanded.value)
    }
    updateSoilMarkersVisibility()
  }

  function cleanupSoilMarkers() {
    for (const m of soilMarkers) {
      m.remove()
    }
    soilMarkers.length = 0
    if (soilPopup) {
      soilPopup.remove()
      soilPopup = null
    }
  }

  function renderSoilOnMap(data) {
    if (!data) return
    const mapInstance = mapRef.value
    if (!mapInstance || !mapInstance.isStyleLoaded()) return

    const rawGeojson = data.geojson || { type: 'FeatureCollection', features: [] }
    const sourceId = 'soil-survey-data'
    const fillId = 'soil-survey-fill'
    const outlineId = 'soil-survey-outline'

    const initialVisibility =
      isLayerVisible && isLayerVisible('soil-survey-layer') ? 'visible' : 'none'

    // Add or update source
    if (mapInstance.getSource(sourceId)) {
      mapInstance.getSource(sourceId).setData(rawGeojson)
    } else {
      mapInstance.addSource(sourceId, {
        type: 'geojson',
        data: rawGeojson,
      })

      // Layer placement: place before parcel-boundary-outline or user-paint-strokes-lines if present
      const beforeId = mapInstance.getLayer('parcel-boundary-outline')
        ? 'parcel-boundary-outline'
        : mapInstance.getLayer('user-paint-strokes-lines')
        ? 'user-paint-strokes-lines'
        : undefined

      mapInstance.addLayer(
        {
          id: fillId,
          type: 'fill',
          source: sourceId,
          layout: { visibility: initialVisibility },
          paint: {
            'fill-color': ['get', 'color'],
            'fill-opacity': 0.42,
          },
        },
        beforeId
      )

      mapInstance.addLayer(
        {
          id: outlineId,
          type: 'line',
          source: sourceId,
          layout: {
            visibility: initialVisibility,
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 2,
            'line-opacity': 0.95,
          },
        },
        beforeId
      )

      // Click on polygon fill shows popup
      mapInstance.on('click', fillId, (e) => {
        if (!e.features || !e.features.length) return
        const p = e.features[0].properties
        selectedSoilSymbol.value = p.musym

        if (soilPopup) soilPopup.remove()
        soilPopup = new mapboxLib.Popup({ closeButton: true, offset: 10 })
          .setLngLat(e.lngLat)
          .setHTML(`
            <div class="soil-popup-content">
              <div class="soil-popup-badge" style="background: ${escapeHtml(p.color || '#c28b5e')};">${escapeHtml(p.musym)}</div>
              <div class="soil-popup-name">${escapeHtml(p.muname)}</div>
              <div class="soil-popup-pct">Property Coverage: <strong>${p.percentage}%</strong></div>
            </div>
          `)
          .addTo(mapInstance)
      })

      mapInstance.on('mouseenter', fillId, () => {
        mapInstance.getCanvas().style.cursor = 'pointer'
      })
      mapInstance.on('mouseleave', fillId, () => {
        mapInstance.getCanvas().style.cursor = ''
      })
    }

    // Render centered symbol markers for each map unit
    cleanupSoilMarkers()

    const labelFeatures = data.labelsGeojson?.features || []
    for (const feat of labelFeatures) {
      const p = feat.properties || {}
      const coords = feat.geometry?.coordinates
      if (!coords || coords.length < 2) continue

      const el = doc.createElement('div')
      el.className = 'soil-unit-marker'
      el.setAttribute('data-symbol', p.musym)
      el.style.setProperty('--soil-color', p.color || '#c28b5e')

      const badge = doc.createElement('div')
      badge.className = 'soil-marker-badge'
      badge.style.borderColor = p.color || '#c28b5e'

      const sym = doc.createElement('span')
      sym.className = 'soil-marker-symbol'
      sym.textContent = p.musym

      badge.appendChild(sym)
      el.appendChild(badge)

      const marker = new mapboxLib.Marker({
        element: el,
        anchor: 'center',
      }).setLngLat(coords)

      const popup = new mapboxLib.Popup({ offset: 12, closeButton: false }).setHTML(`
        <div class="soil-popup-content">
          <div class="soil-popup-badge" style="background: ${escapeHtml(p.color || '#c28b5e')};">${escapeHtml(p.musym)}</div>
          <div class="soil-popup-name">${escapeHtml(p.muname)}</div>
          <div class="soil-popup-pct">Property Coverage: <strong>${p.percentage}%</strong></div>
        </div>
      `)
      marker.setPopup(popup)

      el.addEventListener('click', (ev) => {
        ev.stopPropagation()
        selectedSoilSymbol.value = p.musym
      })

      marker.addTo(mapInstance)
      soilMarkers.push(marker)
    }

    updateSoilMarkersVisibility()
  }

  function focusOnSoilUnit(unit) {
    if (!unit) return
    selectedSoilSymbol.value = unit.musym
    const mapInstance = mapRef.value
    if (!mapInstance) return

    // Find first label feature for this symbol
    const labelFeatures = soilSurveyData.value?.labelsGeojson?.features || []
    const match = labelFeatures.find((f) => f.properties?.musym === unit.musym)
    if (match && match.geometry?.coordinates) {
      mapInstance.flyTo({
        center: match.geometry.coordinates,
        zoom: Math.max(mapInstance.getZoom(), 18.5),
        duration: 1000,
      })
    }

    // Open popup on matching marker
    const marker = soilMarkers.find(
      (m) => m.getElement()?.getAttribute('data-symbol') === unit.musym
    )
    if (marker) {
      const popup = marker.getPopup()
      if (popup && !popup.isOpen()) {
        marker.togglePopup()
      }
    }
  }

  async function loadSoilSurvey() {
    soilLoading.value = true
    soilError.value = ''
    try {
      const data = await fetchSoilSurvey()
      soilSurveyData.value = data
      renderSoilOnMap(data)
    } catch (err) {
      soilError.value = err.message || 'Failed to load soil survey'
    } finally {
      soilLoading.value = false
    }
  }

  async function refreshSoilSurvey() {
    return loadSoilSurvey()
  }

  return {
    soilSurveyData,
    soilLoading,
    soilError,
    selectedSoilSymbol,
    isPanelExpanded,
    soilMarkers,
    togglePanel,
    updateSoilMarkersVisibility,
    syncWithLayerToggle,
    renderSoilOnMap,
    focusOnSoilUnit,
    cleanupSoilMarkers,
    loadSoilSurvey,
    refreshSoilSurvey,
  }
}
