import { useRef, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Textarea } from '@/components/ui/textarea'
import { fieldErrors } from '@/lib/labels'
import { useRefocus } from '@/lib/use-refocus'

export interface IdeaFormProps {
  // Rejects with the API error; validation issues are shown on the field, the rest goes to onError
  onSubmit: (content: string) => Promise<void>
  onError: (error: unknown) => void
  placeholder?: string
  autoFocus?: boolean
}

export function IdeaForm({ onSubmit, onError, placeholder = 'Nueva idea', autoFocus }: IdeaFormProps) {
  const [content, setContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const contentRef = useRef<HTMLInputElement | null>(null)
  useRefocus(busy, contentRef)

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
    <Field label="Contenido de la idea" hideLabel error={error}>
      <div className="action-input">
        <Textarea
          ref={contentRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={placeholder}
          disabled={busy}
          autoFocus={autoFocus}
          submitOnEnter
        />
        <Button type="submit" size="sm" loading={busy} loadingText="Añadiendo…">Añadir</Button>
      </div>
    </Field>
  </form>
}
