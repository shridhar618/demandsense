import { motion } from 'framer-motion'
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { ForecastSeriesResponse } from '@/lib/api'
import { formatDate } from '@/lib/utils'

interface ChartRow {
  date: string
  actual?: number
  predicted?: number
  band?: [number, number]
}

export function ForecastChart({ series }: { series: ForecastSeriesResponse }) {
  // Only show the trailing 90 days of history for legibility, plus the full forecast horizon
  const recentHistory = series.history.slice(-90)

  const rows: ChartRow[] = [
    ...recentHistory.map((p) => ({ date: p.date, actual: p.actual_value ?? undefined })),
    ...series.forecast.map((p) => ({
      date: p.date,
      predicted: p.predicted_value ?? undefined,
      band:
        p.lower_bound !== null && p.upper_bound !== null
          ? ([p.lower_bound, p.upper_bound] as [number, number])
          : undefined,
    })),
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-surface p-5"
    >
      <div className="flex items-center justify-between mb-1">
        <div>
          <p className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
            {series.product_name} — {series.horizon_days}-day forecast
          </p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-ink-faint)' }}>
            Best model: {series.model_type === 'prophet' ? 'Prophet' : 'XGBoost'}
          </p>
        </div>
      </div>

      <div className="h-80 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 11, fill: 'var(--color-ink-faint)' }}
              axisLine={{ stroke: 'var(--color-border)' }}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              tick={{ fontSize: 11, fill: 'var(--color-ink-faint)' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--color-surface-raised)',
                border: '1px solid var(--color-border)',
                borderRadius: 10,
                fontSize: 12,
              }}
              labelFormatter={(label) => formatDate(String(label))}
              labelStyle={{ color: 'var(--color-ink)' }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: 'var(--color-ink-muted)' }} />
            <Area
              dataKey="band"
              stroke="none"
              fill="var(--color-signal)"
              fillOpacity={0.12}
              name="Confidence interval"
              connectNulls
            />
            <Line
              dataKey="actual"
              stroke="var(--color-counter)"
              strokeWidth={2}
              dot={false}
              name="Actual demand"
              connectNulls
            />
            <Line
              dataKey="predicted"
              stroke="var(--color-signal)"
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={false}
              name="Forecast"
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  )
}
