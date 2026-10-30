import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { fieldErrors } from '@/lib/labels'

export interface IdeaFormProps {
  // Rejects with the API error; validation issues are shown on the field, the rest goes to onError
  onSubmit: (content: string) => Promise<void>
  onError: (error: unknown) => void
  placeholder?: string
}

export function IdeaForm({ onSubmit, onError, placeholder = 'Nueva idea' }: IdeaFormProps) {
  const [content, setContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = content.trim()
    if (!trimmed) { setError('Este campo no puede estar vacío.'); return }
    setError(null); setBusy(true)
    try {
      await onSubmit(trimmed)
      setContent('')
    } catch (failure) {
      const byField = fieldErrors(failure)
      if (byField.content) setError(byField.content); else onError(failure)
    } finally { setBusy(false) }
  }

  return <form onSubmit={submit} noValidate aria-label="Nueva idea">
    <div className="action-input"><input value={content} onChange={(e) => setContent(e.target.value)} placeholder={placeholder} aria-label="Contenido de la idea" aria-invalid={!!error} /><Button type="submit" size="sm" disabled={busy}>Añadir</Button></div>
    {error && <p className="field-error">{error}</p>}
  </form>
}
