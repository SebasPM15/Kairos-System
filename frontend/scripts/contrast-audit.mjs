// WCAG contrast audit for the theme tokens in app/globals.css.
// Usage (from frontend/): pnpm contrast. Exits 1 if a pair fails and is not a documented exception.
import { readFileSync } from 'node:fs'

const css = readFileSync(new URL('../app/globals.css', import.meta.url), 'utf8')

// Token values per theme; .light only overrides what it redefines
function tokens(selector) {
  const start = css.indexOf(selector + ' {')
  const body = start < 0 ? '' : css.slice(css.indexOf('{', start) + 1, css.indexOf('}', start))
  return Object.fromEntries([...body.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map(([, k, v]) => [k, v]))
}
const dark = tokens(':root')
const THEMES = { dark, light: { ...dark, ...tokens('.light') } }

// A color is a token name or { mix: token, alpha, over: token } (translucent tint over a background)
// Thresholds: 4.5 text, 3 UI and large text
const TEXT = 4.5, UI = 3
const SURFACES = ['background', 'card', 'soft', 'focus-from']
const text = (fg, bgs, min = TEXT) => bgs.map((bg) => ({ fg, bg, min }))
const badge = (fg, token, alpha, bgs) => bgs.map((over) => ({ fg, bg: { mix: token, alpha, over }, min: TEXT }))

const PAIRS = [
  ...['muted', 'accent-text', 'warm', 'danger', 'blue'].flatMap((fg) => text(fg, SURFACES)),
  ...text('line-strong', ['background', 'card', 'soft'], UI),
  ...text('text-soft', ['background', 'card', 'soft']),
  ...['focus-text', 'focus-number', 'foreground'].flatMap((fg) => text(fg, ['focus-from'])),
  ...['focus-text', 'focus-number'].flatMap((fg) => text(fg, ['card'])),
  ...text('primary-foreground', ['accent-text'], UI), // checkmark on its fill
  ...text('accent-text', ['background', 'card', 'soft'], UI), // focus ring, checked fill, active underline, progress fill
  ...badge('accent-text', 'accent-text', 0.11, ['card', 'focus-from']),
  ...badge('warm', 'warm', 0.1, ['card']),
  ...badge('blue', 'blue', 0.1, ['card']),
  ...badge('done-text', 'foreground', 0.07, ['card', 'soft', 'focus-from']),
]

// Known failures that are intentional; each needs the reason it is acceptable
const EXCEPTIONS = []

const channel = (v) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4 }
const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
const luminance = (hex) => { const [r, g, b] = rgb(hex).map(channel); return 0.2126 * r + 0.7152 * g + 0.0722 * b }
const ratio = (a, b) => { const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05) }
const hex = (c) => '#' + c.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')

function resolve(theme, color) {
  if (typeof color === 'string') return theme[color]
  const top = rgb(theme[color.mix]), under = rgb(theme[color.over])
  return hex(top.map((v, i) => v * color.alpha + under[i] * (1 - color.alpha)))
}
const label = (c) => (typeof c === 'string' ? c : `${c.mix} ${Math.round(c.alpha * 100)}% on ${c.over}`)

let failures = 0
for (const [name, theme] of Object.entries(THEMES)) {
  console.log(`\n${name}`)
  for (const { fg, bg, min } of PAIRS) {
    const r = ratio(resolve(theme, fg), resolve(theme, bg))
    const pair = `${label(fg)} / ${label(bg)}`
    const exception = EXCEPTIONS.find((e) => e.theme === name && e.pair === pair)
    const ok = r >= min
    if (!ok && !exception) failures++
    console.log(`${ok ? 'pass' : exception ? 'skip' : 'FAIL'}  ${r.toFixed(2).padStart(5)} (min ${min})  ${pair}${exception ? `  [${exception.reason}]` : ''}`)
  }
}
console.log(failures ? `\n${failures} failing pair(s)` : '\nAll pairs pass')
process.exit(failures ? 1 : 0)
