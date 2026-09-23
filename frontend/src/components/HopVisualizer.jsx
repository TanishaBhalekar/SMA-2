import React from 'react';
import { ArrowRight, ArrowDown, Key, CheckCircle2, Shield, Sparkles, Database, GitMerge } from 'lucide-react';
import SourceBadge from './SourceBadge';

export default function HopVisualizer({ hops = [], lineage = [], seed = { field: 'email', value: '' } }) {
  // Aggregate hops by source / step sequence
  // If hops exist, group them by source/step or display progressive sequence
  const sourceNameMap = {};
  lineage.forEach((l) => {
    if (l.source_id && l.source_name) {
      sourceNameMap[l.source_id] = l.source_name;
    }
  });

  // Group hops into discrete steps (Hop 1, Hop 2, Hop 3, etc.)
  const stepsMap = {};
  hops.forEach((h) => {
    const sOrder = h.step_order || 1;
    if (!stepsMap[sOrder]) {
      stepsMap[sOrder] = {
        stepOrder: sOrder,
        sourceId: h.source_id,
        sourceName: h.source_name || sourceNameMap[h.source_id] || `Source #${h.source_id}`,
        matchedField: h.matched_field,
        matchedValue: h.matched_value,
        discovered: [],
      };
    }
    stepsMap[sOrder].discovered.push({
      field: h.discovered_field,
      value: h.discovered_value,
    });
  });

  const stepList = Object.values(stepsMap).sort((a, b) => a.stepOrder - b.stepOrder);

  return (
    <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm mb-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-100 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <GitMerge className="w-5 h-5 text-indigo-500" />
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Progressive Hop-by-Hop Discovery Chain
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-mono font-medium border border-indigo-200 dark:border-indigo-800">
              {stepList.length} Connected Hops
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Dynamic BFS entity traversal jumping across isolated database boundaries via unlocked predicate keys
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Transitive Closure Verified
        </div>
      </div>

      {/* Connected Sequence Spine */}
      <div className="relative">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 relative">
          {/* Step 0: Anchor Seed */}
          <div className="flex flex-col relative group">
            <div className="p-4 rounded-xl border border-indigo-300 dark:border-indigo-800/80 bg-indigo-50/50 dark:bg-indigo-950/20 shadow-sm hover:border-indigo-400 transition-all h-full flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400">
                    Step 0 • Anchor Seed
                  </span>
                  <Key className="w-4 h-4 text-indigo-500" />
                </div>
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1">
                  Initial Identifier Query
                </div>
                <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-900/60 mt-2">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono capitalize">
                    {seed.field || 'Identifier'}:
                  </div>
                  <div className="text-xs font-mono font-bold text-indigo-600 dark:text-indigo-300 break-all">
                    {seed.value || 'N/A'}
                  </div>
                </div>
              </div>
              <div className="mt-4 pt-2 border-t border-indigo-200/60 dark:border-indigo-900/40 text-[11px] text-indigo-600 dark:text-indigo-400 flex items-center gap-1 font-medium">
                <Sparkles className="w-3 h-3" /> Traversal Triggered
              </div>
            </div>
          </div>

          {/* Subsequent Hops (Hop 1 to N) */}
          {stepList.map((step, idx) => (
            <div key={step.stepOrder} className="flex flex-col relative group">
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/80 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm transition-all h-full flex flex-col justify-between">
                <div>
                  {/* Step Order & Provenance Badge */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Hop {step.stepOrder}
                    </span>
                    <SourceBadge sourceName={step.sourceName} />
                  </div>

                  {/* Bridge Predicate */}
                  <div className="mb-3 p-2 rounded-lg bg-white dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800">
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                      Matched Predicate:
                    </div>
                    <div className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 truncate" title={`${step.matchedField} = ${step.matchedValue}`}>
                      <span className="text-indigo-500 dark:text-indigo-400 font-normal">{step.matchedField}:</span>{' '}
                      {step.matchedValue}
                    </div>
                  </div>

                  {/* Newly Discovered Attributes */}
                  <div>
                    <div className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                      Unlocked Attributes:
                    </div>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                      {step.discovered.map((attr, aIdx) => (
                        <div
                          key={aIdx}
                          className="px-2 py-1 rounded bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800/80 text-[11px] flex items-center justify-between"
                        >
                          <span className="font-mono text-slate-500 dark:text-slate-400 text-[10px] uppercase">
                            {attr.field}
                          </span>
                          <span className="font-mono font-bold text-slate-900 dark:text-slate-100 truncate ml-2 max-w-[130px]" title={attr.value}>
                            {attr.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                  <span className="font-mono text-[10px]">
                    +{step.discovered.length} fields
                  </span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    Indexed
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
