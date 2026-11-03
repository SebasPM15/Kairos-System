import { useRef, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { fieldErrors } from '@/lib/labels'
import { useRefocus } from '@/lib/use-refocus'
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
  const titleRef = useRef<HTMLInputElement | null>(null)
  useRefocus(busy, titleRef)

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
    <Field label="Decisión" error={errors.title}>
      <Input ref={titleRef} value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy} autoFocus />
    </Field>
    <Field label="Por qué" error={errors.rationale}>
      <Textarea value={rationale} onChange={(e) => setRationale(e.target.value)} disabled={busy} submitOnEnter />
    </Field>
    <div className="form-actions">
      <Button type="submit" size="sm" disabled={busy}>{busy ? 'Registrando…' : 'Registrar decisión'}</Button>
    </div>
  </form>
}
