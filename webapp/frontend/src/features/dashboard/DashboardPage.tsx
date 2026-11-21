import React, { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import {
  UploadCloud,
  Sparkles,
  SplitSquareVertical,
  BarChart3,
  CheckCircle2,
  Clock,
  Layers,
  FileText,
  AlertCircle,
  ArrowUpRight
} from 'lucide-react';
import { MetricCard } from '../../components/common/MetricCard';
import { NeonButton } from '../../components/common/NeonButton';
import { Badge } from '../../components/common/Badge';
import { projectService, restorationService, analyticsService, assetService } from '../../services/api';
import { Project, RestorationJob, Asset } from '../../types';

export const DashboardPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: Project | null }>();
  const [jobs, setJobs] = useState<RestorationJob[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true);
        const [jobsList, assetsList, stats] = await Promise.all([
          restorationService.listJobs({ project_id: currentProject?.id }),
          assetService.list({ project_id: currentProject?.id }),
          analyticsService.getOverview(currentProject?.id)
        ]);
        setJobs(jobsList);
        setAssets(assetsList);
        setOverview(stats);
      } catch (err) {
        console.error("Error loading dashboard data", err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, [currentProject?.id]);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Workspace & Project Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-card bg-surface border border-border shadow-card">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-royal-purple mb-1">
            <span className="w-2 h-2 rounded-full bg-royal-purple" />
            <span>HYBRID WORKSPACE: LEGACY UI RESTORATION</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-display font-bold text-text-primary tracking-tight">
            {currentProject ? currentProject.name : 'Legacy Enterprise UI Documentation'}
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-text-secondary">
            {currentProject?.description || 'Active software screenshot restoration and interface geometry preservation.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-3 shrink-0">
          <Link to="/upload">
            <NeonButton variant="primary" size="md" icon={<UploadCloud className="w-4 h-4" />}>
              Import Screenshot
            </NeonButton>
          </Link>
          <Link to="/restoration">
            <NeonButton variant="ai" size="md" icon={<Sparkles className="w-4 h-4" />}>
              Restoration Studio
            </NeonButton>
          </Link>
        </div>
      </div>

      {/* Quality Analytics & Project Overview Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Total UI Assets"
          value={assets.length}
          subtitle="Screenshots imported & versioned"
          icon={<Layers className="w-5 h-5" />}
          highlight={true}
        />
        <MetricCard
          title="Restoration Jobs"
          value={jobs.length}
          subtitle={`${jobs.filter(j => j.status === 'completed').length} completed successfully`}
          icon={<Sparkles className="w-5 h-5" />}
        />
        <MetricCard
          title="Avg PSNR"
          value={overview?.avg_psnr != null ? `${overview.avg_psnr} dB` : 'N/A'}
          subtitle={overview?.avg_psnr != null ? "Reference reconstruction fidelity" : "Awaiting restoration evaluations"}
          icon={<BarChart3 className="w-5 h-5" />}
          trend={overview?.total_evaluations ? `${overview.total_evaluations} evaluated` : undefined}
        />
        <MetricCard
          title="Avg OCR Consistency"
          value={overview?.avg_ocr_word_acc != null ? `${Math.round(overview.avg_ocr_word_acc * 100)}%` : 'N/A'}
          subtitle={overview?.avg_ocr_word_acc != null ? "Word & character geometry accuracy" : "Awaiting OCR text evaluations"}
          icon={<CheckCircle2 className="w-5 h-5" />}
          trend={overview?.total_evaluations ? `${overview.total_evaluations} evaluated` : undefined}
        />
      </div>

      {/* Asymmetric Section: Recent Jobs & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Recent Jobs Table */}
        <div className="lg:col-span-2 p-6 rounded-card bg-surface border border-border shadow-card">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div>
              <h2 className="text-base font-display font-bold text-text-primary">Recent Restoration Pipeline Jobs</h2>
              <p className="text-xs text-text-secondary mt-0.5">Real-time status derived from actual worker stages</p>
            </div>
            <Link to="/restoration" className="text-xs text-royal-purple font-semibold hover:underline flex items-center gap-1">
              View Studio <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="mt-4 overflow-x-auto">
            {jobs.length === 0 ? (
              <div className="text-center py-12 text-sm text-text-secondary">
                <AlertCircle className="w-8 h-8 text-steel mx-auto mb-2 opacity-50" />
                No restoration jobs submitted yet for this project.
                <div className="mt-3">
                  <Link to="/restoration">
                    <NeonButton variant="outline" size="sm">Start First Restoration</NeonButton>
                  </Link>
                </div>
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border text-steel font-mono text-[11px] uppercase">
                    <th className="py-2.5 px-3">Job ID</th>
                    <th className="py-2.5 px-3">Model</th>
                    <th className="py-2.5 px-3">Stage / Status</th>
                    <th className="py-2.5 px-3">Progress</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {jobs.slice(0, 6).map((job) => (
                    <tr key={job.id} className="hover:bg-surface-muted/50 transition-colors">
                      <td className="py-3 px-3 font-mono text-text-secondary">{job.id.slice(0, 8)}...</td>
                      <td className="py-3 px-3 font-medium text-text-primary">{job.model_name}</td>
                      <td className="py-3 px-3">
                        {job.status === 'completed' && <Badge variant="success">Completed</Badge>}
                        {job.status === 'processing' && <Badge variant="pending" glow>Processing</Badge>}
                        {job.status === 'validating' && <Badge variant="pending">Validating</Badge>}
                        {job.status === 'evaluating' && <Badge variant="ai">Evaluating</Badge>}
                        {job.status === 'queued' && <Badge variant="neutral">Queued</Badge>}
                        {job.status === 'failed' && <Badge variant="error">Failed</Badge>}
                      </td>
                      <td className="py-3 px-3">
                        <div className="w-24 bg-mist rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              job.status === 'completed' ? 'bg-success' : 'bg-gradient-brand'
                            }`}
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <Link to={`/comparison?assetId=${job.asset_id}`}>
                          <button className="text-royal-purple hover:text-electric-blue font-medium transition-colors">
                            Compare →
                          </button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right Column: AI Model Information & Quick Actions */}
        <div className="space-y-6">
          {/* Primary Model Highlight Card */}
          <div className="p-6 rounded-card bg-sidebar text-white border border-sidebar-panel shadow-glow-purple relative overflow-hidden">
            <div className="flex items-center justify-between text-xs font-mono text-neon-violet mb-2">
              <span>PRIMARY ARCHITECTURE</span>
              <span className="w-2 h-2 rounded-full bg-success animate-ping" />
            </div>
            <h3 className="text-lg font-display font-bold text-white">UI-Aware Residual U-Net</h3>
            <p className="mt-2 text-xs text-mist leading-relaxed">
              Formulation: <code>X̂ = Y + F_θ(Y)</code>. Trained with combined loss (L1 pixel reconstruction + SSIM structural similarity + Sobel boundary loss).
            </p>

            <div className="mt-4 pt-3 border-t border-white/10 space-y-1.5 text-xs font-mono text-steel">
              <div className="flex justify-between">
                <span>Loss Formula:</span>
                <span className="text-white">λ1·L1 + λ2·(1−SSIM) + λ3·L_edge</span>
              </div>
              <div className="flex justify-between">
                <span>Inference Device:</span>
                <span className="text-neon-violet">PyTorch CPU / Cuda</span>
              </div>
            </div>

            <div className="mt-5">
              <Link to="/restoration">
                <NeonButton variant="ai" size="sm" className="w-full" icon={<Sparkles className="w-4 h-4" />}>
                  Run Primary Model
                </NeonButton>
              </Link>
            </div>
          </div>

          {/* Quick Studio Tools */}
          <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-3">
            <h3 className="text-xs font-mono uppercase text-steel tracking-wider font-semibold">Fast Workflows</h3>
            <Link
              to="/comparison"
              className="p-3 rounded-lg border border-border hover:border-royal-purple/50 bg-white flex items-center gap-3 transition-colors group block"
            >
              <SplitSquareVertical className="w-4 h-4 text-royal-purple group-hover:scale-110 transition-transform" />
              <div>
                <div className="text-xs font-semibold text-text-primary">Comparison Studio</div>
                <div className="text-[11px] text-text-secondary">Draggable slider & difference overlay</div>
              </div>
            </Link>
            <Link
              to="/analytics"
              className="p-3 rounded-lg border border-border hover:border-royal-purple/50 bg-white flex items-center gap-3 transition-colors group block"
            >
              <BarChart3 className="w-4 h-4 text-hot-pink group-hover:scale-110 transition-transform" />
              <div>
                <div className="text-xs font-semibold text-text-primary">E1–E8 Research Experiments</div>
                <div className="text-[11px] text-text-secondary">Ablation analysis and benchmarks</div>
              </div>
            </Link>
            <Link
              to="/export"
              className="p-3 rounded-lg border border-border hover:border-royal-purple/50 bg-white flex items-center gap-3 transition-colors group block"
            >
              <FileText className="w-4 h-4 text-royal-blue group-hover:scale-110 transition-transform" />
              <div>
                <div className="text-xs font-semibold text-text-primary">PDF Quality Reports</div>
                <div className="text-[11px] text-text-secondary">Generate printable report & CSV</div>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

