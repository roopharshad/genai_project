export type Role = 'owner' | 'admin' | 'member' | 'standard_user' | 'researcher' | 'administrator' | 'platform_admin';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  default_workspace_id?: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description?: string;
  owner_id: string;
  member_count?: number;
  created_at: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  asset_count?: number;
  created_at: string;
}

export interface AssetVersion {
  id: string;
  asset_id: string;
  version_number: number;
  version_type: 'original' | 'restored' | 'synthetic_degraded' | 'ai_reconstructed' | 'enhanced';
  stored_filename: string;
  file_size: number;
  width: number;
  height: number;
  model_id?: string;
  config_summary?: any;
  created_at: string;
}

export interface DegradationAnalysis {
  blur_metric_laplacian_var: number;
  noise_standard_deviation: number;
  edge_density_ratio: number;
  resolution_category?: 'low_res' | 'standard' | 'high_res';
  detected_degradations: {
    blur_detected: boolean;
    noise_detected: boolean;
    compression_artifacts: boolean;
    heavily_degraded: boolean;
  };
  recommended_model: string;
}

export interface Asset {
  id: string;
  project_id: string;
  original_filename: string;
  stored_filename: string;
  file_size: number;
  mime_type: string;
  width: number;
  height: number;
  resolution_category: 'low_res' | 'standard' | 'high_res';
  status: string;
  degradation_analysis?: DegradationAnalysis;
  created_at: string;
  versions?: AssetVersion[];
}

export interface ModelParameter {
  name: string;
  type: string;
  default: any;
  label: string;
  min?: number;
  max?: number;
}

export interface RestorationModel {
  id: string;
  name: string;
  category: string;
  purpose: string;
  is_primary: boolean;
  status: string;
  parameters: ModelParameter[];
}

export interface RestorationJob {
  id: string;
  project_id: string;
  asset_id: string;
  model_id: string;
  model_name: string;
  status: 'queued' | 'validating' | 'processing' | 'evaluating' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  stage: string;
  error_message?: string;
  config_params?: Record<string, any>;
  output_version_id?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface EvaluationResult {
  has_reference: boolean;
  psnr?: number;
  ssim?: number;
  lpips?: number;
  ocr_word_acc?: number;
  ocr_char_acc?: number;
  edge_preservation_score?: number;
  inference_time_ms?: number;
  model_memory_mb?: number;
  metrics_detail?: any;
}

export interface AnalyticsOverview {
  total_evaluations: number;
  avg_psnr: number | null;
  avg_ssim: number | null;
  avg_lpips: number | null;
  avg_ocr_word_acc: number | null;
  avg_edge_score: number | null;
  avg_inference_time_ms: number | null;
  model_breakdown?: Array<{
    model_id: string;
    model_name: string;
    count: number;
    avg_psnr: number | null;
    avg_ssim: number | null;
    avg_lpips: number | null;
    avg_ocr: number | null;
    avg_edge: number | null;
    avg_latency: number | null;
  }>;
  timeline?: Array<{
    id: string;
    time: string;
    psnr: number | null;
    ssim: number | null;
    ocr: number | null;
    edge: number | null;
    model_name: string;
    asset_filename: string;
  }>;
  recent_results: Array<{
    id: string;
    job_id: string;
    model_id?: string;
    model_name?: string;
    asset_filename?: string;
    psnr: number | null;
    ssim: number | null;
    lpips: number | null;
    ocr_word_acc: number | null;
    edge_score: number | null;
    inference_time_ms: number | null;
    created_at: string;
  }>;
}

export interface Experiment {
  id: string;
  experiment_code: string;
  name: string;
  description?: string;
  model_id: string;
  dataset_info?: any;
  hyperparameters?: any;
  metrics_summary?: {
    psnr?: number;
    ssim?: number;
    lpips?: number;
    ocr_word_acc?: number;
    edge_f1?: number;
    inference_time_ms?: number;
  };
  runtime_seconds?: number;
}

