import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Users,
  Cpu,
  Layers,
  Sparkles,
  HardDrive,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Trash2,
  RefreshCw,
  FolderKanban
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { Badge } from '../../components/common/Badge';
import { MetricCard } from '../../components/common/MetricCard';
import api from '../../services/api';

export const AdminDashboardPage: React.FC = () => {
  const [adminData, setAdminData] = useState<any>(null);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [jobsList, setJobsList] = useState<any[]>([]);
  const [modelsList, setModelsList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [cleaning, setCleaning] = useState(false);
  const [cleanMessage, setCleanMessage] = useState<string | null>(null);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [overviewRes, usersRes, jobsRes, modelsRes] = await Promise.all([
        api.get('/admin/overview'),
        api.get('/admin/users'),
        api.get('/admin/jobs'),
        api.get('/admin/models')
      ]);
      setAdminData(overviewRes.data);
      setUsersList(usersRes.data);
      setJobsList(jobsRes.data);
      setModelsList(modelsRes.data);
    } catch (err) {
      console.error("Failed to load admin dashboard", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  const handleToggleModelStatus = async (modelId: string, currentEnabled: boolean) => {
    try {
      await api.patch(`/admin/models/${modelId}`, { enabled: !currentEnabled });
      setModelsList(modelsList.map(m => m.id === modelId ? { ...m, is_enabled: !currentEnabled } : m));
    } catch (err) {
      alert("Failed to update model status.");
    }
  };

  const handleToggleDeployment = async (modelId: string, currentStatus: string) => {
    const nextStatus = currentStatus === 'production' ? 'experimental' : 'production';
    try {
      await api.patch(`/admin/models/${modelId}`, { deployment_status: nextStatus });
      setModelsList(modelsList.map(m => m.id === modelId ? { ...m, deployment_status: nextStatus } : m));
    } catch (err) {
      alert("Failed to update deployment designation.");
    }
  };

  const handleToggleUser = async (userId: string) => {
    try {
      const res = await api.patch(`/admin/users/${userId}/toggle-status`);
      setUsersList(usersList.map(u => u.id === userId ? { ...u, is_active: res.data.is_active } : u));
    } catch (err) {
      alert("Failed to update user status.");
    }
  };

  const handleCleanTemp = async () => {
    try {
      setCleaning(true);
      const res = await api.post('/admin/storage/clean-temp');
      setCleanMessage(`Cleaned ${res.data.deleted_files} temporary processing files.`);
      setTimeout(() => setCleanMessage(null), 4000);
    } catch (err) {
      alert("Failed to clean temporary storage.");
    } finally {
      setCleaning(false);
    }
  };

  const metrics = adminData?.metrics;
  const sys = adminData?.system;

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sidebar text-xs font-mono text-neon-violet mb-1 border border-neon-violet/30 shadow-glow-purple">
            <ShieldAlert className="w-3.5 h-3.5 text-hot-pink" />
            <span>SECTION 03: PLATFORM ADMINISTRATOR INTERFACE</span>
          </div>
          <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
            Platform Administration & Infrastructure Health
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            Global monitoring of user accounts, restoration queue throughput, ML models, and computational resources.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <NeonButton
            variant="outline"
            size="sm"
            onClick={fetchAdminData}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Diagnostics
          </NeonButton>
          <NeonButton
            variant="danger"
            size="sm"
            disabled={cleaning}
            onClick={handleCleanTemp}
            icon={<Trash2 className="w-3.5 h-3.5" />}
          >
            {cleaning ? 'Cleaning...' : 'Purge Temp Storage'}
          </NeonButton>
        </div>
      </div>

      {cleanMessage && (
        <div className="p-3 rounded-lg bg-success/15 border border-success/30 text-success text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{cleanMessage}</span>
        </div>
      )}

      {/* Platform-Wide Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <MetricCard title="Registered Users" value={metrics?.total_users ?? 0} subtitle={`${metrics?.active_users ?? 0} active`} />
        <MetricCard title="Workspaces" value={metrics?.total_workspaces ?? 0} subtitle="Global workspaces" />
        <MetricCard title="Active Projects" value={metrics?.total_projects ?? 0} subtitle="Across all users" />
        <MetricCard title="Total Assets" value={metrics?.total_assets ?? 0} subtitle="Uploaded screenshots" />
        <MetricCard title="Completed Jobs" value={metrics?.completed_jobs ?? 0} subtitle="Successful runs" highlight={true} />
        <MetricCard title="Failed Jobs" value={metrics?.failed_jobs ?? 0} subtitle="Errors caught" />
      </div>

      {/* Infrastructure Resource Telemetry */}
      <div className="p-6 rounded-card bg-sidebar text-white border border-sidebar-panel shadow-glow-purple space-y-4">
        <h2 className="text-sm font-display font-bold text-white flex items-center gap-2">
          <Activity className="w-4 h-4 text-neon-violet" />
          Hardware & PyTorch Runtime Telemetry
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-xl bg-sidebar-panel border border-white/5 space-y-1">
            <span className="text-steel text-[10px] uppercase">PyTorch Framework</span>
            <div className="text-white font-bold">{sys?.pytorch_version || '2.15.0+cpu'}</div>
            <div className="text-[10px] text-neon-violet">{sys?.cuda_available ? 'CUDA Enabled' : 'CPU Threadpool Active'}</div>
          </div>
          <div className="p-3 rounded-xl bg-sidebar-panel border border-white/5 space-y-1">
            <span className="text-steel text-[10px] uppercase">RAM Utilization</span>
            <div className="text-white font-bold">{sys?.ram_used_gb || 0} / {sys?.ram_total_gb || 0} GB</div>
            <div className="text-[10px] text-hot-pink">{sys?.ram_percent || 0}% Allocated</div>
          </div>
          <div className="p-3 rounded-xl bg-sidebar-panel border border-white/5 space-y-1">
            <span className="text-steel text-[10px] uppercase">Storage Free Space</span>
            <div className="text-white font-bold">{sys?.disk_free_gb || 0} GB Free</div>
            <div className="text-[10px] text-success">Storage Healthy</div>
          </div>
          <div className="p-3 rounded-xl bg-sidebar-panel border border-white/5 space-y-1">
            <span className="text-steel text-[10px] uppercase">Worker Queue State</span>
            <div className="text-white font-bold">{metrics?.processing_jobs || 0} Active</div>
            <div className="text-[10px] text-laser-blue">FastAPI Background Runner</div>
          </div>
        </div>
      </div>

      {/* User Management Table */}
      <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-display font-bold text-text-primary">Registered User Accounts & Access Control</h2>
            <p className="text-xs text-text-secondary mt-0.5">Control platform accounts, view assigned roles, and toggle access.</p>
          </div>
          <Badge variant="primary">{usersList.length} Accounts</Badge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-steel font-mono text-[11px] uppercase">
                <th className="py-2.5 px-3">Full Name</th>
                <th className="py-2.5 px-3">Email Address</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Registered At</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {usersList.map((u) => (
                <tr key={u.id} className="hover:bg-surface-muted/40 transition-colors">
                  <td className="py-3 px-3 font-semibold text-text-primary">{u.full_name}</td>
                  <td className="py-3 px-3 font-mono text-steel">{u.email}</td>
                  <td className="py-3 px-3">
                    <Badge variant={u.role === 'administrator' ? 'ai' : 'neutral'} size="sm">
                      {u.role}
                    </Badge>
                  </td>
                  <td className="py-3 px-3">
                    {u.is_active ? (
                      <span className="text-success font-medium flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Active
                      </span>
                    ) : (
                      <span className="text-error font-medium flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" /> Deactivated
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-3 text-steel font-mono text-[11px]">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => handleToggleUser(u.id)}
                      className="text-xs text-royal-purple hover:underline font-medium"
                    >
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Governance & Six Restoration Architectures */}
      <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-sidebar text-[11px] font-mono text-neon-violet border border-neon-violet/30 mb-1">
              <Cpu className="w-3 h-3 text-hot-pink" />
              <span>ADMINISTRATOR MODEL GOVERNANCE</span>
            </div>
            <h2 className="text-base font-display font-bold text-text-primary">Six AI Restoration Architectures & Checkpoint Registry</h2>
            <p className="text-xs text-text-secondary mt-0.5">
              Full catalogue of classical, deep learning, super-resolution, and generative models visible exclusively to Platform Administrators.
            </p>
          </div>
          <Badge variant="ai">{modelsList.length} Technical Models</Badge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-steel font-mono text-[11px] uppercase">
                <th className="py-2.5 px-3">Model Architecture</th>
                <th className="py-2.5 px-3">Type & Version</th>
                <th className="py-2.5 px-3">Checkpoint / Path</th>
                <th className="py-2.5 px-3">Training Status</th>
                <th className="py-2.5 px-3">Designation</th>
                <th className="py-2.5 px-3">State</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {modelsList.map((m) => (
                <tr key={m.id} className="hover:bg-surface-muted/40 transition-colors">
                  <td className="py-3 px-3">
                    <div className="font-semibold text-text-primary flex items-center gap-1.5">
                      {m.name}
                      {m.is_primary && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-royal-purple text-white font-mono uppercase font-bold">
                          Primary
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-text-secondary line-clamp-1 max-w-xs">{m.purpose}</div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="font-mono text-text-primary">{m.model_type}</div>
                    <div className="text-[10px] text-steel font-mono">{m.model_version}</div>
                  </td>
                  <td className="py-3 px-3 font-mono">
                    {m.checkpoint_available ? (
                      <span className="text-success text-[11px] flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 shrink-0" />
                        <span className="truncate max-w-[140px]">{m.checkpoint_file}</span>
                      </span>
                    ) : (
                      <span className="text-warning text-[11px] flex items-center gap-1">
                        <XCircle className="w-3 h-3 shrink-0" /> Missing Checkpoint
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    <span className="text-[11px] text-text-secondary">{m.training_status}</span>
                  </td>
                  <td className="py-3 px-3">
                    <button
                      onClick={() => handleToggleDeployment(m.id, m.deployment_status)}
                      className={`text-[10px] px-2 py-0.5 rounded font-mono uppercase border font-semibold ${
                        m.deployment_status === 'production'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                          : (m.deployment_status === 'experimental' ? 'bg-amber-50 text-amber-700 border-amber-300' : 'bg-purple-50 text-royal-purple border-purple-200')
                      }`}
                      title="Click to toggle Production / Experimental"
                    >
                      {m.deployment_status}
                    </button>
                  </td>
                  <td className="py-3 px-3">
                    <Badge variant={m.is_enabled ? 'success' : 'neutral'} size="sm">
                      {m.is_enabled ? 'Active' : 'Disabled'}
                    </Badge>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => handleToggleModelStatus(m.id, m.is_enabled)}
                      className={`text-xs font-medium hover:underline ${
                        m.is_enabled ? 'text-error' : 'text-success'
                      }`}
                    >
                      {m.is_enabled ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Global Restoration Job Queue Monitoring */}
      <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
        <div>
          <h2 className="text-base font-display font-bold text-text-primary">Global Restoration Queue Inspection</h2>
          <p className="text-xs text-text-secondary mt-0.5">Real-time log of background model executions across all projects.</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-steel font-mono text-[11px] uppercase">
                <th className="py-2.5 px-3">Job ID</th>
                <th className="py-2.5 px-3">Model</th>
                <th className="py-2.5 px-3">Stage / Log</th>
                <th className="py-2.5 px-3">Progress</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Submitted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {jobsList.map((j) => (
                <tr key={j.id} className="hover:bg-surface-muted/40 transition-colors">
                  <td className="py-3 px-3 font-mono text-text-secondary">{j.id.slice(0, 8)}...</td>
                  <td className="py-3 px-3 font-medium text-text-primary">{j.model_name}</td>
                  <td className="py-3 px-3 text-text-secondary text-[11px] font-mono">{j.stage}</td>
                  <td className="py-3 px-3">
                    <div className="w-20 bg-mist rounded-full h-1.5 overflow-hidden">
                      <div className="h-full bg-gradient-brand rounded-full" style={{ width: `${j.progress}%` }} />
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <Badge variant={j.status === 'completed' ? 'success' : (j.status === 'failed' ? 'error' : 'pending')} size="sm">
                      {j.status}
                    </Badge>
                  </td>
                  <td className="py-3 px-3 text-steel font-mono text-[11px]">
                    {new Date(j.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

