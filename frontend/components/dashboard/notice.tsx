import { AlertTriangle, X } from 'lucide-react'
import { Alert, AlertAction, AlertDescription } from '@/components/ui/alert'

export function Notice({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return <Alert variant="destructive" className="mb-7">
    <AlertTriangle />
    <AlertDescription className="text-destructive">{message}</AlertDescription>
    <AlertAction><button onClick={onDismiss} aria-label="Cerrar aviso"><X className="size-3.5" /></button></AlertAction>
  </Alert>
}
