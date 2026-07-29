import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Building2, Mail, Lock, ArrowRight, Loader2, Info } from 'lucide-react';
import '../styles/auth.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-layout">
      <div className="auth-visual">
        <div className="auth-visual-content">
          <div className="brand-logo mb-6">
            <Building2 size={48} className="text-white opacity-90" />
          </div>
          <h1 className="display-font text-5xl font-light text-white mb-4 leading-tight">
            Building Knowledge<br />Intelligence
          </h1>
          <p className="text-white/70 text-lg max-w-md font-light">
            Enterprise AI platform for civil engineers, structural consultants, and facility managers.
          </p>
          
          <div className="auth-stats mt-16 flex gap-12">
            <div>
              <div className="text-3xl font-light text-white mb-1">10k+</div>
              <div className="text-white/50 text-sm tracking-wider uppercase">Entities Indexed</div>
            </div>
            <div>
              <div className="text-3xl font-light text-white mb-1">98%</div>
              <div className="text-white/50 text-sm tracking-wider uppercase">Retrieval Accuracy</div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="auth-form-container">
        <div className="auth-form-wrapper">
          <div className="mb-8">
            <h2 className="text-3xl font-medium text-[var(--color-text-primary)] mb-2">Welcome back</h2>
            <p className="text-[var(--color-text-secondary)]">Sign in to your enterprise workspace</p>
          </div>
          
          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 text-sm flex items-start gap-3 border border-red-100">
              <Info size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="input-group">
              <label htmlFor="email">Work Email</label>
              <div className="input-wrapper">
                <Mail size={18} className="input-icon" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="engineer@company.com"
                  required
                  autoComplete="email"
                />
              </div>
            </div>
            
            <div className="input-group">
              <div className="flex justify-between items-center">
                <label htmlFor="password">Password</label>
                <a href="#" className="text-sm text-[var(--color-primary)] hover:underline">Forgot password?</a>
              </div>
              <div className="input-wrapper">
                <Lock size={18} className="input-icon" />
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                />
              </div>
            </div>
            
            <button 
              type="submit" 
              className="btn btn-primary w-full justify-center h-12 mt-6 text-base"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin mr-2" />
                  Authenticating...
                </>
              ) : (
                <>
                  Sign in to Workspace
                  <ArrowRight size={18} className="ml-2" />
                </>
              )}
            </button>
          </form>
          
          <div className="mt-8 text-center text-sm text-[var(--color-text-secondary)]">
            Don't have an enterprise account?{' '}
            <Link to="/signup" className="text-[var(--color-primary)] font-medium hover:underline">
              Request access
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
