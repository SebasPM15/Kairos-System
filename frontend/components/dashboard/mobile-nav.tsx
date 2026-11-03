'use client'

import { Dialog, DialogContent } from '@/components/ui/dialog'
import { SidebarFooter, SidebarNav } from './sidebar'

// The sidebar at 760px and below: same links and footer inside the left-hand Dialog.
// Closes on navigation, Escape or an outside click; focus returns to the menu button.
export function MobileNav({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent variant="side" side="left" id="mobile-nav" title="Menú">
      <SidebarNav collapsed={false} onNavigate={() => onOpenChange(false)} />
      <SidebarFooter collapsed={false} />
    </DialogContent>
  </Dialog>
}
