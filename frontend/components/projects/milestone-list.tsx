import { Check } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import type { Milestone } from '@/lib/types'

export interface MilestoneListProps {
  // null while loading
  milestones: Milestone[] | null
  onToggle: (milestone: Milestone) => void
}

export function MilestoneList({ milestones, onToggle }: MilestoneListProps) {
  if (milestones === null) return <Skeleton className="h-[38px] rounded-[7px]" aria-busy="true" />
  if (milestones.length === 0) return <p className="drawer-description">Este proyecto aún no tiene hitos.</p>
  return <>{milestones.map((milestone) => <label key={milestone.id} className="milestone"><input type="checkbox" checked={milestone.done} onChange={() => onToggle(milestone)} /><span className="checkmark">{milestone.done ? <Check /> : null}</span><span className={milestone.done ? 'completed' : ''}>{milestone.title}</span></label>)}</>
}
