import { motion } from 'framer-motion'
import type { Product } from '@/lib/api'
import { cn } from '@/lib/utils'

interface ProductSelectorProps {
  products: Product[]
  selectedId: number | null
  onSelect: (id: number) => void
}

export function ProductSelector({ products, selectedId, onSelect }: ProductSelectorProps) {
  if (products.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {products.map((product) => {
        const active = product.id === selectedId
        return (
          <motion.button
            key={product.id}
            layout
            onClick={() => onSelect(product.id)}
            className={cn(
              'px-3.5 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2'
            )}
            style={{
              backgroundColor: active ? 'var(--color-signal-dim)' : 'var(--color-surface)',
              border: `1px solid ${active ? 'var(--color-signal)' : 'var(--color-border)'}`,
              color: active ? 'var(--color-signal)' : 'var(--color-ink-muted)',
            }}
          >
            {product.name}
            <span
              className="text-[10px] font-mono-data px-1.5 py-0.5 rounded"
              style={{ backgroundColor: 'var(--color-surface-raised)', color: 'var(--color-ink-faint)' }}
            >
              {product.record_count}d
            </span>
          </motion.button>
        )
      })}
    </div>
  )
}
