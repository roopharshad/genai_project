import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, AlertCircle, ArrowRight, CheckCircle2, Lock } from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { authService } from '../../services/api';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [workspaceName, setWorkspaceName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match. Please re-enter.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await authService.register(email, password, fullName, workspaceName || 'Personal Workspace');
      localStorage.setItem('docrestore_token', res.access_token);
      localStorage.setItem('docrestore_user', JSON.stringify(res.user));
      // Transition to Step 3: User Onboarding
      navigate('/onboarding');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed. This email may already be registered.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-sidebar flex items-center justify-center p-6 selection:bg-neon-violet selection:text-white">
      <div className="w-full max-w-md p-8 rounded-card bg-sidebar-panel border border-white/10 shadow-glow-purple space-y-6">
        <div className="text-center space-y-2">
          <Link to="/" className="inline-block">
            <div className="w-12 h-12 rounded-2xl bg-gradient-brand flex items-center justify-center mx-auto shadow-glow-purple hover:scale-105 transition-transform">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
          </Link>
          <h1 className="text-2xl font-display font-bold text-white tracking-tight">Create Account</h1>
          <p className="text-xs text-mist font-mono">STEP 2: USER REGISTRATION & WORKSPACE SETUP</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-error/15 border border-error/30 text-error text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="font-semibold text-white block mb-1">Full Name</label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Dr. Alex Vance"
              className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-sans"
            />
          </div>

          <div>
            <label className="font-semibold text-white block mb-1">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@organization.com"
              className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-mono"
            />
          </div>

          <div>
            <label className="font-semibold text-white block mb-1">Password</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 6 characters"
              className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-mono"
            />
          </div>

          <div>
            <label className="font-semibold text-white block mb-1">Confirm Password</label>
            <input
              type="password"
              required
              minLength={6}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your password"
              className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-mono"
            />
          </div>

          <div>
            <label className="font-semibold text-white block mb-1">Workspace Name (Optional)</label>
            <input
              type="text"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              placeholder="e.g. Legacy Enterprise Knowledge Base"
              className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-sans"
            />
          </div>

          <div className="pt-2">
            <NeonButton variant="ai" size="lg" className="w-full" disabled={loading} type="submit" icon={<ArrowRight className="w-4 h-4" />}>
              {loading ? 'Creating Account & Workspace...' : 'Register & Continue to Setup'}
            </NeonButton>
          </div>
        </form>

        <div className="pt-4 border-t border-white/10 text-center text-xs text-steel flex flex-col gap-2">
          <div>
            Already have an account?{' '}
            <Link to="/login" className="text-neon-violet font-semibold hover:underline">
              Sign In to Existing Account
            </Link>
          </div>
          <Link to="/" className="text-[11px] text-steel hover:text-white transition-colors">
            ← Return to Landing Page
          </Link>
        </div>
      </div>
    </div>
  );
};
