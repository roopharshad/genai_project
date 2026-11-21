import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, AlertCircle, ArrowRight } from 'lucide-react';
import { NeonButton } from '../../components/common/NeonButton';
import { authService } from '../../services/api';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('demo@docrestore.ai');
  const [password, setPassword] = useState('docrestore123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const res = await authService.login(email, password);
      localStorage.setItem('docrestore_token', res.access_token);
      localStorage.setItem('docrestore_user', JSON.stringify(res.user));
      navigate('/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-sidebar flex items-center justify-center p-6 selection:bg-neon-violet selection:text-white">
      <div className="w-full max-w-md p-8 rounded-card bg-sidebar-panel border border-white/10 shadow-glow-purple space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-brand flex items-center justify-center mx-auto shadow-glow-purple">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-display font-bold text-white tracking-tight">DocRestore AI</h1>
          <p className="text-xs text-mist font-mono">Sign in to your restoration workspace</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-error/15 border border-error/30 text-error text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="font-semibold text-white block mb-1">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-mono"
            />
          </div>
          <div>
            <label className="font-semibold text-white block mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-white/10 bg-sidebar text-white focus:outline-none focus:ring-2 focus:ring-focus font-mono"
            />
          </div>

          <div className="pt-2">
            <NeonButton variant="primary" size="lg" className="w-full" disabled={loading} type="submit" icon={<ArrowRight className="w-4 h-4" />}>
              {loading ? 'Authenticating...' : 'Sign In to Workspace'}
            </NeonButton>
          </div>
        </form>

        <div className="pt-4 border-t border-white/10 text-center text-xs text-steel">
          Don't have an account?{' '}
          <Link to="/register" className="text-neon-violet font-semibold hover:underline">
            Register new workspace
          </Link>
        </div>
      </div>
    </div>
  );
};

