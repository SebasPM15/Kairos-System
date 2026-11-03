'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import type { ExportSummary } from '@/lib/types'
import { TOAST, errorMessage, exportSummaryText } from '@/lib/labels'
import { toast } from '@/components/ui/toaster'
import * as api from '@/lib/api'

export interface ExportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Result =
  | { state: 'idle' }
  | { state: 'running' }
  | { state: 'done'; summary: ExportSummary }
  | { state: 'error'; message: string }

const DESCRIPTION = 'Escribe tus proyectos como archivos Markdown en la carpeta Kairos de tu vault. La exportación es unidireccional (Kairos → Obsidian): los cambios que hagas en esos archivos se sobrescriben y nunca se leen de vuelta. Tampoco borra nada: lo que ya no exista en Kairos se queda en el vault.'

function ExportResult({ result }: { result: Result }) {
  if (result.state === 'error') return <p className="field-error" role="alert">{result.message}</p>
  if (result.state !== 'done') return null
  const { summary } = result
  return <div className="export-result" role="status">
    <p><strong>{TOAST.exportDone}.</strong> {exportSummaryText(summary)}</p>
    {summary.orphans.length > 0 && <p>Carpetas en el vault sin proyecto (no se tocaron): {summary.orphans.join(', ')}.</p>}
  </div>
}

// Mounted only while the dialog is open, so every opening starts from a clean state
function ExportBody({ onRunningChange }: { onRunningChange: (running: boolean) => void }) {
  const [result, setResult] = useState<Result>({ state: 'idle' })

  const run = async () => {
    setResult({ state: 'running' }); onRunningChange(true)
    try {
      const summary = await api.vault.export()
      setResult({ state: 'done', summary })
      toast.success(TOAST.exportDone, exportSummaryText(summary))
    } catch (error) {
      setResult({ state: 'error', message: errorMessage(error) })
    } finally { onRunningChange(false) }
  }

  return <>
    <Button size="sm" onClick={run} loading={result.state === 'running'} loadingText="Exportando…">Exportar ahora</Button>
    <ExportResult result={result} />
  </>
}

// The dialog stays open when the export ends so the summary can be read. While a request is in
// flight it cannot be dismissed (Escape, outside click or the close button), so a result is never lost.
export function ExportDialog({ open, onOpenChange }: ExportDialogProps) {
  const [running, setRunning] = useState(false)
  return <Dialog open={open} onOpenChange={(next) => { if (!next && running) return; onOpenChange(next) }}>
    <DialogContent title="Exportar a Obsidian" eyebrow="Vault" description={DESCRIPTION} closeDisabled={running}>
      <ExportBody onRunningChange={setRunning} />
    </DialogContent>
  </Dialog>
}
