import { Skeleton } from '@/components/ui/skeleton'
import type { Idea } from '@/lib/types'
import { formatDate } from '@/lib/format'

export interface IdeaListProps {
  // null while loading
  ideas: Idea[] | null
}

export function IdeaList({ ideas }: IdeaListProps) {
  if (ideas === null) return <Skeleton className="h-[38px] rounded-[7px]" aria-busy="true" />
  if (ideas.length === 0) return <p className="drawer-description">Este proyecto aún no tiene ideas.</p>
  return <ul className="entries">{ideas.map((idea) => <li key={idea.id}><p>{idea.content}</p><time dateTime={idea.created_at}>{formatDate(idea.created_at)}</time></li>)}</ul>
}
