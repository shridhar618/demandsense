import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Sparkles, PackageOpen, TrendingUp, Boxes, Brain } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { UploadPanel } from '@/components/UploadPanel'
import { DatasetProfileCard } from '@/components/DatasetProfileCard'
import { ProductSelector } from '@/components/ProductSelector'
import { ModelComparisonTable } from '@/components/ModelComparisonTable'
import { ForecastChart } from '@/components/ForecastChart'
import { RecommendationCard } from '@/components/RecommendationCard'
import { EmptyState } from '@/components/EmptyState'

export function DashboardPage() {
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null)
  const [horizonDays, setHorizonDays] = useState(30)

  const productsQuery = useQuery({
    queryKey: ['products'],
    queryFn: api.listProducts,
  })

  const uploadMutation = useMutation({
    mutationFn: api.uploadDataset,
    onSuccess: (dataset) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      if (dataset.status === 'validated') {
        showToast(`Ingested ${dataset.row_count.toLocaleString()} rows from ${dataset.filename}`, 'success')
      } else {
        showToast(dataset.validation_report.error ?? 'Upload failed validation', 'error')
      }
    },
    onError: () => showToast('Upload failed — check the file and try again', 'error'),
  })

  const inventoryUploadMutation = useMutation({
    mutationFn: api.uploadInventory,
    onSuccess: (result) => {
      if (result.status === 'validated') {
        showToast(`Loaded inventory levels for ${result.row_count} product(s)`, 'success')
      } else {
        showToast(result.error ?? 'Inventory upload failed validation', 'error')
      }
    },
    onError: () => showToast('Inventory upload failed — check the file and try again', 'error'),
  })

  const trainMutation = useMutation({
    mutationFn: ({ productId, horizon }: { productId: number; horizon: number }) =>
      api.trainForecast(productId, horizon),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['forecast', result.product_id] })
      showToast(`Training complete — ${result.best_model === 'prophet' ? 'Prophet' : 'XGBoost'} performed best`, 'success')
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Training failed'
      showToast(message, 'error')
    },
  })

  const recommendationMutation = useMutation({
    mutationFn: (productId: number) => api.generateRecommendation(productId),
    onSuccess: (rec) => {
      queryClient.invalidateQueries({ queryKey: ['recommendation', rec.product_id] })
      showToast('Recommendation generated', 'success')
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Could not generate a recommendation'
      showToast(message, 'error')
    },
  })

  const forecastQuery = useQuery({
    queryKey: ['forecast', selectedProductId],
    queryFn: () => api.getLatestForecast(selectedProductId as number),
    enabled: selectedProductId !== null,
    retry: false,
  })

  const recommendationQuery = useQuery({
    queryKey: ['recommendation', selectedProductId],
    queryFn: () => api.getLatestRecommendation(selectedProductId as number),
    enabled: selectedProductId !== null && !!forecastQuery.data,
    retry: false,
  })

  const latestDataset = uploadMutation.data

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
          <UploadPanel
            isUploading={uploadMutation.isPending}
            onFileSelected={(file) => uploadMutation.mutate(file)}
          />
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3, delay: 0.05 }}>
          <UploadPanel
            isUploading={inventoryUploadMutation.isPending}
            onFileSelected={(file) => inventoryUploadMutation.mutate(file)}
            title="Drop an inventory levels CSV, or click to browse"
            hint="requires columns: product_sku, on_hand_quantity"
            loadingLabel="Loading current inventory positions…"
          />
        </motion.div>
      </div>

      {latestDataset && <DatasetProfileCard dataset={latestDataset} />}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs uppercase tracking-wide font-medium" style={{ color: 'var(--color-ink-faint)' }}>
            Products
          </p>
        </div>

        {productsQuery.isLoading ? (
          <div className="flex gap-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-9 w-32 rounded-lg animate-pulse" style={{ backgroundColor: 'var(--color-surface-raised)' }} />
            ))}
          </div>
        ) : productsQuery.data && productsQuery.data.length > 0 ? (
          <ProductSelector
            products={productsQuery.data}
            selectedId={selectedProductId}
            onSelect={setSelectedProductId}
          />
        ) : (
          <EmptyState
            icon={PackageOpen}
            title="No products yet"
            description="Upload a demand history CSV above to discover products and start forecasting."
          />
        )}
      </section>

      {selectedProductId !== null && (
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <label className="text-xs" style={{ color: 'var(--color-ink-muted)' }}>
              Forecast horizon
            </label>
            <input
              type="number"
              min={7}
              max={180}
              value={horizonDays}
              onChange={(e) => setHorizonDays(Number(e.target.value))}
              className="w-20 px-2 py-1.5 rounded-md text-sm font-mono-data"
              style={{
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-ink)',
              }}
            />
            <span className="text-xs" style={{ color: 'var(--color-ink-faint)' }}>
              days
            </span>

            <button
              disabled={trainMutation.isPending}
              onClick={() => trainMutation.mutate({ productId: selectedProductId, horizon: horizonDays })}
              className="ml-auto flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-opacity disabled:opacity-60"
              style={{ backgroundColor: 'var(--color-signal)', color: '#14151A' }}
            >
              <Sparkles size={14} />
              {trainMutation.isPending ? 'Training Prophet + XGBoost…' : 'Train forecast models'}
            </button>
          </div>

          {forecastQuery.isLoading && (
            <div className="h-80 rounded-2xl animate-pulse" style={{ backgroundColor: 'var(--color-surface)' }} />
          )}

          {forecastQuery.data && (
            <>
              <ForecastChart series={forecastQuery.data} />
            </>
          )}

          {trainMutation.data && (
            <ModelComparisonTable models={trainMutation.data.models} />
          )}

          {!forecastQuery.data && !forecastQuery.isLoading && !trainMutation.data && (
            <EmptyState
              icon={TrendingUp}
              title="No forecast yet for this product"
              description="Click “Train forecast models” to run Prophet and XGBoost and compare their accuracy."
            />
          )}

          {forecastQuery.data && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-wide font-medium flex items-center gap-1.5" style={{ color: 'var(--color-ink-faint)' }}>
                  <Brain size={12} />
                  Decision intelligence
                </p>
                <button
                  disabled={recommendationMutation.isPending}
                  onClick={() => recommendationMutation.mutate(selectedProductId)}
                  className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-opacity disabled:opacity-60"
                  style={{ border: '1px solid var(--color-border-strong)', color: 'var(--color-ink)' }}
                >
                  <Boxes size={13} />
                  {recommendationMutation.isPending ? 'Analyzing…' : 'Generate recommendation'}
                </button>
              </div>

              {recommendationQuery.isLoading && !recommendationMutation.data && (
                <div className="h-40 rounded-2xl animate-pulse" style={{ backgroundColor: 'var(--color-surface)' }} />
              )}

              {(recommendationMutation.data || recommendationQuery.data) && (
                <RecommendationCard rec={recommendationMutation.data ?? recommendationQuery.data!} />
              )}

              {!recommendationMutation.data &&
                !recommendationQuery.data &&
                !recommendationQuery.isLoading && (
                  <EmptyState
                    icon={Boxes}
                    title="No recommendation yet"
                    description="Upload inventory levels for this product, then click “Generate recommendation” to get a reorder decision with reasoning."
                  />
                )}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
