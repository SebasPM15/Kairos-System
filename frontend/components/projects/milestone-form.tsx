import { useRef, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { fieldErrors } from '@/lib/labels'
import { useRefocus } from '@/lib/use-refocus'

export interface MilestoneFormProps {
  // Rejects with the API error; validation issues are shown on the field, the rest goes to onError
  onSubmit: (title: string) => Promise<void>
  onError: (error: unknown) => void
}

export function MilestoneForm({ onSubmit, onError }: MilestoneFormProps) {
  const [title, setTitle] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const titleRef = useRef<HTMLInputElement | null>(null)
  useRefocus(busy, titleRef)

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
    <Field label="Título del hito" hideLabel error={error}>
      <div className="action-input">
        <Input ref={titleRef} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Nuevo hito" disabled={busy} />
        <Button type="submit" size="sm" loading={busy} loadingText="Añadiendo…">Añadir</Button>
      </div>
    </Field>
  </form>
}
