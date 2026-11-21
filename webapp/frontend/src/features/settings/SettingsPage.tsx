import React, { useState, useEffect } from 'react';
import {
  Settings,
  User,
  Shield,
  Users,
  Cpu,
  Sparkles,
  Save,
  CheckCircle2,
  HardDrive,
  Database,
  Terminal
} from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { Badge } from '../../components/common/Badge';
import { settingsService } from '../../services/api';

export const SettingsPage: React.FC = () => {
  const [settingsData, setSettingsData] = useState<any>(null);
  const [fullName, setFullName] = useState('');
  const [neonGlowEnabled, setNeonGlowEnabled] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    settingsService.get().then((data) => {
      setSettingsData(data);
      if (data?.profile?.full_name) {
        setFullName(data.profile.full_name);
      }
    }).catch(() => {});
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await settingsService.updateProfile(fullName);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      alert("Failed to update profile.");
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-muted text-xs font-mono text-royal-purple mb-1 border border-border">
          <Settings className="w-3.5 h-3.5" />
          <span>INTERFACE 09: PROFESSIONAL SETTINGS & ADMINISTRATION</span>
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
          System Preferences & Platform Administration
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Manage user credentials, workspace access roles, AI model preferences, and view platform runtime health.
        </p>
      </div>

      {savedSuccess && (
        <div className="p-3 rounded-lg bg-success/15 border border-success/30 text-success text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>Profile changes saved successfully.</span>
        </div>
      )}

      {/* Grid: Profile & Workspace Members */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Profile Card */}
        <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-border">
            <User className="w-4 h-4 text-royal-purple" />
            <h2 className="text-sm font-display font-bold text-text-primary">User Account Profile</h2>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-4 text-xs">
            <div>
              <label className="font-semibold text-text-primary block mb-1">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-white text-text-primary focus:outline-none focus:ring-2 focus:ring-focus"
              />
            </div>
            <div>
              <label className="font-semibold text-text-primary block mb-1">Email Address</label>
              <input
                type="email"
                disabled
                value={settingsData?.profile?.email || 'demo@docrestore.ai'}
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface-muted text-steel cursor-not-allowed font-mono"
              />
            </div>
            <div>
              <label className="font-semibold text-text-primary block mb-1">Platform Role</label>
              <div className="inline-block">
                <Badge variant="primary">{settingsData?.profile?.role || 'administrator'}</Badge>
              </div>
            </div>

            <div className="pt-2">
              <NeonButton variant="primary" size="sm" type="submit" icon={<Save className="w-3.5 h-3.5" />}>
                Save Changes
              </NeonButton>
            </div>
          </form>
        </div>

        {/* Workspace Members & Roles */}
        <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-hot-pink" />
              <h2 className="text-sm font-display font-bold text-text-primary">Workspace Members & RBAC</h2>
            </div>
            <Badge variant="neutral">
              {settingsData?.workspace?.name || 'Default Workspace'}
            </Badge>
          </div>

          <div className="space-y-3">
            {settingsData?.workspace?.members?.map((m: any) => (
              <div key={m.id} className="p-3 rounded-lg border border-border bg-white flex items-center justify-between text-xs">
                <div>
                  <div className="font-semibold text-text-primary">{m.full_name}</div>
                  <div className="text-[11px] text-steel font-mono">{m.email}</div>
                </div>
                <Badge variant={m.role === 'owner' ? 'ai' : 'primary'} size="sm">
                  {m.role}
                </Badge>
              </div>
            )) || (
              <div className="p-3 rounded-lg border border-border bg-white flex items-center justify-between text-xs">
                <div>
                  <div className="font-semibold text-text-primary">Dr. Alex Vance</div>
                  <div className="text-[11px] text-steel font-mono">demo@docrestore.ai</div>
                </div>
                <Badge variant="ai" size="sm">Owner</Badge>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Visual Identity & AI Model Preferences */}
      <div className="p-6 rounded-card bg-surface border border-border shadow-card space-y-5">
        <h2 className="text-sm font-display font-bold text-text-primary flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-neon-violet" />
          Visual Mode & AI Restoration Preferences
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-xl border border-border bg-surface-muted flex items-center justify-between">
            <div>
              <div className="font-semibold text-text-primary">Extreme Neon Glow Effects</div>
              <div className="text-[11px] text-text-secondary mt-0.5">Toggle glowing neon accents on buttons & borders</div>
            </div>
            <input
              type="checkbox"
              checked={neonGlowEnabled}
              onChange={(e) => setNeonGlowEnabled(e.target.checked)}
              className="w-4 h-4 accent-royal-purple cursor-pointer"
            />
          </div>

          <div className="p-4 rounded-xl border border-border bg-surface-muted flex items-center justify-between">
            <div>
              <div className="font-semibold text-text-primary">Automatic Metric Evaluation</div>
              <div className="text-[11px] text-text-secondary mt-0.5">Run PSNR, SSIM & Sobel edge evaluation on job completion</div>
            </div>
            <input
              type="checkbox"
              defaultChecked
              className="w-4 h-4 accent-royal-purple cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Platform Administration Diagnostics */}
      <div className="p-6 rounded-card bg-sidebar text-white border border-sidebar-panel shadow-glow-purple space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-white/10">
          <Terminal className="w-4 h-4 text-neon-violet" />
          <h2 className="text-sm font-display font-bold text-white">Platform Runtime & System Diagnostics</h2>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-sidebar-panel border border-white/5">
            <span className="text-steel text-[10px] uppercase">Engine Framework</span>
            <div className="text-white font-bold mt-1">PyTorch 2.15.0+cpu</div>
          </div>
          <div className="p-3 rounded-lg bg-sidebar-panel border border-white/5">
            <span className="text-steel text-[10px] uppercase">Database Mode</span>
            <div className="text-success font-bold mt-1">PostgreSQL Ready</div>
          </div>
          <div className="p-3 rounded-lg bg-sidebar-panel border border-white/5">
            <span className="text-steel text-[10px] uppercase">Visual Identity</span>
            <div className="text-neon-violet font-bold mt-1">Royal Spectrum</div>
          </div>
          <div className="p-3 rounded-lg bg-sidebar-panel border border-white/5">
            <span className="text-steel text-[10px] uppercase">Task Worker</span>
            <div className="text-hot-pink font-bold mt-1">Async Runner Active</div>
          </div>
        </div>
      </div>
    </div>
  );
};

