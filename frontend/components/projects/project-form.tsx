import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { fieldErrors } from '@/lib/labels'
import type { ProjectCreate } from '@/lib/types'

export interface ProjectFormProps {
  // Rejects with the API error; validation issues are shown per field, the rest goes to onError
  onSubmit: (data: ProjectCreate) => Promise<void>
  onCancel: () => void
  onError: (error: unknown) => void
}

export function ProjectForm({ onSubmit, onCancel, onError }: ProjectFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) { setErrors({ name: 'Este campo no puede estar vacío.' }); return }
    setErrors({}); setBusy(true)
    try {
      await onSubmit({ name: trimmed, description: description.trim() || undefined })
    } catch (error) {
      const byField = fieldErrors(error)
      if (Object.keys(byField).length > 0) setErrors(byField); else onError(error)
    } finally { setBusy(false) }
  }

  return <form className="form-panel" onSubmit={submit} noValidate aria-label="Nuevo proyecto">
    <label className="field-label" htmlFor="project-name">Nombre</label>
    <input id="project-name" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={!!errors.name} autoFocus />
    {errors.name && <p className="field-error">{errors.name}</p>}
    <label className="field-label" htmlFor="project-description">Descripción</label>
    <input id="project-description" value={description} onChange={(e) => setDescription(e.target.value)} aria-invalid={!!errors.description} />
    {errors.description && <p className="field-error">{errors.description}</p>}
    <div className="form-actions"><Button type="submit" size="sm" disabled={busy}>Crear proyecto</Button><Button type="button" size="sm" variant="ghost" onClick={onCancel}>Cancelar</Button></div>
  </form>
}
