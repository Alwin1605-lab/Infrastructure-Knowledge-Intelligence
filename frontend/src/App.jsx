import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import { ProtectedRoute } from './components/ProtectedRoute';
import { AuthProvider } from './context/AuthContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import { SuspenseLoader } from './components/SuspenseLoader';

import { Outlet } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { TopNav } from './components/layout/TopNav';
import Login from './pages/Login';
import Signup from './pages/Signup';

function AppLayout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-auto bg-slate-50 relative z-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// Core Pages (Lazy Loaded)
const Dashboard = React.lazy(() => import('./pages/Dashboard').then(module => ({ default: module.Dashboard })));
const Workspaces = React.lazy(() => import('./pages/Workspaces').then(module => ({ default: module.Workspaces })));
const WorkspaceDetail = React.lazy(() => import('./pages/WorkspaceDetail').then(module => ({ default: module.WorkspaceDetail })));
const DocumentLibrary = React.lazy(() => import('./pages/DocumentLibrary').then(module => ({ default: module.DocumentLibrary })));
const EngineeringAssistant = React.lazy(() => import('./pages/EngineeringAssistant').then(module => ({ default: module.EngineeringAssistant })));
const Reports = React.lazy(() => import('./pages/Reports').then(module => ({ default: module.Reports })));
const Standards = React.lazy(() => import('./pages/Standards').then(module => ({ default: module.Standards })));
const Settings = React.lazy(() => import('./pages/Settings').then(module => ({ default: module.Settings })));

// Phase 5 Pages
const Analytics = React.lazy(() => import('./pages/Analytics').then(module => ({ default: module.Analytics })));
const GlobalSearch = React.lazy(() => import('./pages/GlobalSearch').then(module => ({ default: module.GlobalSearch })));
const ProcessingQueue = React.lazy(() => import('./pages/ProcessingQueue').then(module => ({ default: module.ProcessingQueue })));
const RetrievalInspector = React.lazy(() => import('./pages/RetrievalInspector').then(module => ({ default: module.RetrievalInspector })));

// Developer / Admin Pages
const EvaluationDashboard = React.lazy(() => import('./pages/EvaluationDashboard').then(module => ({ default: module.EvaluationDashboard })));
const Explainability = React.lazy(() => import('./pages/Explainability').then(module => ({ default: module.Explainability })));
const KnowledgeGraphExplorer = React.lazy(() => import('./pages/KnowledgeGraphExplorer').then(module => ({ default: module.KnowledgeGraphExplorer })));
const SystemMonitoring = React.lazy(() => import('./pages/SystemMonitoring').then(module => ({ default: module.SystemMonitoring })));

// Phase 6 Acquisition Pages
const AcquisitionDashboard = React.lazy(() => import('./pages/AcquisitionDashboard').then(module => ({ default: module.AcquisitionDashboard })));
const ReviewQueue = React.lazy(() => import('./pages/ReviewQueue').then(module => ({ default: module.ReviewQueue })));
const ResearchAssistant = React.lazy(() => import('./pages/ResearchAssistant').then(module => ({ default: module.ResearchAssistant })));
const AdminUpload = React.lazy(() => import('./pages/AdminUpload').then(module => ({ default: module.AdminUpload })));
const BenchmarkDashboard = React.lazy(() => import('./pages/BenchmarkDashboard').then(module => ({ default: module.BenchmarkDashboard })));

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
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Router>
            <Suspense fallback={<SuspenseLoader />}>
              <Routes>
                {/* Public Auth Routes */}
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />

                {/* Protected Enterprise Layout Routes */}
                <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
                  <Route index element={<Dashboard />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/workspaces" element={<Workspaces />} />
                  <Route path="/workspaces/:id" element={<WorkspaceDetail />} />
                  <Route path="/library" element={<DocumentLibrary />} />
                  <Route path="/docs" element={<DocumentLibrary />} />
                  <Route path="/documents" element={<DocumentLibrary />} />
                  <Route path="/assistant" element={<EngineeringAssistant />} />
                  <Route path="/reports" element={<Reports />} />
                  <Route path="/standards" element={<Standards />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/search" element={<GlobalSearch />} />

                  {/* Developer Mode Routes */}
                  <Route path="/dev">
                    <Route index element={<SystemMonitoring />} />
                    <Route path="monitoring" element={<SystemMonitoring />} />
                    <Route path="eval" element={<EvaluationDashboard />} />
                    <Route path="explainability" element={<Explainability />} />
                    <Route path="kg" element={<KnowledgeGraphExplorer />} />
                    <Route path="queue" element={<ProcessingQueue />} />
                    <Route path="retrieval" element={<RetrievalInspector />} />
                    <Route path="benchmark" element={<BenchmarkDashboard />} />
                  </Route>

                  {/* Acquisition Routes */}
                  <Route path="/acquisition">
                    <Route path="dashboard" element={<AcquisitionDashboard />} />
                    <Route path="queue" element={<ReviewQueue />} />
                    <Route path="research" element={<ResearchAssistant />} />
                    <Route path="upload" element={<AdminUpload />} />
                  </Route>
                </Route>
              </Routes>
            </Suspense>
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
    </ErrorBoundary>
  );
}

export default App;
