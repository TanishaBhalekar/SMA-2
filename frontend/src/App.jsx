import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import MetricCards from './components/MetricCards';
import DiscoveryExplorer from './components/DiscoveryExplorer';
import SourceManager from './components/SourceManager';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { api, detectActiveBackend } from './api/client';

export default function App() {
  // Theme state persisted in localStorage
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return true; // Default to dark mode for sleek modern dev aesthetics
  });

  const [activeTab, setActiveTab] = useState('search');
  const [backendOnline, setBackendOnline] = useState(true);
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);

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

  // Check backend connectivity and fetch stats
  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      await detectActiveBackend();
      const res = await api.getStats();
      if (res.data) {
        setStats({
          total_sources: res.data.total_sources ?? 4,
          sources_indexed: res.data.total_sources ?? 4,
          total_attributes: res.data.total_attributes_indexed ?? res.data.total_attributes ?? 20400,
          unique_normalized_values: res.data.indexed_records ?? 11400,
          master_entities: res.data.master_entities ?? 1200,
          multi_hop_links: res.data.links_discovered ?? 4800,
        });
        setBackendOnline(true);
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
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Global Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        backendOnline={backendOnline}
      />

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* KPI Metric Bar */}
        <MetricCards
          stats={stats}
          loading={loadingStats}
          onRefresh={fetchStats}
        />

        {/* View Switcher */}
        {activeTab === 'search' && <DiscoveryExplorer />}
        {activeTab === 'sources' && <SourceManager onSourcesChanged={fetchStats} />}
        {activeTab === 'analytics' && <AnalyticsDashboard stats={stats} darkMode={darkMode} />}
      </main>

      {/* Footer */}
      <footer className="mt-16 border-t border-slate-200 dark:border-slate-800/80 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              PRJ-07: Unified Progressive Entity Resolution Engine
            </span>
            <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800">
              v2.4-EAV
            </span>
          </div>
          <div>
            Built with React 18, Tailwind CSS, Lucide Icons & Recharts • Google Gemini Integrated
          </div>
        </div>
      </footer>
    </div>
  );
}
