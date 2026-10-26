import { computed, ref } from 'vue'
import mapboxgl from 'mapbox-gl'
import { fetchEbirdSightings, getBirdPhotoUrl } from '../api/birdsApi.js'
import { createGeoJSONCircle } from '../utils/geo.js'
import { escapeHtml, formatSightingDate } from '../utils/formatters.js'

export function buildSightingPopupHtml(sighting) {
  const imgUrl = getBirdPhotoUrl(sighting.sciName || sighting.comName)
  return `
    <div class="ebird-popup-content">
      <div class="popup-bird-top-row">
        <div class="popup-bird-thumb-wrap">
          <img
            src="${imgUrl}"
            alt="${escapeHtml(sighting.comName)}"
            class="popup-bird-thumb"
            loading="lazy"
            onerror="this.style.display='none'; if(this.nextElementSibling) this.nextElementSibling.style.display='flex';"
          />
          <div class="popup-bird-thumb-fallback" style="display: none;">🪶</div>
        </div>
        <div class="popup-bird-header">
          <div class="popup-bird-name">${escapeHtml(sighting.comName)}</div>
          <div class="popup-bird-sci">${escapeHtml(sighting.sciName)}</div>
        </div>
      </div>
      <div class="popup-bird-details">
        <div class="popup-tag-row">
          <span class="popup-tag dist-badge">📍 ${sighting.distanceMiles} mi away</span>
          <span class="popup-tag count-badge">🪶 ${sighting.howMany ? sighting.howMany + ' seen' : 'Present'}</span>
        </div>
        <div class="popup-time">🕒 ${escapeHtml(formatSightingDate(sighting.obsDt))} (${escapeHtml(sighting.obsDt)})</div>
        <div class="popup-loc">🏡 ${escapeHtml(sighting.locName || 'Nearby sighting')}</div>
        ${sighting.subId ? `<div class="popup-sub"><a href="https://ebird.org/checklist/${escapeHtml(sighting.subId)}" target="_blank" rel="noopener noreferrer">eBird Checklist #${escapeHtml(sighting.subId)} ↗</a></div>` : ''}
      </div>
    </div>
  `
}

export function useEbirdSightings(
  mapRef,
  {
    isLayerVisible,
    setLayerVisibility,
    mapboxLib = mapboxgl,
    doc = globalThis.document,
  } = {}
) {
  const ebirdSightingsData = ref(null)
  const ebirdLoading = ref(false)
  const ebirdActiveTab = ref('recent')
  const selectedSightingId = ref(null)
  const isEbirdCardExpanded = ref(false)

  let ebirdMarkers = []
  let currentOpenEbirdPopup = null
  let lastLat = null
  let lastLon = null

  const currentTopList = computed(() => {
    if (!ebirdSightingsData.value) return []
    if (ebirdActiveTab.value === 'recent') {
      return ebirdSightingsData.value.topRecent || []
    }
    if (ebirdActiveTab.value === 'closest') {
      return ebirdSightingsData.value.topClosest || []
    }
    return ebirdSightingsData.value.topCommon || []
  })

  function updateEbirdMarkersVisibility() {
    const visible = isLayerVisible ? isLayerVisible('ebird-sightings-layer') : true
    if (!visible && currentOpenEbirdPopup) {
      currentOpenEbirdPopup.remove()
      currentOpenEbirdPopup = null
    }
    for (const marker of ebirdMarkers) {
      const el = marker.getElement()
      if (el) {
        el.style.display = visible ? '' : 'none'
      }
    }
  }

  function syncWithLayerToggle(visible) {
    isEbirdCardExpanded.value = visible
    updateEbirdMarkersVisibility()
  }

  function toggleEbirdCard() {
    isEbirdCardExpanded.value = !isEbirdCardExpanded.value
    if (setLayerVisibility) {
      setLayerVisibility('ebird-sightings-layer', isEbirdCardExpanded.value)
    }
    updateEbirdMarkersVisibility()
  }

  function toggleSightingMarker(marker, sighting) {
    const mapInstance = mapRef.value
    const sId = sighting.id || sighting.speciesCode
    const popup = marker.getPopup()
    const isCurrentlyOpen = popup && popup.isOpen()

    if (isCurrentlyOpen) {
      popup.remove()
      currentOpenEbirdPopup = null
      selectedSightingId.value = null
      for (const m of ebirdMarkers) {
        m.getElement()?.classList.remove('is-focused')
      }
    } else {
      if (currentOpenEbirdPopup && currentOpenEbirdPopup !== popup) {
        currentOpenEbirdPopup.remove()
        currentOpenEbirdPopup = null
      }

      for (const m of ebirdMarkers) {
        m.getElement()?.classList.remove('is-focused')
      }
      marker.getElement()?.classList.add('is-focused')
      selectedSightingId.value = sId

      if (popup && mapInstance) {
        popup.setLngLat([sighting.lng, sighting.lat])
        popup.addTo(mapInstance)
        currentOpenEbirdPopup = popup
      }
    }
  }

  function renderEbirdOnMap(data, centerLat, centerLon) {
    const mapInstance = mapRef.value
    if (!mapInstance || !data || !doc) return
    if (!mapInstance.isStyleLoaded()) {
      mapInstance.once('style.load', () => renderEbirdOnMap(data, centerLat, centerLon))
      return
    }

    for (const m of ebirdMarkers) {
      m.remove()
    }
    ebirdMarkers = []
    if (currentOpenEbirdPopup) {
      currentOpenEbirdPopup.remove()
      currentOpenEbirdPopup = null
    }

    const circleFeature = createGeoJSONCircle([centerLon, centerLat], 1.0)
    const srcId = 'ebird-radius-source'
    const fillId = 'ebird-radius-fill'
    const outlineId = 'ebird-radius-outline'

    const visible = isLayerVisible ? isLayerVisible('ebird-sightings-layer') : true
    const visibility = visible ? 'visible' : 'none'

    if (mapInstance.getSource(srcId)) {
      mapInstance.getSource(srcId).setData(circleFeature)
    } else {
      mapInstance.addSource(srcId, {
        type: 'geojson',
        data: circleFeature,
      })
      const beforeId = mapInstance.getLayer('user-paint-strokes-lines')
        ? 'user-paint-strokes-lines'
        : undefined
      mapInstance.addLayer(
        {
          id: fillId,
          type: 'fill',
          source: srcId,
          layout: { visibility },
          paint: {
            'fill-color': '#0284c7',
            'fill-opacity': 0.05,
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
            visibility,
            'line-cap': 'round',
            'line-join': 'round',
          },
          paint: {
            'line-color': '#38bdf8',
            'line-width': 1.5,
            'line-dasharray': [3, 2],
            'line-opacity': 0.7,
          },
        },
        beforeId
      )
    }

    const sightings = data.sightings || []
    for (const s of sightings) {
      if (s.lng == null || s.lat == null) continue

      const el = doc.createElement('div')
      el.className = 'ebird-map-marker'
      el.dataset.sightingId = s.id || s.speciesCode
      el.dataset.speciesCode = s.speciesCode || ''
      if (!visible) el.style.display = 'none'

      const markerBody = doc.createElement('div')
      markerBody.className = 'marker-body'

      const pin = doc.createElement('div')
      pin.className = 'ebird-pin'
      pin.innerHTML = '🪶'
      pin.title = `${s.comName} (${s.distanceMiles} mi away)`

      markerBody.appendChild(pin)
      el.appendChild(markerBody)

      const popup = new mapboxLib.Popup({
        offset: 20,
        closeButton: true,
        className: 'ebird-mapbox-popup',
      })
        .setLngLat([s.lng, s.lat])
        .setHTML(buildSightingPopupHtml(s))

      popup.on('open', () => {
        if (currentOpenEbirdPopup && currentOpenEbirdPopup !== popup) {
          currentOpenEbirdPopup.remove()
        }
        currentOpenEbirdPopup = popup
      })

      popup.on('close', () => {
        el.classList.remove('is-focused')
        if (currentOpenEbirdPopup === popup) {
          currentOpenEbirdPopup = null
        }
        if (selectedSightingId.value === (s.id || s.speciesCode)) {
          selectedSightingId.value = null
        }
      })

      const marker = new mapboxLib.Marker({
        element: el,
        anchor: 'center',
      })
        .setLngLat([s.lng, s.lat])
        .setPopup(popup)
        .addTo(mapInstance)

      el.addEventListener(
        'click',
        (e) => {
          e.stopImmediatePropagation()
          e.stopPropagation()
          toggleSightingMarker(marker, s)
        },
        true
      )

      ebirdMarkers.push(marker)
    }
  }

  async function loadEbirdSightings(lat = lastLat, lon = lastLon, { refresh = false } = {}) {
    if (lat != null) lastLat = lat
    if (lon != null) lastLon = lon
    if (lastLat == null || lastLon == null) return

    ebirdLoading.value = true
    try {
      const data = await fetchEbirdSightings({
        lat: lastLat,
        lon: lastLon,
        radiusMiles: 1.0,
        days: 30,
        refresh,
      })
      ebirdSightingsData.value = data
      if (mapRef.value) {
        renderEbirdOnMap(data, lastLat, lastLon)
      }
    } catch (err) {
      console.error('Failed to load eBird sightings:', err)
    } finally {
      ebirdLoading.value = false
    }
  }

  async function refreshEbirdSightings() {
    await loadEbirdSightings(lastLat, lastLon, { refresh: true })
  }

  function focusOnSighting(item) {
    const mapInstance = mapRef.value
    if (!item || !mapInstance) return
    const sId = item.id || item.speciesCode

    if (isLayerVisible && !isLayerVisible('ebird-sightings-layer')) {
      if (setLayerVisibility) {
        setLayerVisibility('ebird-sightings-layer', true)
      }
      updateEbirdMarkersVisibility()
    }

    let targetMarker = ebirdMarkers.find((m) => m.getElement()?.dataset.sightingId === sId)
    if (!targetMarker && item.speciesCode) {
      targetMarker = ebirdMarkers.find(
        (m) => m.getElement()?.dataset.speciesCode === item.speciesCode
      )
    }
    if (!targetMarker && item.lng != null && item.lat != null) {
      targetMarker = ebirdMarkers.find((m) => {
        const pos = m.getLngLat()
        return Math.abs(pos.lng - item.lng) < 0.0002 && Math.abs(pos.lat - item.lat) < 0.0002
      })
    }

    const popup = targetMarker?.getPopup()
    if (selectedSightingId.value === sId && popup && popup.isOpen()) {
      popup.remove()
      currentOpenEbirdPopup = null
      selectedSightingId.value = null
      targetMarker?.getElement()?.classList.remove('is-focused')
      return
    }

    selectedSightingId.value = sId

    for (const m of ebirdMarkers) {
      m.getElement()?.classList.remove('is-focused')
    }
    if (targetMarker) {
      targetMarker.getElement()?.classList.add('is-focused')
    }

    const targetLng = item.lng ?? targetMarker?.getLngLat().lng
    const targetLat = item.lat ?? targetMarker?.getLngLat().lat
    if (targetLng != null && targetLat != null) {
      mapInstance.flyTo({
        center: [targetLng, targetLat],
        zoom: Math.max(mapInstance.getZoom(), 17.5),
        speed: 1.4,
        essential: true,
      })
    }

    if (targetMarker && popup) {
      if (currentOpenEbirdPopup && currentOpenEbirdPopup !== popup) {
        currentOpenEbirdPopup.remove()
      }
      popup.addTo(mapInstance)
      currentOpenEbirdPopup = popup
    }
  }

  function cleanupEbirdMarkers() {
    for (const m of ebirdMarkers) {
      m.remove()
    }
    ebirdMarkers = []
    if (currentOpenEbirdPopup) {
      currentOpenEbirdPopup.remove()
      currentOpenEbirdPopup = null
    }
  }

  return {
    ebirdSightingsData,
    ebirdLoading,
    ebirdActiveTab,
    selectedSightingId,
    isEbirdCardExpanded,
    currentTopList,
    updateEbirdMarkersVisibility,
    syncWithLayerToggle,
    toggleEbirdCard,
    toggleSightingMarker,
    renderEbirdOnMap,
    loadEbirdSightings,
    refreshEbirdSightings,
    focusOnSighting,
    cleanupEbirdMarkers,
  }
}
