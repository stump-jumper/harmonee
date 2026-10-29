import test from 'node:test'
import assert from 'node:assert/strict'
import { RecenterControl } from '../src/components/map/RecenterControl.js'

// Simple mock for browser document if running in node environment without full DOM
class MockElement {
  constructor(tagName) {
    this.tagName = tagName
    this.className = ''
    this.innerHTML = ''
    this.type = ''
    this.title = ''
    this.attributes = new Map()
    this.children = []
    this.parentNode = null
    this.listeners = new Map()
  }

  setAttribute(name, val) {
    this.attributes.set(name, val)
  }

  getAttribute(name) {
    return this.attributes.get(name)
  }

  appendChild(child) {
    this.children.push(child)
    child.parentNode = this
    return child
  }

  removeChild(child) {
    const idx = this.children.indexOf(child)
    if (idx !== -1) {
      this.children.splice(idx, 1)
      child.parentNode = null
    }
  }

  querySelector(selector) {
    if (selector === 'button') {
      return this.children.find((c) => c.tagName === 'button') || null
    }
    return null
  }

  addEventListener(event, fn) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(fn)
  }

  removeEventListener(event, fn) {
    if (this.listeners.has(event)) {
      const list = this.listeners.get(event).filter((l) => l !== fn)
      this.listeners.set(event, list)
    }
  }

  click() {
    const list = this.listeners.get('click') || []
    for (const fn of list) {
      fn({ preventDefault: () => {} })
    }
  }
}

test('RecenterControl creates container and button with correct attributes and icon', () => {
  const origDoc = globalThis.document
  globalThis.document = {
    createElement: (tag) => new MockElement(tag),
  }

  try {
    let recenterCalled = false
    const control = new RecenterControl({
      onRecenter: () => {
        recenterCalled = true
      },
    })

    const fakeMap = {}
    const container = control.onAdd(fakeMap)

    assert.ok(container)
    assert.equal(container.className, 'mapboxgl-ctrl mapboxgl-ctrl-group')
    assert.equal(container.children.length, 1)

    const button = container.children[0]
    assert.equal(button.className, 'mapboxgl-ctrl-recenter')
    assert.equal(button.title, 'Recenter on property')
    assert.equal(button.getAttribute('aria-label'), 'Recenter on property')
    assert.ok(button.innerHTML.includes('<svg'))
    assert.ok(button.innerHTML.includes('viewBox="0 0 24 24"'))

    // Trigger click
    button.click()
    assert.equal(recenterCalled, true)

    // Test onRemove
    const parent = new MockElement('div')
    parent.appendChild(container)
    control.onRemove()
    assert.equal(parent.children.length, 0)
  } finally {
    globalThis.document = origDoc
  }
})
