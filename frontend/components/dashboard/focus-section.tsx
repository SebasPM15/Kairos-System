import { ArrowUpRight } from 'lucide-react'
import { NO_NEXT_ACTION_FOCUS_PROMPT, formatCount } from '@/lib/labels'
import { StatusBadge } from '@/components/projects/status-badge'
import { useDashboard } from './dashboard-context'
import { preloadDialog } from './lazy-dialogs'

export function FocusSection() {
  const { projects, setSelectedId } = useDashboard()
  const focus = projects.filter((p) => p.status === 'active')
  if (focus.length === 0) return null
  return <section className="focus-section">
    <div className="section-heading">
      <div><p className="eyebrow">Ahora mismo</p><h2>En foco</h2></div>
      <span className="section-count">{formatCount('project', focus.length)}</span>
    </div>
    <div className="focus-grid">
      {focus.map((project, index) => <button key={project.id} className="focus-card" onClick={() => setSelectedId(project.id)} onPointerEnter={() => preloadDialog('drawer')} onFocus={() => preloadDialog('drawer')}>
        <div className="focus-number">0{index + 1}</div>
        <div className="focus-info">
          <StatusBadge status={project.status} />
          <h3>{project.name}</h3>
          <p>{project.next_action ?? NO_NEXT_ACTION_FOCUS_PROMPT}</p>
        </div>
        <ArrowUpRight />
      </button>)}
    </div>
  </section>
}
