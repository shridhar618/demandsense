import { motion } from 'framer-motion'
import { CheckCircle2, AlertTriangle, FileText, Calendar, Hash } from 'lucide-react'
import type { Dataset } from '@/lib/api'
import { formatNumber } from '@/lib/utils'

export function DatasetProfileCard({ dataset }: { dataset: Dataset }) {
  const failed = dataset.status === 'failed'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-surface p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <FileText size={16} style={{ color: 'var(--color-ink-muted)' }} />
          <p className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
            {dataset.filename}
          </p>
        </div>
        <span
          className="text-[11px] font-medium px-2 py-0.5 rounded-full flex items-center gap-1"
          style={{
            backgroundColor: failed ? 'rgba(248,113,113,0.12)' : 'rgba(52,211,153,0.12)',
            color: failed ? 'var(--color-negative)' : 'var(--color-positive)',
          }}
        >
          {failed ? <AlertTriangle size={11} /> : <CheckCircle2 size={11} />}
          {dataset.status}
        </span>
      </div>

      {failed ? (
        <p className="text-sm" style={{ color: 'var(--color-negative)' }}>
          {dataset.validation_report.error}
        </p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <Stat icon={Hash} label="Rows ingested" value={formatNumber(dataset.row_count)} />
            <Stat icon={Hash} label="Rows rejected" value={formatNumber(dataset.rejected_row_count)} />
            <Stat
              icon={Calendar}
              label="Date range"
              value={
                dataset.date_range_start && dataset.date_range_end
                  ? `${dataset.date_range_start} → ${dataset.date_range_end}`
                  : '—'
              }
              small
            />
          </div>

          <div className="pt-4" style={{ borderTop: '1px solid var(--color-border)' }}>
            <p className="text-[11px] uppercase tracking-wide mb-2" style={{ color: 'var(--color-ink-faint)' }}>
              Pipeline stages
            </p>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {dataset.validation_report.stages?.map((stage) => (
                <span
                  key={stage}
                  className="text-[11px] px-2 py-1 rounded-md font-mono-data"
                  style={{ backgroundColor: 'var(--color-surface-raised)', color: 'var(--color-ink-muted)' }}
                >
                  {stage.replace(/_/g, ' ')}
                </span>
              ))}
            </div>

            {dataset.validation_report.issues?.length > 0 && (
              <ul className="space-y-1">
                {dataset.validation_report.issues.map((issue, i) => (
                  <li key={i} className="text-xs flex gap-1.5" style={{ color: 'var(--color-ink-muted)' }}>
                    <span style={{ color: 'var(--color-warning)' }}>·</span>
                    {issue.issue}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </motion.div>
  )
}

function Stat({
  icon: Icon,
  label,
  value,
  small,
}: {
  icon: typeof Hash
  label: string
  value: string
  small?: boolean
}) {
  return (
    <div>
      <p className="text-[11px] flex items-center gap-1 mb-1" style={{ color: 'var(--color-ink-faint)' }}>
        <Icon size={11} />
        {label}
      </p>
      <p
        className={small ? 'text-xs font-mono-data' : 'text-lg font-mono-data font-medium'}
        style={{ color: 'var(--color-ink)' }}
      >
        {value}
      </p>
    </div>
  )
}
