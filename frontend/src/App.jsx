import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import { ProtectedRoute } from './components/ProtectedRoute';
import { AuthProvider } from './context/AuthContext';

// Auth Pages
import Login from './pages/Login';
import Signup from './pages/Signup';

// Core Pages
import { Dashboard } from './pages/Dashboard';
import { Workspaces } from './pages/Workspaces';
import { WorkspaceDetail } from './pages/WorkspaceDetail';
import { DocumentLibrary } from './pages/DocumentLibrary';
import { EngineeringAssistant } from './pages/EngineeringAssistant';
import { Reports } from './pages/Reports';
import { Standards } from './pages/Standards';
import { Settings } from './pages/Settings';

// Developer / Admin Pages (Hidden from main navigation)
import { EvaluationDashboard } from './pages/EvaluationDashboard';
import { Explainability } from './pages/Explainability';
import { KnowledgeGraphExplorer } from './pages/KnowledgeGraphExplorer';
import { SystemMonitoring } from './pages/SystemMonitoring';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* Protected Routes Wrapper */}
            <Route element={<ProtectedRoute />}>
              {/* Primary Workflow Routes */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/workspaces" element={<Workspaces />} />
              <Route path="/workspaces/:id" element={<WorkspaceDetail />} />
              <Route path="/docs" element={<DocumentLibrary />} />
              <Route path="/assistant" element={<EngineeringAssistant />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/standards" element={<Standards />} />
              <Route path="/settings" element={<Settings />} />

              {/* Developer Mode Routes */}
              <Route path="/dev">
                <Route index element={<Navigate to="monitoring" replace />} />
                <Route path="eval" element={<EvaluationDashboard />} />
                <Route path="explainability" element={<Explainability />} />
                <Route path="kg" element={<KnowledgeGraphExplorer />} />
                <Route path="monitoring" element={<SystemMonitoring />} />
              </Route>
            </Route>
          </Routes>
          <Toaster position="bottom-right" toastOptions={{
          style: {
            background: '#1E293B',
            color: '#F8FAFC',
            borderRadius: '12px',
            fontSize: '14px',
            fontWeight: 500,
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
          }
        }} />
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
