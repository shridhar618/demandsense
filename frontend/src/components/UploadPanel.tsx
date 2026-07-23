import { useCallback, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { UploadCloud, FileSpreadsheet, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface UploadPanelProps {
  onFileSelected: (file: File) => void
  isUploading: boolean
  title?: string
  hint?: string
  loadingLabel?: string
}

export function UploadPanel({
  onFileSelected,
  isUploading,
  title = 'Drop a demand history CSV, or click to browse',
  hint = 'requires columns: date, product_sku, quantity',
  loadingLabel = 'Validating, cleaning, and profiling your data…',
}: UploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files?.[0]
      if (file) onFileSelected(file)
    },
    [onFileSelected]
  )

  return (
    <motion.div
      layout
      onDragOver={(e) => {
        e.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => !isUploading && inputRef.current?.click()}
      className={cn(
        'card-surface flex flex-col items-center justify-center gap-3 py-14 px-6 cursor-pointer transition-colors',
        isDragging && 'border-[var(--color-signal)]'
      )}
      style={{
        borderColor: isDragging ? 'var(--color-signal)' : undefined,
        borderStyle: 'dashed',
        borderWidth: '1.5px',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFileSelected(file)
          e.target.value = ''
        }}
      />

      {isUploading ? (
        <>
          <Loader2 size={28} className="animate-spin" style={{ color: 'var(--color-signal)' }} />
          <p className="text-sm" style={{ color: 'var(--color-ink-muted)' }}>
            {loadingLabel}
          </p>
        </>
      ) : (
        <>
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center"
            style={{ backgroundColor: 'var(--color-signal-dim)' }}
          >
            <UploadCloud size={20} style={{ color: 'var(--color-signal)' }} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
              {title}
            </p>
            <p className="text-xs mt-1 flex items-center gap-1.5 justify-center" style={{ color: 'var(--color-ink-faint)' }}>
              <FileSpreadsheet size={12} />
              {hint}
            </p>
          </div>
        </>
      )}
    </motion.div>
  )
}
