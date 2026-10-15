import React from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error("Uncaught rendering error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-red-100 max-w-md w-full p-8 text-center space-y-6">
            <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto">
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
            
            <div>
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Something went wrong</h2>
              <p className="text-slate-500 text-sm">
                We encountered an unexpected error while loading this page.
              </p>
            </div>

            {this.state.error && (
              <div className="bg-slate-50 rounded-lg p-4 overflow-auto max-h-32 text-left text-xs font-mono text-slate-700 border border-slate-200">
                {this.state.error.toString()}
              </div>
            )}

            <div className="pt-4 flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-medium transition-colors"
              >
                <RefreshCcw size={16} />
                Reload Page
              </button>
              <button
                onClick={() => window.location.href = '/'}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl font-medium transition-colors"
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
