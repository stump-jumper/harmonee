import { computed, ref, watch } from 'vue'
import mapboxgl from 'mapbox-gl'
import {
  fetchInaturalistObservations,
  saveInaturalistUsername,
} from '../api/inaturalistApi.js'
import { getIconicTaxonIcon } from '../constants/mapConstants.js'
import { createGeoJSONCircle } from '../utils/geo.js'
import { escapeHtml, formatSightingDate } from '../utils/formatters.js'

export function buildObservationPopupHtml(obs) {
  const photoUrl = obs.taxon?.photoUrl || (obs.photos?.[0]?.url ?? '')
  const commonName = escapeHtml(obs.speciesGuess || obs.taxon?.preferredCommonName || 'Unknown')
  const sciName = escapeHtml(obs.taxon?.name || '')
  const quality = obs.qualityGrade === 'research' ? 'Research Grade' : 'Needs ID'
  const qualityClass = obs.qualityGrade === 'research' ? 'quality-research' : 'quality-needs-id'
  const propertyBadge = obs.insideProperty
    ? '<span class="popup-tag prop-tag">📍 On Property</span>'
    : `<span class="popup-tag dist-tag">📍 ${(obs.distanceMiles ?? 0).toFixed(2)} mi away</span>`
  const taxonIcon = getIconicTaxonIcon(obs.taxon?.iconicTaxonName)
  const observerName = escapeHtml(obs.user?.name || obs.user?.login || 'Observer')
  const description = obs.description ? `<div class="popup-obs-desc">${escapeHtml(obs.description)}</div>` : ''

  return `
    <div class="inaturalist-popup-content">
      <div class="popup-obs-top-row">
        <div class="popup-obs-thumb-wrap">
          ${
            photoUrl
              ? `<img
                  src="${escapeHtml(photoUrl)}"
                  alt="${commonName}"
                  class="popup-obs-thumb"
                  loading="lazy"
                  onerror="this.style.display='none'; if(this.nextElementSibling) this.nextElementSibling.style.display='flex';"
                />`
              : ''
          }
          <div class="popup-obs-thumb-fallback" style="${photoUrl ? 'display: none;' : ''}">
            ${taxonIcon}
          </div>
        </div>
        <div class="popup-obs-header">
          <div class="popup-obs-name">${commonName}</div>
          <div class="popup-obs-sci">${sciName}</div>
          <div class="popup-tag-row">
            <span class="popup-tag ${qualityClass}">✓ ${quality}</span>
            ${propertyBadge}
          </div>
        </div>
      </div>
      <div class="popup-obs-details">
        <div class="popup-obs-meta">
          <span>🕒 ${escapeHtml(formatSightingDate(obs.observedOn || obs.timeObservedAt))}</span>
          <span>👤 ${observerName}</span>
        </div>
        ${description}
        ${
          obs.uri
            ? `<div class="popup-obs-link">
                <a href="${escapeHtml(obs.uri)}" target="_blank" rel="noopener noreferrer">
                  View on iNaturalist ↗
                </a>
              </div>`
            : ''
        }
      </div>
    </div>
  `
}

