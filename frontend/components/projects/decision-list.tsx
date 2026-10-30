import { Skeleton } from '@/components/ui/skeleton'
import type { Decision } from '@/lib/types'
import { formatDate } from '@/lib/format'

export interface DecisionListProps {
  // null while loading
  decisions: Decision[] | null
}

export function DecisionList({ decisions }: DecisionListProps) {
  if (decisions === null) return <Skeleton className="h-[38px] rounded-[7px]" aria-busy="true" />
  if (decisions.length === 0) return <p className="drawer-description">Este proyecto aún no tiene decisiones.</p>
  return <ul className="entries">{decisions.map((decision) => <li key={decision.id}><h4>{decision.title}</h4><p>{decision.rationale}</p><time dateTime={decision.created_at}>{formatDate(decision.created_at)}</time></li>)}</ul>
}
