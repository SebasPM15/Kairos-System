'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { ExportSummary } from '@/lib/types'
import { errorMessage } from '@/lib/labels'
import * as api from '@/lib/api'

export interface ExportPanelProps {
  onClose: () => void
}

type Result = { state: 'idle' } | { state: 'running' } | { state: 'done'; summary: ExportSummary } | { state: 'error'; message: string }

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

export function ExportPanel({ onClose }: ExportPanelProps) {
  const [result, setResult] = useState<Result>({ state: 'idle' })

  const run = async () => {
    setResult({ state: 'running' })
    try { setResult({ state: 'done', summary: await api.vault.export() }) } catch (error) { setResult({ state: 'error', message: errorMessage(error) }) }
  }

  return <section className="export-panel" aria-label="Exportar a Obsidian">
    <div className="section-title"><span>Exportar a Obsidian</span><Button variant="ghost" size="sm" onClick={onClose}>Cerrar</Button></div>
    <p className="drawer-description">Escribe tus proyectos como archivos Markdown en la carpeta Kairos de tu vault. La exportación es unidireccional (Kairos → Obsidian): los cambios que hagas en esos archivos se sobrescriben y nunca se leen de vuelta. Tampoco borra nada: lo que ya no exista en Kairos se queda en el vault.</p>
    <Button size="sm" onClick={run} disabled={result.state === 'running'}>{result.state === 'running' ? 'Exportando…' : 'Exportar ahora'}</Button>
    {result.state === 'error' && <p className="field-error" role="alert">{result.message}</p>}
    {result.state === 'done' && <div className="export-result" role="status">
      <p><strong>Exportación lista.</strong> {plural(result.summary.projects_exported, 'proyecto exportado', 'proyectos exportados')}; {plural(result.summary.files_written, 'archivo escrito', 'archivos escritos')} y {plural(result.summary.files_unchanged, 'sin cambios', 'sin cambios')}.</p>
      {result.summary.orphans.length > 0 && <p>Carpetas en el vault sin proyecto (no se tocaron): {result.summary.orphans.join(', ')}.</p>}
    </div>}
  </section>
}
