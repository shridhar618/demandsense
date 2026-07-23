import { motion } from 'framer-motion'
import {
  ShoppingCart,
  TrendingUp,
  TrendingDown,
  CircleCheck,
  Gauge,
  ShieldAlert,
  IndianRupee,
} from 'lucide-react'
import type { Recommendation } from '@/lib/api'
import { formatNumber } from '@/lib/utils'

const ACTION_META: Record<
  Recommendation['action'],
  { label: string; icon: typeof ShoppingCart; color: string }
> = {
  purchase_immediately: { label: 'Purchase Immediately', icon: ShoppingCart, color: 'var(--color-negative)' },
  increase_inventory: { label: 'Increase Inventory', icon: TrendingUp, color: 'var(--color-warning)' },
  reduce_inventory: { label: 'Reduce Inventory', icon: TrendingDown, color: 'var(--color-counter)' },
  monitor: { label: 'Monitor', icon: CircleCheck, color: 'var(--color-positive)' },
}

const RISK_COLOR: Record<Recommendation['risk'], string> = {
  low: 'var(--color-positive)',
  medium: 'var(--color-warning)',
  high: 'var(--color-negative)',
}

const PRIORITY_LABEL: Record<Recommendation['priority'], string> = {
  low: 'Low priority',
  medium: 'Medium priority',
  high: 'High priority',
  critical: 'Critical priority',
}

export function RecommendationCard({ rec }: { rec: Recommendation }) {
  const meta = ACTION_META[rec.action]
  const Icon = meta.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-surface p-5"
      style={{ borderColor: meta.color + '55' }}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ backgroundColor: meta.color + '1a' }}
          >
            <Icon size={18} style={{ color: meta.color }} />
          </div>
          <div>
            <p className="font-display font-semibold text-sm" style={{ color: 'var(--color-ink)' }}>
              {meta.label}
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-ink-faint)' }}>
              {PRIORITY_LABEL[rec.priority]} · {(rec.confidence * 100).toFixed(0)}% confidence
            </p>
          </div>
        </div>
        <span
          className="text-[11px] font-medium px-2 py-1 rounded-full flex items-center gap-1 shrink-0"
          style={{ backgroundColor: RISK_COLOR[rec.risk] + '1a', color: RISK_COLOR[rec.risk] }}
        >
          <ShieldAlert size={11} />
          {rec.risk} risk
        </span>
      </div>

      <p className="text-sm leading-relaxed mb-3" style={{ color: 'var(--color-ink-muted)' }}>
        {rec.reason}
      </p>

      <div
        className="rounded-lg px-3 py-2.5 mb-4 text-xs leading-relaxed"
        style={{ backgroundColor: 'var(--color-surface-raised)', color: 'var(--color-ink-muted)' }}
      >
        {rec.business_impact}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <Metric icon={Gauge} label="Days of cover" value={rec.days_of_cover !== null ? `${formatNumber(rec.days_of_cover, 1)}d` : '—'} />
        <Metric icon={Gauge} label="Reorder point" value={rec.reorder_point !== null ? formatNumber(rec.reorder_point) : '—'} />
        <Metric icon={Gauge} label="Safety stock" value={rec.safety_stock !== null ? formatNumber(rec.safety_stock) : '—'} />
        <Metric icon={Gauge} label="EOQ" value={rec.economic_order_qty !== null ? formatNumber(rec.economic_order_qty) : '—'} />
      </div>

      <div className="flex items-center justify-between pt-3" style={{ borderTop: '1px solid var(--color-border)' }}>
        {rec.recommended_order_qty !== null && (
          <p className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
            {rec.recommended_order_qty >= 0 ? 'Order' : 'Reduce by'}{' '}
            <span className="font-mono-data" style={{ color: meta.color }}>
              {formatNumber(Math.abs(rec.recommended_order_qty))}
            </span>{' '}
            units
          </p>
        )}
        {rec.estimated_savings !== null && (
          <p className="text-sm flex items-center gap-1" style={{ color: 'var(--color-positive)' }}>
            <IndianRupee size={13} />
            <span className="font-mono-data font-medium">{formatNumber(rec.estimated_savings)}</span>
            <span className="text-xs" style={{ color: 'var(--color-ink-faint)' }}>
              estimated impact
            </span>
          </p>
        )}
      </div>
    </motion.div>
  )
}

function Metric({ icon: Icon, label, value }: { icon: typeof Gauge; label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] flex items-center gap-1 mb-1" style={{ color: 'var(--color-ink-faint)' }}>
        <Icon size={10} />
        {label}
      </p>
      <p className="text-sm font-mono-data font-medium" style={{ color: 'var(--color-ink)' }}>
        {value}
      </p>
    </div>
  )
}
