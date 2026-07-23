import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from 'recharts'
import { PackageX, AlertTriangle, Layers, IndianRupee } from 'lucide-react'
import { api, type InventoryIntelligenceProduct } from '@/lib/api'
import { formatNumber } from '@/lib/utils'
import { EmptyState } from '@/components/EmptyState'

const ABC_COLORS: Record<string, string> = { A: 'var(--color-signal)', B: 'var(--color-counter)', C: 'var(--color-ink-faint)' }
const MOVEMENT_COLORS: Record<string, string> = {
  fast: 'var(--color-positive)',
  medium: 'var(--color-warning)',
  slow: 'var(--color-negative)',
  unknown: 'var(--color-ink-faint)',
}

export function InventoryIntelligencePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['inventory-intelligence'],
    queryFn: api.getInventoryIntelligence,
  })

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ backgroundColor: 'var(--color-surface)' }} />
        ))}
      </div>
    )
  }

  if (!data || data.products.length === 0) {
    return (
      <EmptyState
        icon={Layers}
        title="No inventory data yet"
        description="Upload demand history and inventory levels from the Dashboard to see ABC analysis, movement classes, and stockout/dead-stock risk here."
      />
    )
  }

  const { summary, products } = data

  const abcChartData = ['A', 'B', 'C'].map((cls) => ({ name: cls, value: summary.abc_breakdown[cls] ?? 0 }))
  const movementChartData = ['fast', 'medium', 'slow', 'unknown']
    .filter((k) => (summary.movement_breakdown[k] ?? 0) > 0)
    .map((k) => ({ name: k, value: summary.movement_breakdown[k] ?? 0 }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          icon={IndianRupee}
          label="Total inventory value"
          value={`₹${formatNumber(summary.total_inventory_value)}`}
          color="var(--color-signal)"
        />
        <KpiCard
          icon={PackageX}
          label="Dead stock items"
          value={String(summary.dead_stock_count)}
          color="var(--color-ink-faint)"
        />
        <KpiCard
          icon={AlertTriangle}
          label="Stockout risk"
          value={String(summary.stockout_risk_count)}
          color="var(--color-negative)"
        />
        <KpiCard
          icon={Layers}
          label="Overstocked"
          value={String(summary.overstock_count)}
          color="var(--color-counter)"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card-surface p-5">
          <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-ink)' }}>
            ABC classification
          </p>
          <p className="text-xs mb-4" style={{ color: 'var(--color-ink-faint)' }}>
            Pareto split by trailing revenue contribution
          </p>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={abcChartData} layout="vertical" margin={{ left: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 12, fill: 'var(--color-ink-muted)' }} axisLine={false} tickLine={false} width={24} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--color-surface-raised)', border: '1px solid var(--color-border)', borderRadius: 10, fontSize: 12 }}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={22}>
                  {abcChartData.map((entry) => (
                    <Cell key={entry.name} fill={ABC_COLORS[entry.name]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card-surface p-5">
          <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-ink)' }}>
            Movement class
          </p>
          <p className="text-xs mb-4" style={{ color: 'var(--color-ink-faint)' }}>
            Annualized turnover: fast ≥12, medium 3–12, slow &lt;3
          </p>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={movementChartData} layout="vertical" margin={{ left: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 12, fill: 'var(--color-ink-muted)' }} axisLine={false} tickLine={false} width={48} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--color-surface-raised)', border: '1px solid var(--color-border)', borderRadius: 10, fontSize: 12 }}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={22}>
                  {movementChartData.map((entry) => (
                    <Cell key={entry.name} fill={MOVEMENT_COLORS[entry.name]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      <ProductTable products={products} />
    </div>
  )
}

function KpiCard({ icon: Icon, label, value, color }: { icon: typeof IndianRupee; label: string; value: string; color: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card-surface p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} style={{ color }} />
        <p className="text-[11px] uppercase tracking-wide" style={{ color: 'var(--color-ink-faint)' }}>
          {label}
        </p>
      </div>
      <p className="text-xl font-mono-data font-semibold" style={{ color: 'var(--color-ink)' }}>
        {value}
      </p>
    </motion.div>
  )
}

function Badge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span
      className="text-[11px] font-medium px-2 py-0.5 rounded-full inline-block"
      style={{ backgroundColor: color + '1a', color }}
    >
      {children}
    </span>
  )
}

function ProductTable({ products }: { products: InventoryIntelligenceProduct[] }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card-surface overflow-hidden">
      <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <p className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
          Product catalog
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ color: 'var(--color-ink-faint)' }}>
              <th className="text-left font-medium px-5 py-2.5 text-xs">Product</th>
              <th className="text-left font-medium px-3 py-2.5 text-xs">ABC</th>
              <th className="text-left font-medium px-3 py-2.5 text-xs">Movement</th>
              <th className="text-right font-medium px-3 py-2.5 text-xs">Days of cover</th>
              <th className="text-right font-medium px-3 py-2.5 text-xs">On hand</th>
              <th className="text-right font-medium px-3 py-2.5 text-xs">Value</th>
              <th className="text-left font-medium px-5 py-2.5 text-xs">Flags</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.product_id} style={{ borderTop: '1px solid var(--color-border)' }}>
                <td className="px-5 py-3">
                  <p className="font-medium" style={{ color: 'var(--color-ink)' }}>
                    {p.name}
                  </p>
                  <p className="text-xs font-mono-data" style={{ color: 'var(--color-ink-faint)' }}>
                    {p.sku}
                  </p>
                </td>
                <td className="px-3 py-3">
                  <Badge color={ABC_COLORS[p.abc_class]}>{p.abc_class}</Badge>
                </td>
                <td className="px-3 py-3">
                  <Badge color={MOVEMENT_COLORS[p.movement_class]}>{p.movement_class}</Badge>
                </td>
                <td className="text-right px-3 py-3 font-mono-data" style={{ color: 'var(--color-ink-muted)' }}>
                  {p.days_of_cover !== null ? `${formatNumber(p.days_of_cover, 1)}d` : '—'}
                </td>
                <td className="text-right px-3 py-3 font-mono-data" style={{ color: 'var(--color-ink-muted)' }}>
                  {formatNumber(p.on_hand_quantity)}
                </td>
                <td className="text-right px-3 py-3 font-mono-data" style={{ color: 'var(--color-ink-muted)' }}>
                  ₹{formatNumber(p.inventory_value)}
                </td>
                <td className="px-5 py-3">
                  <div className="flex gap-1.5 flex-wrap">
                    {p.stockout_risk && <Badge color="var(--color-negative)">stockout risk</Badge>}
                    {p.overstock && <Badge color="var(--color-counter)">overstock</Badge>}
                    {p.is_dead_stock && <Badge color="var(--color-ink-faint)">dead stock</Badge>}
                    {!p.has_inventory_data && <Badge color="var(--color-warning)">no inventory data</Badge>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}
