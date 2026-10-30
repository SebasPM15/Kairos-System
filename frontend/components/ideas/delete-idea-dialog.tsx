'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogTitle } from '@/components/ui/alert-dialog'
import type { Idea } from '@/lib/types'

export interface DeleteIdeaDialogProps {
  // The idea to confirm; null keeps the dialog closed
  idea: Idea | null
  onCancel: () => void
  onConfirm: (idea: Idea) => Promise<void>
}

export function DeleteIdeaDialog({ idea, onCancel, onConfirm }: DeleteIdeaDialogProps) {
  const [busy, setBusy] = useState(false)
  const confirm = async () => {
    if (!idea) return
    setBusy(true)
    try { await onConfirm(idea) } finally { setBusy(false) }
  }
  const container = typeof document === 'undefined' ? null : document.querySelector<HTMLElement>('.dashboard')

  return <AlertDialog open={idea !== null} onOpenChange={(open) => { if (!open) onCancel() }}>
    <AlertDialogContent container={container}>
      <AlertDialogTitle>¿Borrar esta idea?</AlertDialogTitle>
      <AlertDialogDescription>
        «{idea?.content}» se borrará de Kairos y no se puede deshacer. Si ya la exportaste, el archivo en Obsidian se queda como está: la exportación nunca borra nada del vault.
      </AlertDialogDescription>
      <AlertDialogFooter>
        <AlertDialogCancel>Cancelar</AlertDialogCancel>
        <Button variant="destructive" size="sm" disabled={busy} onClick={confirm}>Borrar idea</Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
}