export function useInaturalistObservations(
  mapRef,
  {
    isLayerVisible,
    setLayerVisibility,
    mapboxLib = mapboxgl,
    doc = globalThis.document,
  } = {}
) {
  const inaturalistData = ref(null)
  const inaturalistLoading = ref(false)
  const activeCategory = ref('all')
  const propertyOnly = ref(true)
  const scope = ref('property') // 'property' | 'vicinity' | 'all_user'
  const selectedObservationId = ref(null)
  const isPanelExpanded = ref(false)
  const isEditingUsername = ref(false)
  const usernameInput = ref('')

  let inaturalistMarkers = []
  let currentOpenPopup = null
  let lastLat = null
  let lastLon = null

  const filteredObservations = computed(() => {
    const list = inaturalistData.value?.observations || []
    if (activeCategory.value === 'all') return list
    if (activeCategory.value === 'Other') {
      const known = new Set(['Plantae', 'Insecta', 'Aves', 'Fungi'])
      return list.filter((o) => !known.has(o.taxon?.iconicTaxonName))
    }
    return list.filter((o) => o.taxon?.iconicTaxonName === activeCategory.value)
  })

  watch(activeCategory, () => {
    updateInaturalistMarkersVisibility()
  })

  function updateInaturalistMarkersVisibility() {
    const visible = isLayerVisible ? isLayerVisible('inaturalist-observations-layer') : false
    if (!visible && currentOpenPopup) {
      currentOpenPopup.remove()
      currentOpenPopup = null
    }
    for (const marker of inaturalistMarkers) {
      const el = marker.getElement()
      if (el) {
        if (!visible) {
          el.style.display = 'none'
        } else {
          const cat = el.dataset.iconicTaxon
          let matches = true
          if (activeCategory.value !== 'all') {
            if (activeCategory.value === 'Other') {
              matches = !['Plantae', 'Insecta', 'Aves', 'Fungi'].includes(cat)
            } else {
              matches = cat === activeCategory.value
            }
          }
          el.style.display = matches ? '' : 'none'
        }
      }
    }

    if (currentOpenPopup && visible && activeCategory.value !== 'all') {
      const currentObsId = selectedObservationId.value
      if (currentObsId) {
        const marker = inaturalistMarkers.find(
          (m) => m.getElement()?.dataset.obsId === String(currentObsId)
        )
        if (marker && marker.getElement()?.style.display === 'none') {
          currentOpenPopup.remove()
          currentOpenPopup = null
          selectedObservationId.value = null
        }
      }
    }

    const mapInstance = mapRef.value
    if (mapInstance && mapInstance.setLayoutProperty) {
      const visibility = visible ? 'visible' : 'none'
      if (mapInstance.getLayer('inaturalist-radius-fill')) {
        mapInstance.setLayoutProperty('inaturalist-radius-fill', 'visibility', visibility)
      }
      if (mapInstance.getLayer('inaturalist-radius-outline')) {
        mapInstance.setLayoutProperty('inaturalist-radius-outline', 'visibility', visibility)
      }
    }
  }

  function syncWithLayerToggle(visible) {
    isPanelExpanded.value = visible
    updateInaturalistMarkersVisibility()
  }

  function togglePanel() {
    isPanelExpanded.value = !isPanelExpanded.value
    if (setLayerVisibility) {
      setLayerVisibility('inaturalist-observations-layer', isPanelExpanded.value)
    }
    updateInaturalistMarkersVisibility()
  }

  function toggleObservationMarker(marker, obs) {
    const mapInstance = mapRef.value
    const obsId = obs.id
    const popup = marker.getPopup()
    const isCurrentlyOpen = popup && popup.isOpen()

    if (isCurrentlyOpen) {
      popup.remove()
      currentOpenPopup = null
      selectedObservationId.value = null
      for (const m of inaturalistMarkers) {
        m.getElement()?.classList.remove('is-focused')
      }
    } else {
      if (currentOpenPopup && currentOpenPopup !== popup) {
        currentOpenPopup.remove()
        currentOpenPopup = null
      }

      for (const m of inaturalistMarkers) {
        m.getElement()?.classList.remove('is-focused')
      }
      marker.getElement()?.classList.add('is-focused')
      selectedObservationId.value = obsId

      if (popup && mapInstance) {
        popup.setLngLat([obs.lng, obs.lat])
        popup.addTo(mapInstance)
        currentOpenPopup = popup
      }
    }
  }

  function renderObservationsOnMap(data, centerLat = lastLat, centerLon = lastLon) {
    const mapInstance = mapRef.value
    if (!mapInstance || !data || !doc) return

    cleanupInaturalistMarkers()

    const visible = isLayerVisible ? isLayerVisible('inaturalist-observations-layer') : false
    const visibility = visible ? 'visible' : 'none'

    // Add observation radius indicator layer if center coordinates provided
    if (centerLat != null && centerLon != null && typeof mapInstance.addSource === 'function') {
      const setupRadius = () => {
        if (!mapInstance || typeof mapInstance.getSource !== 'function') return
        const circleFeature = createGeoJSONCircle([centerLon, centerLat], 0.5)
        const srcId = 'inaturalist-radius-source'
        const fillId = 'inaturalist-radius-fill'
        const outlineId = 'inaturalist-radius-outline'

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
                'fill-color': '#22c55e',
                'fill-opacity': 0.04,
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
                'line-color': '#22c55e',
                'line-width': 1.5,
                'line-dasharray': [3, 2],
                'line-opacity': 0.7,
              },
            },
            beforeId
          )
        }
      }

      if (mapInstance.isStyleLoaded && mapInstance.isStyleLoaded()) {
        setupRadius()
      } else if (mapInstance.once) {
        mapInstance.once('load', setupRadius)
      }
    }

    const observations = data.observations || []
    for (const obs of observations) {
      if (obs.lng == null || obs.lat == null) continue

      const el = doc.createElement('div')
      el.className = 'inaturalist-map-marker'
      el.dataset.obsId = String(obs.id)
      el.dataset.iconicTaxon = obs.taxon?.iconicTaxonName || 'Other'
      if (!visible) el.style.display = 'none'

      const markerBody = doc.createElement('div')
      markerBody.className = 'marker-body'

      const pin = doc.createElement('div')
      pin.className = `inat-pin ${obs.isResearchGrade ? 'research-grade' : ''}`
      pin.innerHTML = getIconicTaxonIcon(obs.taxon?.iconicTaxonName) || '🌿'
      pin.title = `${obs.speciesGuess || obs.taxon?.preferredCommonName || 'Observation'} (${obs.taxon?.name || ''})`

      markerBody.appendChild(pin)
      el.appendChild(markerBody)

      const popup = new mapboxLib.Popup({
        offset: 20,
        closeButton: true,
        className: 'inaturalist-mapbox-popup',
      })
        .setLngLat([obs.lng, obs.lat])
        .setHTML(buildObservationPopupHtml(obs))

      popup.on('open', () => {
        if (currentOpenPopup && currentOpenPopup !== popup) {
          currentOpenPopup.remove()
        }
        currentOpenPopup = popup
      })

      popup.on('close', () => {
        el.classList.remove('is-focused')
        if (currentOpenPopup === popup) {
          currentOpenPopup = null
        }
        if (selectedObservationId.value === obs.id) {
          selectedObservationId.value = null
        }
      })

      const marker = new mapboxLib.Marker({
        element: el,
        anchor: 'center',
      })
        .setLngLat([obs.lng, obs.lat])
        .setPopup(popup)
        .addTo(mapInstance)

      el.addEventListener(
        'click',
        (e) => {
          e.stopImmediatePropagation()
          e.stopPropagation()
          toggleObservationMarker(marker, obs)
        },
        true
      )

      inaturalistMarkers.push(marker)
    }
  }

  async function loadInaturalistObservations(lat = lastLat, lon = lastLon) {
    if (lat != null) lastLat = lat
    if (lon != null) lastLon = lon
    if (lastLat == null || lastLon == null) return

    inaturalistLoading.value = true
    try {
      const data = await fetchInaturalistObservations({
        lat: lastLat,
        lon: lastLon,
        propertyOnly: propertyOnly.value,
        scope: scope.value,
        radiusMiles: 0.5,
      })
      inaturalistData.value = data
      if (data.observer?.login) {
        usernameInput.value = data.observer.login
      }
      if (mapRef.value) {
        renderObservationsOnMap(data, lastLat, lastLon)
      }
    } catch (err) {
      console.error('Failed to load iNaturalist observations:', err)
    } finally {
      inaturalistLoading.value = false
    }
  }

  function focusOnObservation(obs) {
    const mapInstance = mapRef.value
    if (!obs || !mapInstance) return
    const obsId = String(obs.id)

    if (isLayerVisible && !isLayerVisible('inaturalist-observations-layer')) {
      if (setLayerVisibility) {
        setLayerVisibility('inaturalist-observations-layer', true)
      }
      isPanelExpanded.value = true
      updateInaturalistMarkersVisibility()
    }

    const targetMarker = inaturalistMarkers.find(
      (m) => m.getElement()?.dataset.obsId === obsId
    )

    if (targetMarker) {
      if (mapInstance.flyTo) {
        mapInstance.flyTo({
          center: [obs.lng, obs.lat],
          zoom: Math.max(mapInstance.getZoom(), 19),
          duration: 900,
          essential: true,
        })
      } else if (mapInstance.setCenter) {
        mapInstance.setCenter([obs.lng, obs.lat])
      }
      setTimeout(() => {
        toggleObservationMarker(targetMarker, obs)
      }, 350)
    }
  }

  async function setScope(newScope) {
    if (scope.value === newScope) return
    scope.value = newScope
    propertyOnly.value = newScope === 'property'
    await loadInaturalistObservations()
  }

  async function setPropertyScope(onlyProperty) {
    await setScope(onlyProperty ? 'property' : 'vicinity')
  }

  async function updateUsername(newUsername) {
    try {
      inaturalistLoading.value = true
      await saveInaturalistUsername(newUsername)
      isEditingUsername.value = false
      await loadInaturalistObservations()
    } catch (err) {
      console.error('Failed to save iNaturalist username:', err)
    } finally {
      inaturalistLoading.value = false
    }
  }

  function cleanupInaturalistMarkers() {
    for (const m of inaturalistMarkers) {
      m.remove()
    }
    inaturalistMarkers = []
    if (currentOpenPopup) {
      currentOpenPopup.remove()
      currentOpenPopup = null
    }
  }

  return {
    inaturalistData,
    inaturalistLoading,
    activeCategory,
    propertyOnly,
    scope,
    selectedObservationId,
    isPanelExpanded,
    isEditingUsername,
    usernameInput,
    filteredObservations,
    syncWithLayerToggle,
    togglePanel,
    renderObservationsOnMap,
    loadInaturalistObservations,
    focusOnObservation,
    setScope,
    setPropertyScope,
    updateUsername,
    cleanupInaturalistMarkers,
  }
}
