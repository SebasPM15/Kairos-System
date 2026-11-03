// Dialogs and toasts render inside .dashboard so they inherit the theme class that lives on it.
// Once the theme class moves to <html> this can return null (or be deleted) in this one place.
export function portalContainer(): HTMLElement | null {
  return typeof document === 'undefined' ? null : document.querySelector<HTMLElement>('.dashboard')
}

// Same element as a ref-like object, for portals that resolve their container after mounting
export const portalContainerRef = {
  get current(): HTMLElement | null { return portalContainer() },
}
