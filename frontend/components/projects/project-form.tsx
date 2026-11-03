import { useRef, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { fieldErrors } from '@/lib/labels'
import { useRefocus } from '@/lib/use-refocus'
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
  const nameRef = useRef<HTMLInputElement | null>(null)
  useRefocus(busy, nameRef)

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
    <Field label="Nombre" error={errors.name}>
      <Input ref={nameRef} value={name} onChange={(e) => setName(e.target.value)} disabled={busy} autoFocus />
    </Field>
    <Field label="Descripción" error={errors.description}>
      <Textarea value={description} onChange={(e) => setDescription(e.target.value)} disabled={busy} submitOnEnter />
    </Field>
    <div className="form-actions">
      <Button type="submit" size="sm" disabled={busy}>{busy ? 'Creando…' : 'Crear proyecto'}</Button>
      <Button type="button" size="sm" variant="ghost" onClick={onCancel} disabled={busy}>Cancelar</Button>
    </div>
  </form>
}
