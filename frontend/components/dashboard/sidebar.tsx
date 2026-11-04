'use client'

import Link from 'next/link'
import { Bot, ChartColumn, Lightbulb, LayoutGrid, Moon, PanelLeftClose, PanelLeftOpen, Sun, type LucideIcon } from 'lucide-react'
import { Tooltip } from '@/components/ui/tooltip'
import { useSidebar } from '@/lib/use-sidebar'
import { useTheme } from '@/lib/use-theme'
import { ROUTES, useDashboard, type View } from './dashboard-context'

export const NAV_ITEMS: { view: View; label: string; icon: LucideIcon }[] = [
  { view: 'projects', label: 'Proyectos', icon: LayoutGrid },
  { view: 'ideas', label: 'Ideas', icon: Lightbulb },
  { view: 'metrics', label: 'Métricas', icon: ChartColumn },
  { view: 'bot', label: 'Bot', icon: Bot },
]

export function SidebarBrand() {
  return <div className="sidebar-brand">
    <span className="brand-mark" aria-hidden="true">●</span>
    <span className="sidebar-label">Kairos</span>
  </div>
}

export function SidebarNav({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const { view } = useDashboard()
  return <nav className="sidebar-nav" aria-label="Secciones">
    {NAV_ITEMS.map(({ view: value, label, icon: Icon }) => <Tooltip
      key={value}
      label={label}
      disabled={!collapsed}
      render={<Link
        href={ROUTES[value]}
        className="sidebar-item"
        aria-current={view === value ? 'page' : undefined}
        onClick={onNavigate}
      />}
    >
      <Icon aria-hidden="true" />
      <span className="sidebar-label">{label}</span>
    </Tooltip>)}
  </nav>
}

function ThemeToggle({ collapsed }: { collapsed: boolean }) {
  const { theme, setTheme } = useTheme()
  const light = theme === 'light'
  return <Tooltip
    label={light ? 'Tema oscuro' : 'Tema claro'}
    disabled={!collapsed}
    render={<button type="button" className="sidebar-item" aria-label="Cambiar tema" onClick={() => setTheme(light ? 'dark' : 'light')} />}
  >
    {light ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />}
    <span className="sidebar-label">{light ? 'Tema oscuro' : 'Tema claro'}</span>
  </Tooltip>
}

// Placeholder until there is auth. get_current_user (backend/app/deps.py) is the only place that
// decides who the user is, so this is the single spot to swap for the real account.
function UserZone() {
  return <div className="sidebar-user">
    <span className="sidebar-avatar" aria-hidden="true">U</span>
    <span className="sidebar-label sidebar-user-text">
      <span>Usuario local</span>
      <span>Sin cuenta</span>
    </span>
  </div>
}

export function SidebarFooter({ collapsed }: { collapsed: boolean }) {
  return <div className="sidebar-footer">
    <ThemeToggle collapsed={collapsed} />
    <UserZone />
  </div>
}

function CollapseToggle({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const label = collapsed ? 'Expandir barra lateral' : 'Contraer barra lateral'
  return <Tooltip
    label={label}
    disabled={!collapsed}
    render={<button type="button" className="sidebar-item" aria-expanded={!collapsed} aria-controls="sidebar" aria-label={label} onClick={onToggle} />}
  >
    {collapsed ? <PanelLeftOpen aria-hidden="true" /> : <PanelLeftClose aria-hidden="true" />}
    <span className="sidebar-label">Contraer</span>
  </Tooltip>
}

// Desktop sidebar (from 761px). Expanded or collapsed comes from data-sidebar on <html>, so the
// first paint is already right; this component only reads it to know when tooltips are needed.
export function Sidebar() {
  const { collapsed, toggle } = useSidebar()
  return <aside id="sidebar" className="sidebar" aria-label="Barra lateral">
    <SidebarBrand />
    <SidebarNav collapsed={collapsed} />
    <div className="sidebar-collapse"><CollapseToggle collapsed={collapsed} onToggle={toggle} /></div>
    <SidebarFooter collapsed={collapsed} />
  </aside>
}
