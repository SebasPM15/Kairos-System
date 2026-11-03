// Saved preferences shared by the inline <head> script and the hooks that change them
export type Theme = 'light' | 'dark'
export type SidebarState = 'expanded' | 'collapsed'

export const THEME_KEY = 'kairos-theme'
export const SIDEBAR_KEY = 'kairos-sidebar'

// Runs before first paint, once: puts the theme class and color-scheme on <html> and, if the user
// chose a sidebar state, data-sidebar. Dark is the default (the system preference is deliberately
// ignored); without a saved sidebar choice the CSS decides by viewport width. Both reads sit in a
// try/catch, so blocked storage still renders correctly.
export const PREFS_SCRIPT = `(function(){var d=document.documentElement,t='dark',s='';try{if(localStorage.getItem('${THEME_KEY}')==='light')t='light';s=localStorage.getItem('${SIDEBAR_KEY}')||''}catch(e){}d.classList.add(t);d.style.colorScheme=t;if(s==='expanded'||s==='collapsed')d.setAttribute('data-sidebar',s)})()`
