import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Users, User, ArrowRight, CheckCircle2, Shield, FolderPlus } from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { workspaceService, projectService } from '../../services/api';

export const OnboardingPage: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [workspaceType, setWorkspaceType] = useState<'personal' | 'team'>('personal');
  const [workspaceName, setWorkspaceName] = useState('Enterprise Knowledge Base');
  const [workspacePurpose, setWorkspacePurpose] = useState('Restoration of legacy documentation screenshots and technical software manuals.');
  const [projectName, setProjectName] = useState('Legacy Windows & Unix Documentation');
  const [loading, setLoading] = useState(false);

  const handleFinishOnboarding = async () => {
    try {
      setLoading(true);
      const ws = await workspaceService.create(workspaceName, workspacePurpose);
      await projectService.create(ws.id, projectName, 'Default starting project');
      navigate('/dashboard');
    } catch (err) {
      console.error("Onboarding setup failed", err);
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-sidebar flex items-center justify-center p-6 selection:bg-neon-violet selection:text-white">
      <div className="w-full max-w-2xl p-8 rounded-card bg-sidebar-panel border border-white/10 shadow-glow-purple space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-brand flex items-center justify-center shadow-glow-purple">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-display font-bold text-white tracking-tight">DocRestore AI Setup</h1>
              <p className="text-xs text-mist font-mono">Workspace & Project Onboarding</p>
            </div>
          </div>
          <div className="text-xs font-mono text-neon-violet">Step {step} of 2</div>
        </div>

        {step === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-base font-semibold text-white">Choose Workspace Mode</h2>
              <p className="text-xs text-mist mt-1">Select how you intend to organize legacy UI restoration projects.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setWorkspaceType('personal')}
                className={`p-5 rounded-xl border text-left transition-all ${
                  workspaceType === 'personal'
                    ? 'border-royal-purple bg-sidebar text-white shadow-glow-purple ring-2 ring-neon-violet/30'
                    : 'border-white/10 bg-sidebar-panel/80 text-mist hover:border-white/30'
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-royal-purple/20 text-neon-violet flex items-center justify-center mb-3">
                  <User className="w-4 h-4" />
                </div>
                <div className="font-bold text-sm text-white">Personal Workspace</div>
                <p className="text-xs text-steel mt-1">For independent developers, technical writers, and researchers.</p>
              </button>

              <button
                type="button"
                onClick={() => setWorkspaceType('team')}
                className={`p-5 rounded-xl border text-left transition-all ${
                  workspaceType === 'team'
                    ? 'border-royal-purple bg-sidebar text-white shadow-glow-purple ring-2 ring-neon-violet/30'
                    : 'border-white/10 bg-sidebar-panel/80 text-mist hover:border-white/30'
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-fuchsia-brand/20 text-hot-pink flex items-center justify-center mb-3">
                  <Users className="w-4 h-4" />
                </div>
                <div className="font-bold text-sm text-white">Team Workspace</div>
                <p className="text-xs text-steel mt-1">Collaborative restoration with role-based access for multi-user teams.</p>
              </button>
            </div>

            <div className="flex justify-end pt-4">
              <NeonButton variant="primary" size="md" onClick={() => setStep(2)} icon={<ArrowRight className="w-4 h-4" />}>
                Continue to Project Setup
              </NeonButton>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5 text-xs">
            <div>
              <h2 className="text-base font-semibold text-white">Workspace & First Project Details</h2>
              <p className="text-xs text-mist mt-0.5">Customize your environment and initial screenshot repository.</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="font-semibold text-white block mb-1">Workspace Name</label>
                <input
                  type="text"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-sans"
                />
              </div>

              <div>
                <label className="font-semibold text-white block mb-1">Workspace Purpose</label>
                <input
                  type="text"
                  value={workspacePurpose}
                  onChange={(e) => setWorkspacePurpose(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-sans"
                />
              </div>

              <div>
                <label className="font-semibold text-white block mb-1">First Restoration Project Name</label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-sans"
                />
              </div>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-white/10">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-steel hover:text-white transition-colors"
              >
                ← Back
              </button>
              <NeonButton
                variant="ai"
                size="md"
                disabled={loading}
                onClick={handleFinishOnboarding}
                icon={<CheckCircle2 className="w-4 h-4" />}
              >
                {loading ? 'Creating Environment...' : 'Complete Setup & Launch Dashboard'}
              </NeonButton>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

