import { Button } from '@/components/ui/button'
import type { Project } from '@/lib/types'
import { ProjectCard } from './project-card'

export interface ProjectListProps {
  projects: Project[]
  onOpen: (projectId: number) => void
  // Offered in the empty state when a search text is the reason there are no results
  onClearSearch?: () => void
}

export function ProjectList({ projects, onOpen, onClearSearch }: ProjectListProps) {
  return <>
    <div className="project-grid">
      {projects.map((project) => <ProjectCard key={project.id} project={project} onOpen={() => onOpen(project.id)} />)}
    </div>
    {projects.length === 0 && <div className="no-results">
      <h3>No encontramos proyectos</h3>
      <p>Prueba con otro filtro o término de búsqueda.</p>
      {onClearSearch && <Button variant="outline" onClick={onClearSearch}>Limpiar búsqueda</Button>}
    </div>}
  </>
}
