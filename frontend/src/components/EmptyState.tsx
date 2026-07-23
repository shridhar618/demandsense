import type { LucideIcon } from 'lucide-react'

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon
  title: string
  description: string
}) {
  return (
    <div className="card-surface flex flex-col items-center justify-center text-center gap-3 py-16 px-6">
      <Icon size={26} style={{ color: 'var(--color-ink-faint)' }} />
      <div>
        <p className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
          {title}
        </p>
        <p className="text-xs mt-1 max-w-xs" style={{ color: 'var(--color-ink-faint)' }}>
          {description}
        </p>
      </div>
    </div>
  )
}
