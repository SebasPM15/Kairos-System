'use client'

import { useCallback, useSyncExternalStore } from 'react'
import { SIDEBAR_KEY, type SidebarState } from './prefs'

// Same breakpoint as the CSS: expanded by default from 1200px, collapsed below
const WIDE = '(min-width: 1200px)'

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-sidebar'] })
  const media = window.matchMedia(WIDE)
  media.addEventListener('change', onChange)
  return () => { observer.disconnect(); media.removeEventListener('change', onChange) }
}

function getSnapshot(): SidebarState {
  const saved = document.documentElement.getAttribute('data-sidebar')
  if (saved === 'expanded' || saved === 'collapsed') return saved
  return window.matchMedia(WIDE).matches ? 'expanded' : 'collapsed'
}

const getServerSnapshot = (): SidebarState => 'expanded'

// The data-sidebar attribute on <html> (set by the inline script) is what the CSS reads
export function useSidebar() {
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)

  const setState = useCallback((next: SidebarState) => {
    document.documentElement.setAttribute('data-sidebar', next)
    try { localStorage.setItem(SIDEBAR_KEY, next) } catch { /* storage blocked: the choice lasts until reload */ }
  }, [])

  return { collapsed: state === 'collapsed', toggle: () => setState(state === 'collapsed' ? 'expanded' : 'collapsed') }
}
