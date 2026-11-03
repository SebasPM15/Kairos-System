import type { Metadata } from 'next'
import { BotCommands } from '@/components/bot/bot-commands'

export const metadata: Metadata = { title: 'Bot · Kairos' }

export default function Page() {
  return <BotCommands />
}
