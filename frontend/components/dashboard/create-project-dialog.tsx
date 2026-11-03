'use client'

import { Dialog, DialogContent } from '@/components/ui/dialog'
import { ProjectForm } from '@/components/projects/project-form'
import { useDashboard } from './dashboard-context'

// Success closes it (the context clears `creating`); 422 errors stay on their field inside the form
export function CreateProjectDialog() {
  const { creating, setCreating, createProject, showError } = useDashboard()
  return <Dialog open={creating} onOpenChange={(open) => { if (!open) setCreating(false) }}>
    <DialogContent title="Nuevo proyecto" eyebrow="Proyectos" focusFirstField>
      <ProjectForm onSubmit={createProject} onCancel={() => setCreating(false)} onError={showError} />
    </DialogContent>
  </Dialog>
}
