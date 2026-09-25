import React, { useState } from 'react';
import {
  Sun, Moon, Database, Search, BarChart3, Activity, ShieldCheck,
  Sparkles, Clock, Plus, Edit2, Check, X, FolderKanban
} from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';

export default function Header({ activeTab, setActiveTab, darkMode, setDarkMode, backendOnline = true }) {
  const {
    currentWorkspace,
    workspaces,
    createNewWorkspace,
    renameWorkspace,
    setHistoryDrawerOpen
  } = useWorkspace();

  const [isEditingName, setIsEditingName] = useState(false);
  const [sessionNameInput, setSessionNameInput] = useState('');

  const handleStartRename = () => {
    setSessionNameInput(currentWorkspace?.name || '');
    setIsEditingName(true);
  };

  const handleSaveRename = async () => {
    if (sessionNameInput.trim()) {
      await renameWorkspace(currentWorkspace?.id, sessionNameInput.trim());
    }
    setIsEditingName(false);
  };

  return (
    <header className="sticky top-0 z-40 backdrop-blur-md bg-white/80 dark:bg-slate-950/80 border-b border-slate-200 dark:border-slate-800 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Brand & Live Status */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 flex-shrink-0">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <div className="hidden sm:block">
              <div className="flex items-center gap-2">
                <span className="font-bold text-base lg:text-lg text-slate-900 dark:text-white tracking-tight">
                  Unified Entity Resolution
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-full font-mono bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                  PRJ-07
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  {backendOnline ? 'Engine Active' : 'Connecting Engine...'}
                </span>
                <span className="text-slate-400 dark:text-slate-600">•</span>
                <span className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                  Graph BFS Core v2.4
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
            <button
              onClick={() => setActiveTab('search')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'search'
                  ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              Discovery Explorer
            </button>
            <button
              onClick={() => setActiveTab('sources')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'sources'
                  ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              Source & Ingestion
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'analytics'
                  ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Silo Analytics
            </button>
          </nav>

          {/* Right Action Bar: Session Controls & Theme */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Active Session Badge / Rename */}
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-xs">
              <FolderKanban className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0" />
              {isEditingName ? (
                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    value={sessionNameInput}
                    onChange={(e) => setSessionNameInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveRename();
                      if (e.key === 'Escape') setIsEditingName(false);
                    }}
                    autoFocus
                    className="w-36 px-1.5 py-0.5 rounded border border-indigo-400 bg-white dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium"
                  />
                  <button onClick={handleSaveRename} className="text-emerald-500 hover:text-emerald-600 p-0.5" title="Save name">
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => setIsEditingName(false)} className="text-slate-400 hover:text-slate-600 p-0.5" title="Cancel">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 max-w-[200px]">
                  <span className="truncate font-semibold text-slate-800 dark:text-slate-200" title={currentWorkspace?.name || 'Active Session'}>
                    {currentWorkspace?.name || 'Active Session'}
                  </span>
                  {currentWorkspace?.isDraft && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 flex-shrink-0">
                      Draft
                    </span>
                  )}
                  <button
                    onClick={handleStartRename}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors p-0.5 flex-shrink-0"
                    title="Rename current session"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>

            {/* + New Session Button */}
            <button
              onClick={() => {
                createNewWorkspace();
                setActiveTab('sources');
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs shadow-sm shadow-indigo-600/20 transition-all"
              title="Create a new clean ingestion session canvas"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">+ New Session</span>
            </button>

            {/* History Drawer Button */}
            <button
              onClick={() => setHistoryDrawerOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-xs font-medium"
              title="Open Session History"
            >
              <Clock className="w-3.5 h-3.5 text-indigo-500" />
              <span className="hidden sm:inline">History</span>
              <span className="px-1.5 py-0.2 rounded-full font-mono text-[10px] bg-slate-200 dark:bg-slate-800 font-bold">
                {workspaces.length}
              </span>
            </button>

            {/* Theme Toggle */}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label="Toggle theme"
            >
              {darkMode ? (
                <Sun className="w-4 h-4 text-amber-400 transition-transform hover:rotate-45" />
              ) : (
                <Moon className="w-4 h-4 text-slate-600 transition-transform hover:-rotate-12" />
              )}
            </button>
          </div>
        </div>


        {/* Mobile Navigation bar */}
        <div className="flex md:hidden items-center justify-around py-2 border-t border-slate-200 dark:border-slate-800">
          <button
            onClick={() => setActiveTab('search')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${
              activeTab === 'search'
                ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-semibold'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            Explorer
          </button>
          <button
            onClick={() => setActiveTab('sources')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${
              activeTab === 'sources'
                ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-semibold'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            Sources
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${
              activeTab === 'analytics'
                ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-semibold'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            Analytics
          </button>
        </div>
      </div>
    </header>
  );
}
