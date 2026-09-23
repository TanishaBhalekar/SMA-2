import React, { useState } from 'react';
import { Search, Loader2, Sparkles, AlertCircle, RefreshCw, CheckCircle, Database, FolderKanban, ArrowRight } from 'lucide-react';
import { api } from '../api/client';
import { useWorkspace } from '../context/WorkspaceContext';
import HopVisualizer from './HopVisualizer';
import MasterEntityCard from './MasterEntityCard';
import GeminiAccordion from './GeminiAccordion';

export default function DiscoveryExplorer({ onNavigateToSources }) {
  const { currentWorkspace } = useWorkspace();

  const [identifierType, setIdentifierType] = useState('email');
  const [identifierValue, setIdentifierValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [discoveryResult, setDiscoveryResult] = useState(null);
  const [executedSeed, setExecutedSeed] = useState({ field: 'email', value: '' });

  const triggerSearch = async (fieldType = identifierType, val = identifierValue) => {
    if (!val.trim()) return;
    setLoading(true);
    setError(null);
    setExecutedSeed({ field: fieldType, value: val.trim() });

    try {
      const res = await api.searchEntity(fieldType, val.trim(), currentWorkspace?.id);
      setDiscoveryResult(res.data);
    } catch (err) {
      console.error('Search failed:', err);
      const detail = err.response?.data?.detail || err.message || 'Failed to resolve entity graph.';
      setError(detail);
      setDiscoveryResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    triggerSearch();
  };

  return (
    <div>
      {/* Search Control Bar */}
      <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <Search className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              Progressive Discovery Explorer
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Enter any single anchor identifier to trigger automated cross-silo graph traversal
            </p>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700/60 self-start sm:self-auto">
            <FolderKanban className="w-3.5 h-3.5 text-indigo-500" />
            <span className="text-[11px] text-slate-400">Scope:</span>
            <span className="font-semibold text-slate-900 dark:text-white truncate max-w-[160px]">
              {currentWorkspace?.name || 'Active Session'}
            </span>
          </div>
        </div>


        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row items-stretch gap-3">
          {/* Identifier Type Selector */}
          <div className="sm:w-48 flex-shrink-0">
            <label htmlFor="seed-type-select" className="sr-only">Seed Identifier Type</label>
            <select
              id="seed-type-select"
              value={identifierType}
              onChange={(e) => setIdentifierType(e.target.value)}
              className="w-full h-11 px-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="email">Email Address</option>
              <option value="phone">Phone / Mobile</option>
              <option value="username">Platform Username</option>
              <option value="member_id">Member / Loyalty ID</option>
              <option value="name">Full Name</option>
            </select>
          </div>

          {/* Identifier Value Input */}
          <div className="relative flex-1">
            <input
              type="text"
              value={identifierValue}
              onChange={(e) => setIdentifierValue(e.target.value)}
              placeholder="e.g. john@example.com or 9876543210..."
              className="w-full h-11 pl-4 pr-10 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-white placeholder-slate-400 text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
            {identifierValue && (
              <button
                type="button"
                onClick={() => setIdentifierValue('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs"
              >
                ✕
              </button>
            )}
          </div>

          {/* Action Button */}
          <button
            type="submit"
            disabled={loading || !identifierValue.trim()}
            className="h-11 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Traversing Graph...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Discover Entity</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-300 text-sm flex items-start gap-3 mb-8">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-500" />
          <div>
            <div className="font-semibold">Entity Resolution Unsuccessful</div>
            <div className="text-xs mt-0.5">{error}</div>
            <div className="text-xs mt-2 text-slate-600 dark:text-slate-400">
              💡 Tip: Verify the identifier type and value entered, or ensure the records have been indexed.
            </div>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !discoveryResult && (
        <div className="rounded-2xl p-12 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center mb-8">
          <div className="inline-flex p-4 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 mb-4 animate-pulse">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
            Traversing EAV Attribute Store...
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            Executing iterative BFS expansion from `{executedSeed.field}: {executedSeed.value}` across HR, CRM, Platform, and Membership databases.
          </p>
        </div>
      )}

      {/* Results View */}
      {discoveryResult && (
        <div className="space-y-8 animate-fadeIn">
          {/* Hop-by-Hop Visualizer */}
          <HopVisualizer
            hops={discoveryResult.hops || []}
            lineage={discoveryResult.lineage || []}
            seed={executedSeed}
          />

          {/* Consolidated Master Entity Card */}
          <MasterEntityCard
            entity={discoveryResult.entity}
            hops={discoveryResult.hops || []}
            lineage={discoveryResult.lineage || []}
          />

          {/* AI Match Rationale Accordion */}
          <GeminiAccordion
            explanation={discoveryResult.gemini_explanation}
          />
        </div>
      )}

      {/* Clean Slate Landing Placeholder */}
      {!discoveryResult && !loading && !error && (
        <div className="rounded-2xl p-10 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center shadow-sm">
          <div className="w-12 h-12 mx-auto mb-4 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-base text-slate-900 dark:text-white mb-2">
            Ready for Progressive Graph Traversal
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mb-6">
            Querying is scoped to session <strong className="text-slate-800 dark:text-slate-200 font-semibold">{currentWorkspace?.name}</strong>.
            The progressive BFS engine traverses email, phone numbers, usernames, and member IDs across all uploaded silos in this session.
          </p>

          <div className="inline-flex flex-col sm:flex-row items-center gap-2 p-1.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs">
            <span className="text-slate-400 px-2 font-medium">Quick suggestions:</span>
            <button
              onClick={() => {
                setIdentifierType('email');
                setIdentifierValue('john@example.com');
                triggerSearch('email', 'john@example.com');
              }}
              className="px-3 py-1 rounded-lg bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 font-mono text-[11px] shadow-sm border border-slate-200 dark:border-slate-700 transition-colors"
            >
              john@example.com
            </button>
            <button
              onClick={() => {
                setIdentifierType('phone');
                setIdentifierValue('9876543210');
                triggerSearch('phone', '9876543210');
              }}
              className="px-3 py-1 rounded-lg bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 font-mono text-[11px] shadow-sm border border-slate-200 dark:border-slate-700 transition-colors"
            >
              9876543210
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

