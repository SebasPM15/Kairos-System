import { SearchInput } from '@/components/ui/search-input'
import { Select } from '@/components/ui/select'
import { ProjectList } from '@/components/projects/project-list'
import { useDashboard } from './dashboard-context'

const FILTER_LABELS: [string, string][] = [
  ['all', 'Todos'], ['active', 'Activos'], ['paused', 'Pausa'], ['idea', 'Ideas'], ['done', 'Terminados'],
]

export function ProjectsSection() {
  const { projects, staleAfterDays, filter, setFilter, sort, setSort, query, setQuery, setSelectedId } = useDashboard()
  const visible = projects
    .filter((p) => filter === 'all' || p.status === filter)
    .filter((p) => p.name.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => sort === 'progress' ? b.progress - a.progress : b.days_since_activity - a.days_since_activity)
  return <section className="projects-section">
    <div className="section-heading">
      <div><p className="eyebrow">Vista general</p><h2>Todos tus proyectos</h2></div>
      <SearchInput value={query} onValueChange={setQuery} label="Buscar proyectos" placeholder="Buscar..." />
    </div>
    <div className="toolbar">
      <div className="filters">
        {FILTER_LABELS.map(([value, label]) => <button
          key={value}
          className={filter === value ? 'active' : ''}
          aria-pressed={filter === value}
          onClick={() => setFilter(value)}
        >{label}</button>)}
      </div>
      <label className="sort">Ordenar por <Select value={sort} onChange={(e) => setSort(e.target.value)}>
        <option value="touch">Días sin tocar</option>
        <option value="progress">Progreso</option>
      </Select></label>
    </div>
    <ProjectList projects={visible} onOpen={setSelectedId} onClearSearch={query ? () => setQuery('') : undefined} staleAfterDays={staleAfterDays} />
  </section>
}
