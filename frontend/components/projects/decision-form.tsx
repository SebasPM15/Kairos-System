import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { fieldErrors } from '@/lib/labels'
import type { DecisionCreate } from '@/lib/types'

export interface DecisionFormProps {
  // Rejects with the API error; validation issues are shown per field, the rest goes to onError
  onSubmit: (data: DecisionCreate) => Promise<void>
  onError: (error: unknown) => void
}

const EMPTY_MESSAGE = 'Este campo no puede estar vacío.'

export function DecisionForm({ onSubmit, onError }: DecisionFormProps) {
  const [title, setTitle] = useState('')
  const [rationale, setRationale] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const data = { title: title.trim(), rationale: rationale.trim() }
    const local: Record<string, string> = {}
    if (!data.title) local.title = EMPTY_MESSAGE
    if (!data.rationale) local.rationale = EMPTY_MESSAGE
    setErrors(local)
    if (Object.keys(local).length > 0) return
    setBusy(true)
    try {
      await onSubmit(data)
      setTitle(''); setRationale('')
    } catch (failure) {
      const byField = fieldErrors(failure)
      if (Object.keys(byField).length > 0) setErrors(byField); else onError(failure)
    } finally { setBusy(false) }
  }

  return <form className="form-panel" onSubmit={submit} noValidate aria-label="Nueva decisión">
    <label className="field-label" htmlFor="decision-title">Decisión</label>
    <input id="decision-title" value={title} onChange={(e) => setTitle(e.target.value)} aria-invalid={!!errors.title} />
    {errors.title && <p className="field-error">{errors.title}</p>}
    <label className="field-label" htmlFor="decision-rationale">Por qué</label>
    <input id="decision-rationale" value={rationale} onChange={(e) => setRationale(e.target.value)} aria-invalid={!!errors.rationale} />
    {errors.rationale && <p className="field-error">{errors.rationale}</p>}
    <div className="form-actions"><Button type="submit" size="sm" disabled={busy}>Registrar decisión</Button></div>
  </form>
}
