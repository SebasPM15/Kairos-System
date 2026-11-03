import type { ReactNode } from 'react'
import { AppShell } from '@/components/dashboard/app-shell'
import { DashboardProvider } from '@/components/dashboard/dashboard-context'
import { Toaster } from '@/components/ui/toaster'

// Provider, shell and toaster mount once; only the page below changes on navigation
export default function AppLayout({ children }: { children: ReactNode }) {
  return <DashboardProvider>
    <AppShell>{children}</AppShell>
    <Toaster />
  </DashboardProvider>
}
