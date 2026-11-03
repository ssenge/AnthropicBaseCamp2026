#!/usr/bin/env node
// Mechanical checks for Vue SFCs. Prints one JSON object per component.
// ponytail: regex over SFC text, swap for @vue/compiler-sfc if false positives become a problem
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const LONG_TEMPLATE = 100
const LONG_SCRIPT = 150

function block(source, tag) {
  const open = source.search(new RegExp(`^<${tag}[ >]`, 'm'))
  if (open === -1) return { text: '', line: 0 }
  const close = source.lastIndexOf(`</${tag}>`)
  return {
    text: source.slice(open, close === -1 ? undefined : close),
    line: source.slice(0, open).split('\n').length
  }
}

function matches(text, startLine, pattern) {
  const found = []
  text.split('\n').forEach((content, i) => {
    if (pattern.test(content)) found.push(startLine + i)
  })
  return found
}

export function analyze(source) {
  const template = block(source, 'template')
  const script = block(source, 'script')
  const lines = (b) => (b.text ? b.text.split('\n').length : 0)
  const isOptions = /^\s*(data\(\)|methods:|mounted\(\))/m.test(script.text)
  const findings = []
  const add = (rule, at, detail) => {
    if (at.length) findings.push({ rule, lines: at, detail })
  }

  add('index-key', matches(template.text, template.line, /:key="(index|i|idx)"/),
    'v-for uses the array index as its key')
  add('console', matches(script.text, script.line, /console\.(log|debug|info)\(/),
    'Debug logging left in the component')
  add('raw-http', matches(script.text, script.line, /axios\.|fetch\(|localhost:\d+/),
    'HTTP call outside client/src/api.js')
  add('var', matches(script.text, script.line, /^\s*var\s/), 'var instead of const/let')
  add('hardcoded-currency', matches(template.text, template.line, />\s*\$\{\{/),
    'Hardcoded $ ignores JPY; use formatCurrency')
  if (isOptions) add('options-api', [script.line], 'Options API; the project uses Composition API')
  if (lines(template) > LONG_TEMPLATE) add('long-template', [template.line], `Template is ${lines(template)} lines`)
  if (lines(script) > LONG_SCRIPT) add('long-script', [script.line], `Script is ${lines(script)} lines`)

  // Text between tags with no interpolation is probably a string that t() should own
  const untranslated = matches(template.text, template.line, />\s*[A-Z][a-z]+( [A-Za-z]+)*\s*</)
  add('hardcoded-text', untranslated, 'Literal text in the template, not passed through t()')

  // Calls in the template with arguments-free names are often derived data that should be computed
  const templateCalls = new Set(
    [...template.text.matchAll(/\{\{\s*(\w+)\(/g)].map((m) => m[1]).filter((name) => name !== 't')
  )

  return {
    templateLines: lines(template),
    scriptLines: lines(script),
    api: isOptions ? 'options' : /setup\s*\(|<script setup/.test(source) ? 'composition' : 'none',
    templateCalls: [...templateCalls],
    findings
  }
}

function collect(path) {
  if (statSync(path).isFile()) return path.endsWith('.vue') ? [path] : []
  return readdirSync(path).flatMap((name) =>
    name === 'node_modules' ? [] : collect(join(path, name))
  )
}

const args = process.argv.slice(2)
const roots = args.length ? args : ['client/src/views', 'client/src/components']
for (const file of roots.flatMap(collect).sort()) {
  const report = analyze(readFileSync(file, 'utf8'))
  console.log(JSON.stringify({ file: relative(process.cwd(), file), ...report }))
}
