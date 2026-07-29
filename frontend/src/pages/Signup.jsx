import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Building2, User, Mail, Lock, ArrowRight, Loader2, Info } from 'lucide-react';
import '../styles/auth.css';

export default function Signup() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    organization: '',
    role: 'Engineer'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const { signup, login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      // 1. Create account
      await signup(formData);
      // 2. Auto login
      await login(formData.email, formData.password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
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
            Join the Next<br />Generation of<br />Infrastructure AI
          </h1>
          <p className="text-white/70 text-lg max-w-md font-light">
            Set up your organization's workspace and start analyzing building data instantly.
          </p>
          
          <div className="mt-12 space-y-6">
            {[
              "Private enterprise workspaces",
              "Access to global engineering standards",
              "Multi-agent diagnostic pipeline",
              "Automated report generation"
            ].map((feature, i) => (
              <div key={i} className="flex items-center gap-3 text-white/80 font-light">
                <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                  <div className="w-2 h-2 rounded-full bg-white"></div>
                </div>
                {feature}
              </div>
            ))}
          </div>
        </div>
      </div>
      
      <div className="auth-form-container">
        <div className="auth-form-wrapper max-w-[480px]">
          <div className="mb-8">
            <h2 className="text-3xl font-medium text-[var(--color-text-primary)] mb-2">Create Account</h2>
            <p className="text-[var(--color-text-secondary)]">Enter your details to get started</p>
          </div>
          
          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 text-sm flex items-start gap-3 border border-red-100">
              <Info size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="input-group">
                <label htmlFor="full_name">Full Name</label>
                <div className="input-wrapper">
                  <User size={18} className="input-icon" />
                  <input
                    id="full_name"
                    name="full_name"
                    type="text"
                    value={formData.full_name}
                    onChange={handleChange}
                    placeholder="Jane Doe"
                    required
                  />
                </div>
              </div>
              <div className="input-group">
                <label htmlFor="role">Primary Role</label>
                <div className="input-wrapper select-wrapper">
                  <select
                    id="role"
                    name="role"
                    value={formData.role}
                    onChange={handleChange}
                    required
                    className="pl-4"
                  >
                    <option value="Engineer">Civil Engineer</option>
                    <option value="Consultant">Consultant</option>
                    <option value="Facility Manager">Facility Manager</option>
                    <option value="Inspector">Inspector</option>
                    <option value="Administrator">Administrator</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="organization">Organization Name</label>
              <div className="input-wrapper">
                <Building2 size={18} className="input-icon" />
                <input
                  id="organization"
                  name="organization"
                  type="text"
                  value={formData.organization}
                  onChange={handleChange}
                  placeholder="ABC Engineering Inc."
                  required
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="email">Work Email</label>
              <div className="input-wrapper">
                <Mail size={18} className="input-icon" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="engineer@company.com"
                  required
                />
              </div>
            </div>
            
            <div className="input-group">
              <label htmlFor="password">Password</label>
              <div className="input-wrapper">
                <Lock size={18} className="input-icon" />
                <input
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  required
                  minLength={8}
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
                  Creating Account...
                </>
              ) : (
                <>
                  Create Account
                  <ArrowRight size={18} className="ml-2" />
                </>
              )}
            </button>
          </form>
          
          <div className="mt-8 text-center text-sm text-[var(--color-text-secondary)]">
            Already have an account?{' '}
            <Link to="/login" className="text-[var(--color-primary)] font-medium hover:underline">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
