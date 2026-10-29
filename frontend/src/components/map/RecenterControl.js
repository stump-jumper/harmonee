/**
 * Mapbox GL IControl for recentering the view to the property boundaries/size.
 */
export class RecenterControl {
  constructor(options = {}) {
    this._onRecenter = options.onRecenter
    this._title = options.title || 'Recenter on property'
    this._container = null
    this._map = null
    this._clickHandler = this._handleClick.bind(this)
  }

  _handleClick(e) {
    e.preventDefault()
    if (typeof this._onRecenter === 'function') {
      this._onRecenter()
    }
  }

  onAdd(map) {
    this._map = map
    this._container = document.createElement('div')
    this._container.className = 'mapboxgl-ctrl mapboxgl-ctrl-group'

    const button = document.createElement('button')
    button.className = 'mapboxgl-ctrl-recenter'
    button.type = 'button'
    button.title = this._title
    button.setAttribute('aria-label', this._title)
    button.innerHTML = `
      <span class="mapboxgl-ctrl-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 8V5a2 2 0 0 1 2-2h3" />
          <path d="M16 3h3a2 2 0 0 1 2 2v3" />
          <path d="M21 16v3a2 2 0 0 1-2 2h-3" />
          <path d="M8 21H5a2 2 0 0 1-2-2v-3" />
          <circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" />
        </svg>
      </span>
    `

    button.addEventListener('click', this._clickHandler)
    this._container.appendChild(button)
    return this._container
  }

  onRemove() {
    if (this._container) {
      const button = this._container.querySelector('button')
      if (button) {
        button.removeEventListener('click', this._clickHandler)
      }
      if (this._container.parentNode) {
        this._container.parentNode.removeChild(this._container)
      }
    }
    this._container = null
    this._map = null
  }
}
