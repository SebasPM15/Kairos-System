'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { BotCommand } from '@/lib/types'
import { errorMessage } from '@/lib/labels'
import * as api from '@/lib/api'

type Load = { state: 'loading' } | { state: 'error'; message: string } | { state: 'ready'; commands: BotCommand[] }

// The catalog only exposes the full syntax; the arguments are whatever follows "/name"
const argumentsOf = (command: BotCommand) => command.syntax.replace(`/${command.name}`, '').trim()

export function BotCommands() {
  const [load, setLoad] = useState<Load>({ state: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let live = true
    api.bot.commands().then((commands) => live && setLoad({ state: 'ready', commands }), (error) => live && setLoad({ state: 'error', message: errorMessage(error) }))
    return () => { live = false }
  }, [attempt])

  const retry = () => { setLoad({ state: 'loading' }); setAttempt((n) => n + 1) }

  return <section className="projects-section"><div className="section-heading"><div><p className="eyebrow">Telegram</p><h2>Comandos del bot</h2></div></div>
    <p className="drawer-description">Escríbele al bot desde Telegram. El proyecto se indica con su slug, antes de los dos puntos.</p>
    {load.state === 'loading' && <div className="entries" aria-busy="true" aria-label="Cargando comandos">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[38px] rounded-[8px]" />)}</div>}
    {load.state === 'error' && <div className="state-panel" role="alert"><h3>No pudimos cargar los comandos</h3><p>{load.message}</p><Button variant="outline" onClick={retry}>Reintentar</Button></div>}
    {load.state === 'ready' && load.commands.length === 0 && <div className="state-panel"><h3>Sin comandos disponibles</h3><p>El bot no declara ningún comando.</p></div>}
    {load.state === 'ready' && load.commands.length > 0 && <table className="command-table"><thead><tr><th>Comando</th><th>Argumentos</th><th>Descripción</th></tr></thead><tbody>{load.commands.map((command) => <tr key={command.name}><td><code>/{command.name}</code></td><td><code>{argumentsOf(command) || '—'}</code></td><td>{command.description}</td></tr>)}</tbody></table>}
  </section>
}
