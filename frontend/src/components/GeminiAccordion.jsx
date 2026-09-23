import React, { useState } from 'react';
import { Sparkles, ChevronDown, ChevronUp, Bot, ShieldCheck, Zap } from 'lucide-react';

export default function GeminiAccordion({ explanation }) {
  const [isOpen, setIsOpen] = useState(true);

  if (!explanation) return null;

  return (
    <div className="rounded-2xl border border-indigo-200 dark:border-indigo-900/60 bg-gradient-to-br from-indigo-50/50 via-white to-purple-50/30 dark:from-slate-900 dark:via-indigo-950/20 dark:to-slate-900 shadow-sm overflow-hidden mb-8 transition-all">
      {/* Header Accordion Toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-indigo-50/40 dark:hover:bg-indigo-950/40 transition-colors focus:outline-none"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/20">
            <Sparkles className="w-4 h-4 animate-spin-slow" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-1.5">
                ✨ Gemini Explanation & Match Rationale
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800">
                AI Synthesized
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Plain-English reasoning validating cross-silo identity linkage and zero conflicting attributes
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400 hidden sm:inline">
            {isOpen ? 'Collapse Rationale' : 'Expand Rationale'}
          </span>
          <div className="p-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
            {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </button>

      {/* Accordion Content */}
      {isOpen && (
        <div className="px-6 pb-6 pt-2 border-t border-indigo-100 dark:border-indigo-900/40">
          <div className="p-5 rounded-xl bg-white dark:bg-slate-950 border border-indigo-100 dark:border-indigo-900/60 shadow-inner">
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100 dark:border-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              <span>Entity Resolution Proof & Transitive Closure Analysis</span>
            </div>
            <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed space-y-3 whitespace-pre-line font-sans">
              {explanation}
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
              <span className="flex items-center gap-1 font-mono">
                <Zap className="w-3 h-3 text-amber-500" /> Model: gemini-2.5-flash / Rule-Engine Synthesizer
              </span>
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                Verified Cross-Silo Linkage
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
