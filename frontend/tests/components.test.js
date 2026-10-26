import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse, compileTemplate, compileScript } from '@vue/compiler-sfc'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const srcDir = path.resolve(__dirname, '../src')

function findVueFiles(dir) {
  const results = []
  const list = fs.readdirSync(dir, { withFileTypes: true })
  for (const entry of list) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      results.push(...findVueFiles(fullPath))
    } else if (entry.isFile() && entry.name.endsWith('.vue')) {
      results.push(fullPath)
    }
  }
  return results
}

const vueFiles = findVueFiles(srcDir)

test('finds all vue components in src', () => {
  assert.ok(vueFiles.length >= 10, `Expected at least 10 vue files, found ${vueFiles.length}`)
})

for (const filePath of vueFiles) {
  const relativeName = path.relative(srcDir, filePath).replace(/\\/g, '/')
  test(`compile SFC: ${relativeName}`, () => {
    const source = fs.readFileSync(filePath, 'utf-8')
    const { descriptor, errors } = parse(source, { filename: relativeName })

    assert.equal(errors.length, 0, `Parse errors in ${relativeName}: ${errors.map((e) => e.message).join(', ')}`)

    if (descriptor.template) {
      const templateResult = compileTemplate({
        id: relativeName,
        filename: relativeName,
        source: descriptor.template.content,
        compilerOptions: { isCustomElement: (tag) => tag.startsWith('mapbox-') },
      })
      assert.equal(
        templateResult.errors.length,
        0,
        `Template errors in ${relativeName}: ${templateResult.errors.map((e) => (typeof e === 'string' ? e : e.message)).join(', ')}`
      )
    }

    if (descriptor.script || descriptor.scriptSetup) {
      assert.doesNotThrow(() => {
        compileScript(descriptor, { id: relativeName })
      }, `Script compilation failed in ${relativeName}`)
    }
  })
}
