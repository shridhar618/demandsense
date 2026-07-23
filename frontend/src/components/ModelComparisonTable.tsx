import { motion } from 'framer-motion'
import { Trophy } from 'lucide-react'
import type { ModelMetrics } from '@/lib/api'
import { formatNumber } from '@/lib/utils'

const MODEL_LABELS: Record<string, string> = {
  prophet: 'Prophet',
  xgboost: 'XGBoost',
}

export function ModelComparisonTable({ models }: { models: ModelMetrics[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-surface overflow-hidden"
    >
      <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <p className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
          Model comparison
        </p>
        <p className="text-xs mt-0.5" style={{ color: 'var(--color-ink-faint)' }}>
          Evaluated on a held-out tail of actual history
        </p>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr style={{ color: 'var(--color-ink-faint)' }}>
            <th className="text-left font-medium px-5 py-2.5 text-xs">Model</th>
            <th className="text-right font-medium px-3 py-2.5 text-xs">MAE</th>
            <th className="text-right font-medium px-3 py-2.5 text-xs">RMSE</th>
            <th className="text-right font-medium px-3 py-2.5 text-xs">MAPE</th>
            <th className="text-right font-medium px-5 py-2.5 text-xs">Training time</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={m.model_type} style={{ borderTop: '1px solid var(--color-border)' }}>
              <td className="px-5 py-3">
                <span className="flex items-center gap-2 font-medium" style={{ color: 'var(--color-ink)' }}>
                  {m.is_best && <Trophy size={13} style={{ color: 'var(--color-signal)' }} />}
                  {MODEL_LABELS[m.model_type] ?? m.model_type}
                </span>
              </td>
              <td className="text-right px-3 py-3 font-mono-data" style={{ color: 'var(--color-ink-muted)' }}>
                {formatNumber(m.mae, 2)}
              </td>
              <td className="text-right px-3 py-3 font-mono-data" style={{ color: 'var(--color-ink-muted)' }}>
                {formatNumber(m.rmse, 2)}
              </td>
              <td className="text-right px-3 py-3 font-mono-data" style={{ color: 'var(--color-ink-muted)' }}>
                {m.mape !== null ? `${formatNumber(m.mape, 1)}%` : '—'}
              </td>
              <td className="text-right px-5 py-3 font-mono-data" style={{ color: 'var(--color-ink-muted)' }}>
                {formatNumber(m.training_time_ms)} ms
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  )
}
