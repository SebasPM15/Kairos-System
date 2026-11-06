import type { Metadata } from 'next'
import { BotCommands } from '@/components/bot/bot-commands'
import { BotStatusCard } from '@/components/bot/bot-status-card'

export const metadata: Metadata = { title: 'Bot · Kairos' }

export default function Page() {
  return <>
    <BotStatusCard />
    <BotCommands />
  </>
}
