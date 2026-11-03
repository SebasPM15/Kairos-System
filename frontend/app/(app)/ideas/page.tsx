import type { Metadata } from 'next'
import { IdeasRoute } from '@/components/dashboard/ideas-route'

export const metadata: Metadata = { title: 'Ideas · Kairos' }

export default function Page() {
  return <IdeasRoute />
}
