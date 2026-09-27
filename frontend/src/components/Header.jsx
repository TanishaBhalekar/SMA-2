import React, { useState } from 'react';
import {
  Sun, Moon, Database, Search, BarChart3,
  Sparkles, Clock, Plus, Edit2, Check, X, FolderKanban, LogOut
} from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';
import { useAuth } from '../context/AuthContext';
import { formatSessionTitle } from '../utils/dateUtils';

export default function Header({ activeTab, setActiveTab, darkMode, setDarkMode, backendOnline = true }) {
  const { user, signOut } = useAuth();
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
    setSessionNameInput(formatSessionTitle(currentWorkspace) || currentWorkspace?.name || '');
    setIsEditingName(true);
  };

  const handleSaveRename = async () => {
    if (sessionNameInput.trim()) {
      await renameWorkspace(currentWorkspace?.id, sessionNameInput.trim());
    }
    setIsEditingName(false);
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 backdrop-blur px-6 py-3 flex items-center justify-between min-h-[68px]">
      {/* 2. Logo & Project Title Block */}
      <div className="flex items-center gap-3">
        {/* Gradient Icon */}
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 shrink-0">
          <Sparkles className="w-5 h-5 text-white" />
        </div>

        {/* Title + Badges */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-slate-900 dark:text-white tracking-tight whitespace-nowrap">
              Unified Entity Resolution
            </span>
            <span className="px-2 py-0.5 text-[11px] font-semibold tracking-wider text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/60 border border-purple-200 dark:border-purple-700/40 rounded-full shrink-0">
              PRJ-07
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Engine Active
            </span>
            <span className="text-slate-300 dark:text-slate-600">•</span>
            <span className="text-slate-500 dark:text-slate-400 text-[11px]">Graph BFS Core v2.4</span>
          </div>
        </div>
      </div>

      {/* 3. Navigation / Right Controls */}
      <div className="flex items-center gap-3">
        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900/90 rounded-xl border border-slate-200/80 dark:border-slate-800">
          <button
            onClick={() => setActiveTab('search')}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'search'
                ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm border border-slate-200/60 dark:border-transparent'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
            title="Discovery Explorer"
          >
            <Search className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Explorer</span>
          </button>
          <button
            onClick={() => setActiveTab('sources')}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'sources'
                ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm border border-slate-200/60 dark:border-transparent'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
            title="Source & Ingestion"
          >
            <Database className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sources</span>
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'analytics'
                ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm border border-slate-200/60 dark:border-transparent'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
            title="Silo Analytics"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Analytics</span>
          </button>
        </nav>

        {/* Active Session Pill (with Rename) */}
        <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs shadow-sm">
          <FolderKanban className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400 flex-shrink-0" />
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
                className="w-36 px-1.5 py-0.5 rounded border border-indigo-400 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium"
              />
              <button onClick={handleSaveRename} className="text-emerald-600 dark:text-emerald-400 hover:text-emerald-500 p-0.5" title="Save name">
                <Check className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setIsEditingName(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5" title="Cancel">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 max-w-[200px]">
              <span className="truncate font-semibold text-slate-800 dark:text-slate-200" title={formatSessionTitle(currentWorkspace) || 'Active Session'}>
                {formatSessionTitle(currentWorkspace) || 'Active Session'}
              </span>
              {currentWorkspace?.isDraft && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 flex-shrink-0">
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
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-sm shadow-indigo-600/20 active:scale-[0.98] transition-all shrink-0"
          title="Create a new clean ingestion session canvas"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">New Session</span>
        </button>

        {/* History Drawer Button */}
        <button
          onClick={() => setHistoryDrawerOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-xs font-semibold shrink-0 shadow-sm"
          title="Open Session History"
        >
          <Clock className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
          <span className="hidden sm:inline">History</span>
          <span className="px-1.5 py-0.5 rounded-full font-mono text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold border border-slate-200 dark:border-slate-700">
            {workspaces.length}
          </span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 shrink-0"
          title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label="Toggle theme"
        >
          {darkMode ? (
            <Sun className="w-4 h-4 text-amber-400 transition-transform hover:rotate-45" />
          ) : (
            <Moon className="w-4 h-4 text-slate-600 transition-transform hover:-rotate-12" />
          )}
        </button>

        {/* User Identity Pill & Sign Out Button */}
        <div className="flex items-center gap-1.5 pl-1 border-l border-slate-200 dark:border-slate-800">
          {user?.email && (
            <span
              className="hidden xl:inline text-[11px] font-mono font-medium text-slate-500 dark:text-slate-400 max-w-[130px] truncate"
              title={user.email}
            >
              {user.email}
            </span>
          )}
          <button
            onClick={signOut}
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-900/50 hover:text-rose-700 dark:hover:text-rose-300 transition-all text-xs font-semibold shrink-0 shadow-sm"
            title={`Signed in as ${user?.email || 'authenticated user'}. Click to Sign Out.`}
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </div>
    </header>
  );
}
