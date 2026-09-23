import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud, FileText, CheckCircle2, AlertCircle, Database,
  ArrowRight, Sparkles, RefreshCw, X, Eye, Play, Layers, Shield,
  Trash2, Settings2, FolderKanban, ChevronDown, ChevronUp, Plus
} from 'lucide-react';
import { api } from '../api/client';
import SourceBadge from './SourceBadge';
import { useWorkspace } from '../context/WorkspaceContext';

const CANONICAL_OPTIONS = [
  { value: 'name', label: 'Name (Person / Full Name)' },
  { value: 'email', label: 'Email (Primary Email)' },
  { value: 'phone', label: 'Phone (Mobile / Contact)' },
  { value: 'username', label: 'Username (Platform Handle)' },
  { value: 'source_record_id', label: 'Source Record ID (Identifier)' },
  { value: 'member_id', label: 'Member ID (Loyalty / Club)' },
  { value: 'address', label: 'Address (Location / City)' },
  { value: 'company', label: 'Company (Employer / Org)' },
  { value: 'loyalty_tier', label: 'Loyalty Tier (Rewards Tier)' },
  { value: 'metadata', label: 'Metadata / Extra Attributes' },
  { value: 'ignore', label: '🚫 Ignore / Do Not Index' },
];

export default function SourceManager({ onSourcesChanged }) {
  const { currentWorkspace, refreshWorkspaces } = useWorkspace();

  const [sources, setSources] = useState([]);
  const [loadingSources, setLoadingSources] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [expandedSourceId, setExpandedSourceId] = useState(null);
  const [fileQueue, setFileQueue] = useState([]);
  const fileInputRef = useRef(null);

  // Upload & Schema Mapping Modal/Drawer State
  const [uploadState, setUploadState] = useState({
    active: false,
    file: null,
    sourceId: null,
    columns: [],
    sampleRows: [],
    mappings: {}, // { colName: { canonical_field, confidence_score, is_identifier, method } }
    stage: 'idle', // 'idle' | 'uploading' | 'review' | 'normalizing' | 'indexing' | 'completed' | 'error'
    progressMessage: '',
    error: null,
  });

  // Fetch existing sources scoped to the active workspace session
  const fetchSources = async () => {
    if (!currentWorkspace?.id) return;
    setLoadingSources(true);
    try {
      const res = await api.listSources(currentWorkspace.id);
      setSources(res.data || []);
      if (onSourcesChanged) onSourcesChanged();
      refreshWorkspaces();
    } catch (err) {
      console.error('Failed to fetch sources for workspace:', err);
    } finally {
      setLoadingSources(false);
    }
  };

  const [resolvingSession, setResolvingSession] = useState(false);
  const [resolutionNotice, setResolutionNotice] = useState(null);

  // Manually trigger multi-hop session-wide resolution pass
  const handleRunResolution = async () => {
    if (!currentWorkspace?.id) return;
    setResolvingSession(true);
    setResolutionNotice(null);
    try {
      const res = await api.resolveWorkspace(currentWorkspace.id);
      await fetchSources();
      await refreshWorkspaces();
      if (onSourcesChanged) onSourcesChanged();
      const count = res.data?.resolution?.master_entities ?? res.data?.stats?.master_entities ?? 0;
      const links = res.data?.resolution?.links_discovered ?? res.data?.stats?.links_discovered ?? 0;
      setResolutionNotice(`Resolved ${count} Master Entities with ${links} Multi-Hop Links!`);
      setTimeout(() => setResolutionNotice(null), 6000);
    } catch (err) {
      console.error('Session resolution failed:', err);
      const msg = err.response?.data?.detail || err.message || 'Session resolution failed.';
      setResolutionNotice(`Resolution Error: ${msg}`);
      setTimeout(() => setResolutionNotice(null), 6000);
    } finally {
      setResolvingSession(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, [currentWorkspace?.id]);

  // Handle Drag & Drop
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelected(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesSelected(Array.from(e.target.files));
    }
  };

  // Handle multi-file selection queue
  const handleFilesSelected = (files) => {
    const validFiles = files.filter((f) => {
      const ext = f.name.split('.').pop().toLowerCase();
      return ['csv', 'sql'].includes(ext);
    });

    if (validFiles.length === 0) {
      alert('Please upload .csv or .sql file format(s).');
      return;
    }

    // Process the first file immediately and queue remaining
    const [first, ...rest] = validFiles;
    setFileQueue(rest);
    processFileUpload(first);
  };

  // Upload file and inspect schema
  const processFileUpload = async (file) => {
    const filename = file.name;
    const ext = filename.split('.').pop().toLowerCase();

    setUploadState({
      active: true,
      file,
      sourceId: null,
      columns: [],
      sampleRows: [],
      mappings: {},
      stage: 'uploading',
      progressMessage: `Uploading ${filename} to session "${currentWorkspace?.name || 'Active'}"...`,
      error: null,
    });

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('source_type', ext.toUpperCase());
      if (currentWorkspace?.id) {
        formData.append('workspace_id', currentWorkspace.id);
      }

      const res = await api.uploadSource(formData, currentWorkspace?.id);
      const data = res.data;

      // Extract mappings from suggested_mappings
      const initialMappings = {};
      (data.columns || []).forEach((col) => {
        const suggestion = (data.suggested_mappings || {})[col] || {
          canonical_field: 'name',
          confidence_score: 0.5,
          is_identifier: false,
          method: 'heuristic',
        };
        initialMappings[col] = {
          canonical_field: suggestion.canonical_field,
          confidence_score: suggestion.confidence_score,
          is_identifier: suggestion.is_identifier,
          method: suggestion.method,
        };
      });

      setUploadState((prev) => ({
        ...prev,
        sourceId: data.source_id,
        columns: data.columns || [],
        sampleRows: data.sample_rows || [],
        columnSamples: data.column_samples || {},
        mappings: initialMappings,
        stage: 'review',
        progressMessage: 'Schema detected. Verify column mappings below.',
      }));
    } catch (err) {
      console.error('File upload failed:', err);
      const msg = err.response?.data?.detail || err.message || 'File upload failed.';
      setUploadState((prev) => ({
        ...prev,
        stage: 'error',
        error: msg,
      }));
    }
  };


  // User edits a mapping dropdown
  const handleMappingChange = (col, newCanonical) => {
    setUploadState((prev) => {
      const curr = prev.mappings[col] || {};
      const isIdent = ['email', 'phone', 'username', 'member_id', 'source_record_id'].includes(newCanonical);
      return {
        ...prev,
        mappings: {
          ...prev.mappings,
          [col]: {
            ...curr,
            canonical_field: newCanonical,
            is_identifier: isIdent,
            confidence_score: 1.0, // User verified
            method: 'user_confirmed',
          },
        },
      };
    });
  };

  // Toggle is_identifier checkbox
  const handleIdentifierToggle = (col) => {
    setUploadState((prev) => {
      const curr = prev.mappings[col] || {};
      return {
        ...prev,
        mappings: {
          ...prev.mappings,
          [col]: {
            ...curr,
            is_identifier: !curr.is_identifier,
          },
        },
      };
    });
  };

  // Confirm mapping and run background ingestion
  const handleConfirmMapping = async () => {
    if (!uploadState.sourceId) return;

    // Filter out 'ignore' mappings
    const cleanMappings = {};
    Object.entries(uploadState.mappings).forEach(([col, m]) => {
      if (m.canonical_field !== 'ignore') {
        cleanMappings[col] = {
          canonical_field: m.canonical_field,
          confidence_score: m.confidence_score,
          is_identifier: m.is_identifier,
        };
      }
    });

    setUploadState((prev) => ({
      ...prev,
      stage: 'normalizing',
      progressMessage: 'Normalizing values (E.164 phones, RFC emails, lowercase tokens)...',
    }));

    try {
      await api.confirmMapping(uploadState.sourceId, cleanMappings);

      // Transition to Indexing state
      setUploadState((prev) => ({
        ...prev,
        stage: 'indexing',
        progressMessage: 'Building EAV inverted attribute indexes and composite keys...',
      }));

      // Poll source status until INDEXED
      const sourceId = uploadState.sourceId;
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await api.getSourceStatus(sourceId);
          if (statusRes.data.status === 'INDEXED') {
            clearInterval(pollInterval);
            setUploadState((prev) => ({
              ...prev,
              stage: 'completed',
              progressMessage: `Ingestion complete! Successfully indexed ${statusRes.data.record_count} records.`,
            }));
            fetchSources();
          } else if (statusRes.data.status === 'FAILED') {
            clearInterval(pollInterval);
            setUploadState((prev) => ({
              ...prev,
              stage: 'error',
              error: 'Ingestion failed on background worker task.',
            }));
          }
        } catch {
          // Keep polling
        }
      }, 1000);
    } catch (err) {
      console.error('Confirmation failed:', err);
      const msg = err.response?.data?.detail || err.message || 'Mapping confirmation failed.';
      setUploadState((prev) => ({
        ...prev,
        stage: 'error',
        error: msg,
      }));
    }
  };

  const closeDrawer = () => {
    setUploadState({
      active: false,
      file: null,
      sourceId: null,
      columns: [],
      sampleRows: [],
      mappings: {},
      stage: 'idle',
      progressMessage: '',
      error: null,
    });
    if (fileInputRef.current) fileInputRef.current.value = '';

    // If more files are in the upload queue, advance to the next file
    if (fileQueue.length > 0) {
      const [nextFile, ...rest] = fileQueue;
      setFileQueue(rest);
      setTimeout(() => processFileUpload(nextFile), 200);
    }
  };

  const handleDeleteSource = async (sourceId, sourceName) => {
    if (!window.confirm(`Are you sure you want to remove "${sourceName}" from this session?`)) return;
    try {
      await api.deleteSource(sourceId);
      await fetchSources();
    } catch (err) {
      console.error('Failed to remove source:', err);
      alert('Failed to remove source.');
    }
  };

  return (
    <div>
      {/* Active Session Context Bar */}
      <div className="mb-6 p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold">
            <FolderKanban className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-indigo-700 dark:text-indigo-300 font-semibold uppercase tracking-wider">
                Active Session
              </span>
              <span className="font-bold text-sm text-slate-900 dark:text-white">
                {currentWorkspace?.name || 'Loading Session...'}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {sources.length} {sources.length === 1 ? 'source' : 'sources'} ingested • Drop 1, 2, 5, or 10+ arbitrary CSV/SQL files
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleRunResolution}
            disabled={resolvingSession || loadingSources || !currentWorkspace?.id}
            className="self-start sm:self-center flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-sm"
            title="Execute session-wide multi-hop BFS resolution across all active datasets"
          >
            <Sparkles className={`w-3.5 h-3.5 ${resolvingSession ? 'animate-spin' : ''}`} />
            {resolvingSession ? 'Resolving...' : 'Run Session Resolution'}
          </button>
          <button
            onClick={fetchSources}
            disabled={loadingSources}
            className="self-start sm:self-center flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingSources ? 'animate-spin' : ''}`} />
            Refresh Sources
          </button>
        </div>
      </div>

      {/* Resolution Notification Banner */}
      {resolutionNotice && (
        <div className="mb-4 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs flex items-center justify-between animate-fadeIn shadow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
            <span className="font-semibold">{resolutionNotice}</span>
          </div>
          <button
            onClick={() => setResolutionNotice(null)}
            className="text-emerald-600 hover:text-emerald-800 dark:text-emerald-400 p-1"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Drag & Drop File Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative cursor-pointer rounded-2xl p-8 border-2 border-dashed transition-all text-center mb-8 ${
          dragActive
            ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/30 scale-[1.01]'
            : 'border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:border-indigo-400 dark:hover:border-indigo-500'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".csv,.sql"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
          <UploadCloud className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
          Drop database dumps or click to browse
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto mb-3">
          Upload 1 or multiple <span className="font-mono text-indigo-600 dark:text-indigo-400">.csv</span> or{' '}
          <span className="font-mono text-indigo-600 dark:text-indigo-400">.sql</span> dumps simultaneously.
        </p>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
          <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
          Incremental Ingestion • AI Canonical Mapping
        </div>
      </div>

      {/* Schema Review & AI Mapping Drawer / Modal */}
      {uploadState.active && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="relative w-full max-w-4xl bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden animate-fadeIn">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-500" />
                  <h3 className="font-bold text-slate-900 dark:text-white text-base">
                    Interactive Schema Review & AI Column Mapping
                  </h3>
                  <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-semibold border border-indigo-200 dark:border-indigo-800">
                    {uploadState.file?.name}
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Inspect source columns, review AI suggested canonical targets, and confirm indexing parameters
                </p>
              </div>
              <button
                onClick={closeDrawer}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 max-h-[65vh] overflow-y-auto">
              {/* Live Progress Tracker */}
              {['uploading', 'normalizing', 'indexing', 'completed'].includes(uploadState.stage) && (
                <div className="mb-6 p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center justify-between text-xs font-semibold mb-2">
                    <span className="text-slate-700 dark:text-slate-300">Ingestion Pipeline Status</span>
                    <span className="text-indigo-600 dark:text-indigo-400 font-mono capitalize">
                      {uploadState.stage}
                    </span>
                  </div>
                  {/* Progress Steps Bar */}
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    {[
                      { key: 'uploading', label: '1. Uploading' },
                      { key: 'normalizing', label: '2. Normalizing' },
                      { key: 'indexing', label: '3. Indexing' },
                      { key: 'completed', label: '4. Completed' },
                    ].map((step, idx) => {
                      const stages = ['uploading', 'normalizing', 'indexing', 'completed'];
                      const currentIdx = stages.indexOf(uploadState.stage);
                      const isPast = currentIdx >= idx;
                      const isCurrent = uploadState.stage === step.key;
                      return (
                        <div
                          key={step.key}
                          className={`p-2 rounded-lg text-center text-xs font-medium border transition-all ${
                            isCurrent
                              ? 'bg-indigo-600 text-white border-indigo-600 animate-pulse'
                              : isPast
                              ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800'
                              : 'bg-slate-100 dark:bg-slate-900 text-slate-400 border-slate-200 dark:border-slate-800'
                          }`}
                        >
                          {step.label}
                        </div>
                      );
                    })}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 font-mono flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                    {uploadState.progressMessage}
                  </div>
                </div>
              )}

              {/* Error Message */}
              {uploadState.error && (
                <div className="mb-4 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{uploadState.error}</span>
                </div>
              )}

              {/* Schema Review Table */}
              {uploadState.columns.length > 0 && (
                <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
                  <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                      <tr>
                        <th scope="col" className="px-4 py-3">Source Column</th>
                        <th scope="col" className="px-4 py-3">Sample Values</th>
                        <th scope="col" className="px-4 py-3">Canonical Target</th>
                        <th scope="col" className="px-4 py-3">AI Confidence Badge</th>
                        <th scope="col" className="px-4 py-3 text-center">Identifier</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80 bg-white dark:bg-slate-900">
                      {uploadState.columns.map((col) => {
                        const mapping = uploadState.mappings[col] || {};
                        const samples = (uploadState.columnSamples && uploadState.columnSamples[col]?.length > 0)
                          ? uploadState.columnSamples[col].join(', ')
                          : uploadState.sampleRows
                              .map((r) => r[col])
                              .filter((v) => v !== undefined && v !== null && String(v).trim() !== '' && String(v).toLowerCase() !== 'nan')
                              .slice(0, 3)
                              .join(', ');

                        const scorePct = Math.round((mapping.confidence_score || 0.8) * 100);
                        const isAi = mapping.method?.includes('gemini') || mapping.confidence_score > 0.8;

                        return (
                          <tr key={col} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                            <td className="px-4 py-3 font-mono font-bold text-slate-900 dark:text-white">
                              {col}
                            </td>
                            <td className="px-4 py-3 text-slate-500 dark:text-slate-400 font-mono text-[11px] max-w-xs truncate" title={samples}>
                              {samples || '—'}
                            </td>
                            <td className="px-4 py-3">
                              <select
                                value={mapping.canonical_field || 'name'}
                                onChange={(e) => handleMappingChange(col, e.target.value)}
                                disabled={['normalizing', 'indexing', 'completed'].includes(uploadState.stage)}
                                className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                              >
                                {CANONICAL_OPTIONS.map((opt) => (
                                  <option key={opt.value} value={opt.value}>
                                    {opt.label}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td className="px-4 py-3">
                              {isAi ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                                  <Sparkles className="w-3 h-3 text-purple-500" />
                                  ✨ {scorePct}% AI Match
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                  <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                                  Rule Matched ({scorePct}%)
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <input
                                type="checkbox"
                                checked={mapping.is_identifier || false}
                                onChange={() => handleIdentifierToggle(col)}
                                disabled={['normalizing', 'indexing', 'completed'].includes(uploadState.stage)}
                                className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Modal Footer Actions */}
            <div className="p-6 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-between">
              <div className="text-xs text-slate-500 dark:text-slate-400">
                {uploadState.stage === 'completed'
                  ? 'All records indexed into the high-performance EAV index.'
                  : 'Identifiers will be automatically added to the BFS queue during resolution.'}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={closeDrawer}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                >
                  {uploadState.stage === 'completed' ? 'Close' : 'Cancel'}
                </button>
                {uploadState.stage !== 'completed' && (
                  <button
                    onClick={handleConfirmMapping}
                    disabled={['normalizing', 'indexing'].includes(uploadState.stage)}
                    className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 disabled:opacity-50 flex items-center gap-1.5 transition-all"
                  >
                    <Play className="w-3.5 h-3.5" />
                    Confirm Mapping & Index
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Ingested Datasets Table & Accordion */}
      <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-500" />
            <h3 className="font-bold text-slate-900 dark:text-white text-sm">
              Datasets Ingested in this Session ({sources.length})
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Session ID: {currentWorkspace?.id || '—'}
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" className="px-4 py-3">Source Name</th>
                <th scope="col" className="px-4 py-3">Provenance Category</th>
                <th scope="col" className="px-4 py-3">Format</th>
                <th scope="col" className="px-4 py-3">Indexed Records</th>
                <th scope="col" className="px-4 py-3">Status</th>
                <th scope="col" className="px-4 py-3">Uploaded</th>
                <th scope="col" className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80 bg-white dark:bg-slate-900">
              {sources.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-400 dark:text-slate-500">
                    <Database className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-slate-700" />
                    <p className="font-semibold text-slate-700 dark:text-slate-300 text-sm">
                      Clean Canvas — No Sources Ingested Yet
                    </p>
                    <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                      Drag & drop your CSV or SQL files above to add datasets to this session. You can upload 1, 2, 5, 10, or more sources.
                    </p>
                  </td>
                </tr>
              ) : (
                sources.map((s) => {
                  const isExpanded = expandedSourceId === s.id;
                  return (
                    <React.Fragment key={s.id}>
                      <tr className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">
                          <button
                            onClick={() => setExpandedSourceId(isExpanded ? null : s.id)}
                            className="flex items-center gap-1.5 hover:text-indigo-600 dark:hover:text-indigo-400 text-left"
                          >
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                            )}
                            <span className="truncate max-w-[200px]" title={s.name}>
                              {s.name}
                            </span>
                          </button>
                        </td>
                        <td className="px-4 py-3">
                          <SourceBadge sourceName={s.name} />
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                          <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-bold">
                            {s.source_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono font-bold text-slate-900 dark:text-slate-200">
                          {s.record_count?.toLocaleString() || 0} rows
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              s.status === 'INDEXED'
                                ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                                : s.status === 'MAPPED'
                                ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800'
                                : 'bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
                            }`}
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-current" />
                            {s.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                          {s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => {
                                // Inspect schema for this source again if needed
                                setUploadState((prev) => ({
                                  ...prev,
                                  active: true,
                                  file: { name: s.name },
                                  sourceId: s.id,
                                  columns: ['name', 'email', 'phone', 'address'],
                                  sampleRows: [],
                                  mappings: {
                                    name: { canonical_field: 'name', confidence_score: 1.0, is_identifier: false },
                                    email: { canonical_field: 'email', confidence_score: 1.0, is_identifier: true },
                                    phone: { canonical_field: 'phone', confidence_score: 1.0, is_identifier: true },
                                    address: { canonical_field: 'address', confidence_score: 1.0, is_identifier: false },
                                  },
                                  stage: 'review',
                                  progressMessage: 'Configure canonical mappings for this source.',
                                }));
                              }}
                              className="px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium text-[11px] transition-colors flex items-center gap-1"
                              title="Configure Schema Mapping"
                            >
                              <Settings2 className="w-3 h-3 text-indigo-500" />
                              <span className="hidden sm:inline">Configure Mapping</span>
                            </button>

                            <button
                              onClick={() => handleDeleteSource(s.id, s.name)}
                              className="p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                              title="Remove dataset from session"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Expandable Accordion Row */}
                      {isExpanded && (
                        <tr className="bg-slate-50/50 dark:bg-slate-950/50">
                          <td colSpan={7} className="px-6 py-4">
                            <div className="text-xs space-y-2">
                              <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
                                <span>Storage Path: <code className="font-mono text-[11px] text-slate-700 dark:text-slate-300">{s.file_path}</code></span>
                                <span>Status: <strong className="font-mono">{s.status}</strong></span>
                              </div>
                              <p className="text-[11px] text-slate-400">
                                All {s.record_count?.toLocaleString()} rows from this dataset are indexed into the session EAV store and participate dynamically in progressive multi-hop BFS discovery.
                              </p>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

