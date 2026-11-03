// Theme persistence shared by the inline <head> script and the useTheme hook
export type Theme = 'light' | 'dark'

export const THEME_KEY = 'kairos-theme'

// Runs before first paint: puts the theme class and color-scheme on <html>. Dark is the default
// (the system preference is deliberately ignored) and also what renders if localStorage throws.
export const THEME_SCRIPT = `(function(){var d=document.documentElement,t='dark';try{if(localStorage.getItem('${THEME_KEY}')==='light')t='light'}catch(e){}d.classList.add(t);d.style.colorScheme=t})()`
