import React, { useState } from 'react';
import {
  X, Clock, Database, Layers, Users, GitFork,
  CheckCircle2, Plus, Edit2, Trash2, Check, ExternalLink,
  Search, AlertTriangle
} from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';

export default function SessionHistoryDrawer() {
  const {
    currentWorkspace,
    workspaces,
    historyDrawerOpen,
    setHistoryDrawerOpen,
    switchWorkspace,
    createNewWorkspace,
    renameWorkspace,
    deleteWorkspace,
    purgeEmptySessions,
  } = useWorkspace();

  const [searchTerm, setSearchTerm] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isPurging, setIsPurging] = useState(false);
  const [purgeFeedback, setPurgeFeedback] = useState(null);

  if (!historyDrawerOpen) return null;

  const filteredWorkspaces = workspaces.filter((ws) =>
    ws.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (ws.description && ws.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const startRename = (ws) => {
    setEditingId(ws.id);
    setEditName(ws.name);
  };

  const saveRename = async (id) => {
    if (editName.trim()) {
      await renameWorkspace(id, editName.trim());
    }
    setEditingId(null);
  };

  const handleCreateNew = async () => {
    setIsCreating(true);
    try {
      await createNewWorkspace();
      setHistoryDrawerOpen(false);
    } finally {
      setIsCreating(false);
    }
  };

  const confirmDelete = async (id) => {
    await deleteWorkspace(id);
    setDeletingId(null);
  };

  const handlePurgeEmpty = async () => {
    setIsPurging(true);
    setPurgeFeedback(null);
    try {
      const res = await purgeEmptySessions();
      const count = res?.purged_count ?? 0;
      setPurgeFeedback({
        type: 'success',
        text: count > 0 ? `Successfully cleared ${count} empty session(s).` : 'No empty sessions found in database.'
      });
      setTimeout(() => setPurgeFeedback(null), 3500);
    } catch (err) {
      console.error('Failed to clear empty sessions:', err);
      setPurgeFeedback({
        type: 'error',
        text: 'Failed to clear empty sessions.'
      });
      setTimeout(() => setPurgeFeedback(null), 3500);
    } finally {
      setIsPurging(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/60 backdrop-blur-sm animate-fadeIn">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/50">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center border border-indigo-200 dark:border-indigo-800">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-slate-900 dark:text-white text-base">
                    Session History
                  </h3>
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
                    {workspaces.length}
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Switch or manage persistent ingestion sessions
                </p>
              </div>
            </div>
            <button
              onClick={() => setHistoryDrawerOpen(false)}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Close session history"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Action Toolbar */}
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 space-y-2.5 bg-white dark:bg-slate-900">
            <div className="flex items-center gap-2">
              <button
                onClick={handleCreateNew}
                disabled={isCreating}
                className="flex-1 py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs flex items-center justify-center gap-1.5 shadow-sm shadow-indigo-600/20 transition-all disabled:opacity-50"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>+ New Session</span>
              </button>
              <button
                onClick={handlePurgeEmpty}
                disabled={isPurging}
                className="py-2 px-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 hover:bg-red-50 dark:hover:bg-red-950/40 text-slate-700 dark:text-slate-300 hover:text-red-600 dark:hover:text-red-400 font-medium text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
                title="Purge all unused/empty sessions with 0 sources from SQLite"
              >
                <Trash2 className={`w-3.5 h-3.5 ${isPurging ? 'animate-spin' : ''}`} />
                <span>{isPurging ? 'Clearing...' : 'Clear Empty Sessions'}</span>
              </button>
            </div>

            {/* Purge Notification */}
            {purgeFeedback && (
              <div
                className={`p-2 rounded-lg text-xs flex items-center justify-between transition-all ${
                  purgeFeedback.type === 'success'
                    ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                    : 'bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
                }`}
              >
                <span>{purgeFeedback.text}</span>
                <button
                  onClick={() => setPurgeFeedback(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}

            {/* Search filter */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter saved sessions..."
                className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white placeholder-slate-400 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {/* Active Draft Session Banner */}
            {currentWorkspace?.isDraft && (
              <div className="p-3 rounded-2xl border border-amber-300/70 dark:border-amber-700/60 bg-amber-50/70 dark:bg-amber-950/30 text-xs mb-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5 font-bold text-amber-900 dark:text-amber-200">
                    <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                    Active Draft Session
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-300">
                    In Memory
                  </span>
                </div>
                <p className="text-[11px] text-amber-700 dark:text-amber-400">
                  "{currentWorkspace.name}" will be automatically saved to database when you upload your first file.
                </p>
              </div>
            )}
            {filteredWorkspaces.length === 0 ? (
              <div className="text-center py-12 px-4">
                <Clock className="w-10 h-10 mx-auto text-slate-300 dark:text-slate-700 mb-3" />
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  No Sessions Found
                </h4>
                <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
                  {searchTerm
                    ? `No sessions matching "${searchTerm}"`
                    : 'Start a new session to begin uploading operational datasets.'}
                </p>
              </div>
            ) : (
              filteredWorkspaces.map((ws) => {
                const isActive = currentWorkspace?.id === ws.id;
                const isEditing = editingId === ws.id;
                const isDeleting = deletingId === ws.id;

                return (
                  <div
                    key={ws.id}
                    className={`rounded-2xl p-4 border transition-all ${
                      isActive
                        ? 'border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/20 shadow-sm'
                        : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                    }`}
                  >
                    {/* Header Row: Title & Active Badge */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex-1 min-w-0">
                        {isEditing ? (
                          <div className="flex items-center gap-1.5">
                            <input
                              type="text"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') saveRename(ws.id);
                                if (e.key === 'Escape') setEditingId(null);
                              }}
                              autoFocus
                              className="w-full px-2 py-1 rounded border border-indigo-400 bg-white dark:bg-slate-950 text-xs font-bold text-slate-900 dark:text-white focus:outline-none"
                            />
                            <button
                              onClick={() => saveRename(ws.id)}
                              className="p-1 rounded bg-indigo-600 text-white hover:bg-indigo-700"
                              title="Save name"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="p-1 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-300"
                              title="Cancel"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <h4
                              className="font-bold text-xs text-slate-900 dark:text-white truncate cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-400"
                              onClick={() => switchWorkspace(ws.id)}
                              title={ws.name}
                            >
                              {ws.name}
                            </h4>
                            <button
                              onClick={() => startRename(ws)}
                              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                              title="Rename session"
                            >
                              <Edit2 className="w-3 h-3" />
                            </button>
                          </div>
                        )}
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {ws.created_at
                            ? new Date(ws.created_at).toLocaleString(undefined, {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : 'Baseline'}
                        </div>
                      </div>

                      {isActive && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 flex-shrink-0">
                          <CheckCircle2 className="w-3 h-3" />
                          Active
                        </span>
                      )}
                    </div>

                    {/* Metadata Grid */}
                    <div className="grid grid-cols-2 gap-2 my-3 p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-100 dark:border-slate-800/60 text-[11px]">
                      <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                        <Database className="w-3.5 h-3.5 text-blue-500" />
                        <span>
                          <strong className="font-mono text-slate-900 dark:text-white font-semibold">
                            {ws.total_sources || 0}
                          </strong>{' '}
                          {ws.total_sources === 1 ? 'Source' : 'Sources'}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                        <Layers className="w-3.5 h-3.5 text-emerald-500" />
                        <span>
                          <strong className="font-mono text-slate-900 dark:text-white font-semibold">
                            {ws.total_records?.toLocaleString() || 0}
                          </strong>{' '}
                          Records
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                        <Users className="w-3.5 h-3.5 text-purple-500" />
                        <span>
                          <strong className="font-mono text-slate-900 dark:text-white font-semibold">
                            {ws.master_entities?.toLocaleString() || 0}
                          </strong>{' '}
                          Entities
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                        <GitFork className="w-3.5 h-3.5 text-amber-500" />
                        <span>
                          <strong className="font-mono text-slate-900 dark:text-white font-semibold">
                            {ws.links_discovered?.toLocaleString() || 0}
                          </strong>{' '}
                          Hops
                        </span>
                      </div>
                    </div>

                    {/* Action Bar */}
                    {isDeleting ? (
                      <div className="p-2.5 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-xs">
                        <div className="flex items-center gap-1.5 text-red-700 dark:text-red-300 font-semibold mb-2">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Delete this session?
                        </div>
                        <p className="text-[11px] text-red-600 dark:text-red-400 mb-2">
                          Permanently removes all uploaded files, EAV indexes, and entities in this workspace.
                        </p>
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setDeletingId(null)}
                            className="px-2.5 py-1 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 text-[11px]"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => confirmDelete(ws.id)}
                            className="px-2.5 py-1 rounded bg-red-600 hover:bg-red-700 text-white font-medium text-[11px]"
                          >
                            Yes, Delete
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800/80">
                        {isActive ? (
                          <span className="text-[11px] text-indigo-600 dark:text-indigo-400 font-medium">
                            Currently Loaded
                          </span>
                        ) : (
                          <button
                            onClick={() => switchWorkspace(ws.id)}
                            className="px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-300 font-medium text-xs transition-colors flex items-center gap-1"
                          >
                            <ExternalLink className="w-3 h-3" />
                            Load Session
                          </button>
                        )}

                        <button
                          onClick={() => setDeletingId(ws.id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                          title="Delete session"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
