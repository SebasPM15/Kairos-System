import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { fieldErrors } from '@/lib/labels'

export interface MilestoneFormProps {
  // Rejects with the API error; validation issues are shown on the field, the rest goes to onError
  onSubmit: (title: string) => Promise<void>
  onError: (error: unknown) => void
}

export function MilestoneForm({ onSubmit, onError }: MilestoneFormProps) {
  const [title, setTitle] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = title.trim()
    if (!trimmed) { setError('Este campo no puede estar vacío.'); return }
    setError(null); setBusy(true)
    try {
      await onSubmit(trimmed)
      setTitle('')
    } catch (failure) {
      const byField = fieldErrors(failure)
      if (byField.title) setError(byField.title); else onError(failure)
    } finally { setBusy(false) }
  }

  return <form onSubmit={submit} noValidate aria-label="Nuevo hito">
    <div className="action-input"><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Nuevo hito" aria-label="Título del hito" aria-invalid={!!error} /><Button type="submit" size="sm" disabled={busy}>Añadir</Button></div>
    {error && <p className="field-error">{error}</p>}
  </form>
}
