import type { Project } from '@/lib/types'
import { ProjectCard } from './project-card'

export interface ProjectListProps {
  projects: Project[]
  onOpen: (projectId: number) => void
}

export function ProjectList({ projects, onOpen }: ProjectListProps) {
  return <><div className="project-grid">{projects.map((project) => <ProjectCard key={project.id} project={project} onOpen={() => onOpen(project.id)} />)}</div>{projects.length === 0 && <div className="no-results"><h3>No encontramos proyectos</h3><p>Prueba con otro filtro o término de búsqueda.</p></div>}</>
}
