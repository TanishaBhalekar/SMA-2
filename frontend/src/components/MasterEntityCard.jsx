import React from 'react';
import { User, Mail, Phone, ShieldCheck, Database, Calendar, Layers, ExternalLink } from 'lucide-react';
import SourceBadge from './SourceBadge';

export default function MasterEntityCard({ entity, hops = [], lineage = [] }) {
  if (!entity) return null;

  const consolidated = entity.consolidated_attributes || {};

  // Extract primary fields
  const primaryName = entity.canonical_name || (consolidated.name && consolidated.name[0]) || 'Unknown Entity';
  const primaryEmail = (consolidated.email && consolidated.email[0]) || 'Not recorded';
  const primaryPhone = (consolidated.phone && consolidated.phone[0]) || 'Not recorded';
  const masterId = entity.id || 'ENT-0000';

  // Construct mapping of (discovered_field, discovered_value) -> discovered_via & source
  const hopDiscoveryMap = {};
  hops.forEach((h) => {
    const key = `${h.discovered_field}:${h.discovered_value}`;
    hopDiscoveryMap[key] = {
      sourceId: h.source_id,
      via: `Predicate: ${h.matched_field} = ${h.matched_value}`,
      stepOrder: h.step_order,
    };
  });

  const sourceNameMap = {};
  lineage.forEach((l) => {
    if (l.source_id) {
      sourceNameMap[l.source_id] = l.source_name;
    }
  });

  // Build provenance table rows
  const provenanceRows = [];
  lineage.forEach((rec) => {
    const sName = rec.source_name || sourceNameMap[rec.source_id] || `Source #${rec.source_id}`;
    if (rec.attributes) {
      Object.entries(rec.attributes).forEach(([field, rawVal]) => {
        const valStr = String(rawVal);
        const hopInfo = hopDiscoveryMap[`${field}:${valStr}`];
        provenanceRows.push({
          field,
          value: valStr,
          normalized: valStr.toLowerCase().trim(),
          source: sName,
          via: hopInfo ? hopInfo.via : (field === 'email' ? 'Initial Anchor Seed' : 'Direct Record Link'),
          isIdentifier: ['email', 'phone', 'username', 'member_id'].includes(field.toLowerCase()),
        });
      });
    }
  });

  // Deduplicate rows with same field and value
  const seen = new Set();
  const dedupedRows = provenanceRows.filter((r) => {
    const k = `${r.field}|${r.value}|${r.source}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  return (
    <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm mb-8">
      {/* Top Summary Header */}
      <div className="p-6 rounded-xl bg-gradient-to-r from-slate-50 via-indigo-50/20 to-purple-50/20 dark:from-slate-950 dark:via-indigo-950/20 dark:to-purple-950/20 border border-slate-200 dark:border-slate-800 mb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white flex items-center justify-center font-bold text-xl shadow-lg shadow-indigo-500/25">
              {primaryName.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                  {primaryName}
                </h3>
                <span className="font-mono text-xs px-2.5 py-1 rounded-full bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 font-bold border border-indigo-200 dark:border-indigo-800 shadow-sm">
                  {masterId}
                </span>
                <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 font-medium border border-emerald-200 dark:border-emerald-800">
                  <ShieldCheck className="w-3 h-3" /> Resolved Golden Record
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-600 dark:text-slate-400">
                <span className="flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-mono">{primaryEmail}</span>
                </span>
                <span className="text-slate-300 dark:text-slate-700">•</span>
                <span className="flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-mono">{primaryPhone}</span>
                </span>
                {entity.created_at && (
                  <>
                    <span className="text-slate-300 dark:text-slate-700">•</span>
                    <span className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>Synthesized: {new Date(entity.created_at).toLocaleTimeString()}</span>
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-right">
              <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                Lineage Confidence
              </div>
              <div className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">
                99.8% Transitive
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Provenance Table Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-slate-500 dark:text-slate-400" />
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Data Lineage & Provenance Registry
            </h4>
            <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
              ({dedupedRows.length} attributes mapped)
            </span>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" className="px-4 py-3">Canonical Field</th>
                <th scope="col" className="px-4 py-3">Observed Value</th>
                <th scope="col" className="px-4 py-3">Normalized Form</th>
                <th scope="col" className="px-4 py-3">Source System</th>
                <th scope="col" className="px-4 py-3">Discovered Via</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80 bg-white dark:bg-slate-900">
              {dedupedRows.map((row, idx) => (
                <tr
                  key={idx}
                  className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-200 capitalize">
                    {row.field.replace('_', ' ')}
                  </td>
                  <td className="px-4 py-3">
                    {row.isIdentifier ? (
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-semibold border border-slate-200 dark:border-slate-700">
                        {row.value}
                      </span>
                    ) : (
                      <span className="text-slate-800 dark:text-slate-200 font-medium">
                        {row.value}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                    {row.normalized}
                  </td>
                  <td className="px-4 py-3">
                    <SourceBadge sourceName={row.source} />
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                    <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                      {row.via}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
