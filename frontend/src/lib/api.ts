import axios from 'axios'

const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1' })

export interface ValidationReport {
  stages: string[]
  issues: { issue: string }[]
  input_rows?: number
  products_discovered?: number
  error?: string
}

export interface Dataset {
  id: number
  filename: string
  uploaded_at: string
  status: 'processing' | 'validated' | 'failed'
  row_count: number
  rejected_row_count: number
  date_range_start: string | null
  date_range_end: string | null
  validation_report: ValidationReport
}

export interface Product {
  id: number
  sku: string
  name: string
  category: string | null
  record_count: number
}

export interface ModelMetrics {
  model_type: string
  mae: number | null
  rmse: number | null
  mape: number | null
  training_time_ms: number | null
  is_best: boolean
  feature_importance: Record<string, number> | null
  forecast_run_id: number
}

export interface TrainForecastResponse {
  product_id: number
  comparison_batch_id: string
  models: ModelMetrics[]
  best_model: string
}

export interface ForecastPoint {
  date: string
  predicted_value: number | null
  lower_bound: number | null
  upper_bound: number | null
  actual_value: number | null
}

export interface ForecastSeriesResponse {
  product_id: number
  product_name: string
  forecast_run_id: number
  model_type: string
  horizon_days: number
  metrics: ModelMetrics
  history: ForecastPoint[]
  forecast: ForecastPoint[]
}

export interface InventoryUploadResult {
  status: string
  row_count: number
  rejected_row_count: number
  validation_report: { stages?: string[]; issues?: { issue: string }[] }
  error: string | null
}

export interface Recommendation {
  id: number
  product_id: number
  forecast_run_id: number
  created_at: string
  action: 'purchase_immediately' | 'increase_inventory' | 'reduce_inventory' | 'monitor'
  reason: string
  confidence: number
  priority: 'low' | 'medium' | 'high' | 'critical'
  risk: 'low' | 'medium' | 'high'
  business_impact: string
  estimated_savings: number | null
  forecasted_demand_leadtime: number | null
  safety_stock: number | null
  reorder_point: number | null
  economic_order_qty: number | null
  days_of_cover: number | null
  recommended_order_qty: number | null
}

export interface InventoryIntelligenceProduct {
  product_id: number
  sku: string
  name: string
  category: string | null
  trailing_revenue: number
  trailing_quantity: number
  on_hand_quantity: number
  inventory_value: number
  turnover_ratio: number
  movement_class: 'fast' | 'medium' | 'slow' | 'unknown'
  is_dead_stock: boolean
  days_of_cover: number | null
  stockout_risk: boolean
  overstock: boolean
  has_inventory_data: boolean
  abc_class: 'A' | 'B' | 'C'
}

export interface InventoryIntelligenceSummary {
  total_products: number
  total_inventory_value: number
  dead_stock_count: number
  stockout_risk_count: number
  overstock_count: number
  abc_breakdown: Record<string, number>
  movement_breakdown: Record<string, number>
  as_of: string | null
}

export interface InventoryIntelligenceResponse {
  products: InventoryIntelligenceProduct[]
  summary: InventoryIntelligenceSummary
}

export const api = {
  uploadDataset: async (file: File): Promise<Dataset> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await client.post<Dataset>('/datasets/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  uploadInventory: async (file: File): Promise<InventoryUploadResult> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await client.post<InventoryUploadResult>('/inventory/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  listProducts: async (): Promise<Product[]> => {
    const { data } = await client.get<Product[]>('/products')
    return data
  },

  trainForecast: async (productId: number, horizonDays: number): Promise<TrainForecastResponse> => {
    const { data } = await client.post<TrainForecastResponse>('/forecasts/train', {
      product_id: productId,
      horizon_days: horizonDays,
    })
    return data
  },

  getLatestForecast: async (productId: number): Promise<ForecastSeriesResponse> => {
    const { data } = await client.get<ForecastSeriesResponse>(`/forecasts/${productId}/latest`)
    return data
  },

  generateRecommendation: async (productId: number): Promise<Recommendation> => {
    const { data } = await client.post<Recommendation>(`/decisions/${productId}/generate`)
    return data
  },

  getLatestRecommendation: async (productId: number): Promise<Recommendation> => {
    const { data } = await client.get<Recommendation>(`/decisions/${productId}/latest`)
    return data
  },

  getInventoryIntelligence: async (): Promise<InventoryIntelligenceResponse> => {
    const { data } = await client.get<InventoryIntelligenceResponse>('/inventory/intelligence')
    return data
  },
}
