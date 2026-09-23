import React from 'react';
import { Database, Layers, Users, GitFork, RefreshCw } from 'lucide-react';

export default function MetricCards({ stats, loading, onRefresh }) {
  const cards = [
    {
      title: 'Sources Ingested',
      value: stats ? (stats.total_sources ?? 0).toLocaleString() : '0',
      subtitle: `${stats ? (stats.sources_indexed ?? stats.total_sources ?? 0) : 0} Active Silos`,
      icon: Database,
      color: 'blue',
      gradient: 'from-blue-500/20 to-blue-600/5',
      border: 'border-blue-500/30',
      text: 'text-blue-600 dark:text-blue-400',
      badge: 'Operational Silos',
    },
    {
      title: 'Attributes Indexed',
      value: stats ? (stats.total_attributes ?? 0).toLocaleString() : '0',
      subtitle: `${stats ? (stats.unique_normalized_values ?? 0).toLocaleString() : '0'} unique keys`,
      icon: Layers,
      color: 'emerald',
      gradient: 'from-emerald-500/20 to-emerald-600/5',
      border: 'border-emerald-500/30',
      text: 'text-emerald-600 dark:text-emerald-400',
      badge: 'EAV Inverted Index',
    },
    {
      title: 'Master Entities Discovered',
      value: stats ? (stats.master_entities ?? 0).toLocaleString() : '0',
      subtitle: 'Disjoint Identity Clusters',
      icon: Users,
      color: 'purple',
      gradient: 'from-purple-500/20 to-purple-600/5',
      border: 'border-purple-500/30',
      text: 'text-purple-600 dark:text-purple-400',
      badge: 'Resolved Graphs',
    },
    {
      title: 'Multi-Hop Links Formed',
      value: stats ? (stats.multi_hop_links ?? 0).toLocaleString() : '0',
      subtitle: `${stats && stats.master_entities > 0 ? (stats.multi_hop_links / stats.master_entities).toFixed(1) : '0'} avg hops / entity`,
      icon: GitFork,
      color: 'amber',
      gradient: 'from-amber-500/20 to-amber-600/5',
      border: 'border-amber-500/30',
      text: 'text-amber-600 dark:text-amber-400',
      badge: 'BFS Traversal',
    },
  ];


  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            System Operational Metrics
          </h2>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Live telemetry from high-performance SQLite EAV attribute store
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          title="Refresh metrics"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card, i) => {
          const Icon = card.icon;
          return (
            <div
              key={i}
              className="relative overflow-hidden rounded-2xl p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow"
            >
              <div
                className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${card.gradient} rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none`}
              />
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                    {card.title}
                  </span>
                  <div className="mt-1 text-2xl font-bold font-mono text-slate-900 dark:text-white tracking-tight">
                    {card.value}
                  </div>
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {card.subtitle}
                  </div>
                </div>
                <div className={`p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border ${card.border} ${card.text}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px]">
                <span className="text-slate-400 dark:text-slate-500 font-mono">
                  {card.badge}
                </span>
                <span className="inline-flex items-center text-emerald-600 dark:text-emerald-400 font-medium">
                  Active
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
