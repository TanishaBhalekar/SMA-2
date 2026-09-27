import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import MetricCards from './components/MetricCards';
import DiscoveryExplorer from './components/DiscoveryExplorer';
import SourceManager from './components/SourceManager';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import SessionHistoryDrawer from './components/SessionHistoryDrawer';
import { WorkspaceProvider, useWorkspace } from './context/WorkspaceContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import { api, detectActiveBackend } from './api/client';

function AppContent({ darkMode, setDarkMode }) {
  const { currentWorkspace } = useWorkspace();

  const [activeTab, setActiveTab] = useState('search');
  const [backendOnline, setBackendOnline] = useState(true);
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);

  // Check backend connectivity and fetch stats for the current workspace
  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      await detectActiveBackend();
      setBackendOnline(true);
      if (currentWorkspace?.isDraft || !currentWorkspace?.id) {
        setStats({
          total_sources: 0,
          sources_indexed: 0,
          total_attributes: 0,
          unique_normalized_values: 0,
          master_entities: 0,
          multi_hop_links: 0,
        });
        return;
      }
      const res = await api.getStats(currentWorkspace.id);
      if (res.data) {
        setStats({
          total_sources: res.data.total_sources ?? 0,
          sources_indexed: res.data.total_sources ?? 0,
          total_attributes: res.data.total_attributes_indexed ?? res.data.total_attributes ?? 0,
          unique_normalized_values: res.data.indexed_records ?? 0,
          master_entities: res.data.master_entities ?? 0,
          multi_hop_links: res.data.links_discovered ?? 0,
        });
      }
    } catch (err) {
      console.warn('Backend probe warning:', err);
      setBackendOnline(false);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [currentWorkspace?.id, currentWorkspace?.isDraft]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Global Header with Workspace Controls and Sign Out */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        backendOnline={backendOnline}
      />

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* KPI Metric Bar (Scoped to Active Session) */}
        <MetricCards
          stats={stats}
          loading={loadingStats}
          onRefresh={fetchStats}
        />

        {/* View Switcher */}
        {activeTab === 'search' && (
          <DiscoveryExplorer onNavigateToSources={() => setActiveTab('sources')} />
        )}
        {activeTab === 'sources' && (
          <SourceManager onSourcesChanged={fetchStats} />
        )}
        {activeTab === 'analytics' && (
          <AnalyticsDashboard stats={stats} darkMode={darkMode} />
        )}
      </main>

      {/* Session History Sliding Drawer */}
      <SessionHistoryDrawer />

      {/* Footer */}
      <footer className="mt-16 border-t border-slate-200 dark:border-slate-800/80 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              PRJ-07: Unified Progressive Entity Resolution Engine
            </span>
            <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800">
              v2.5-MultiTenant
            </span>
          </div>
          <div>
            Built with React 18, Tailwind CSS, Lucide Icons & Recharts • Supabase Auth Protected
          </div>
        </div>
      </footer>
    </div>
  );
}

function AppRoot() {
  const { user, loading } = useAuth();

  // Theme state persisted in localStorage
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return true; // Default to dark mode
  });

  // Sync theme changes with DOM and localStorage
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  // Loading state while verifying Supabase session
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
            Verifying Supabase authentication...
          </span>
        </div>
      </div>
    );
  }

  // If no user is logged in, show Login page
  if (!user) {
    return <Login darkMode={darkMode} setDarkMode={setDarkMode} />;
  }

  // If authenticated, provide workspace context and render main dashboard
  return (
    <WorkspaceProvider>
      <AppContent darkMode={darkMode} setDarkMode={setDarkMode} />
    </WorkspaceProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoot />
    </AuthProvider>
  );
}
