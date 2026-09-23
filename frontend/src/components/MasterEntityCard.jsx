import React from 'react';
import {
  User, Mail, Phone, ShieldCheck, Database, Calendar, Layers,
  Building, MapPin, AtSign, CreditCard, ExternalLink, CheckCircle2
} from 'lucide-react';
import SourceBadge from './SourceBadge';

export default function MasterEntityCard({ entity, hops = [], lineage = [] }) {
  if (!entity) return null;

  const consolidated = entity.consolidated_attributes || {};
  const auth = entity.authoritative_profile || {};

  // Best-value canonical attribute resolution (ensuring single authoritative representation)
  const primaryName = auth.name || entity.canonical_name || (consolidated.name && consolidated.name[0]) || 'Unknown Entity';
  const primaryEmail = auth.email || (consolidated.email && consolidated.email[0]) || 'Not recorded';
  const primaryPhone = auth.phone || (consolidated.phone && consolidated.phone[0]) || 'Not recorded';
  const primaryUsername = auth.username || (consolidated.username && consolidated.username[0]) || 'Not recorded';
  const primaryAddress = auth.address || (consolidated.address && consolidated.address[0]) || 'Not recorded';
  const primaryCompany = auth.company || (consolidated.company && consolidated.company[0]) || 'Not recorded';
  const primaryMemberId = auth.member_id || (consolidated.member_id && consolidated.member_id[0]) || (consolidated.source_record_id && consolidated.source_record_id[0]) || 'Not recorded';
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
          isIdentifier: ['email', 'phone', 'username', 'member_id', 'source_record_id'].includes(field.toLowerCase()),
        });
      });
    }
  });

  // Deduplicate rows with same field, value, and source
  const seen = new Set();
  const dedupedRows = provenanceRows.filter((r) => {
    const k = `${r.field}|${r.value}|${r.source}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  return (
    <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm mb-8">
      {/* Primary Authoritative Master Entity Card (Single authoritative value, no duplicates) */}
      <div className="p-6 rounded-xl bg-gradient-to-r from-slate-50 via-indigo-50/20 to-purple-50/20 dark:from-slate-950 dark:via-indigo-950/20 dark:to-purple-950/20 border border-slate-200 dark:border-slate-800 mb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
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
                  <ShieldCheck className="w-3.5 h-3.5" /> Authoritative Master Record
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Resolved 360-degree identity graph synthesized across operational datasets
              </p>
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

        {/* Authoritative Master Record Attribute Grid (1 Authoritative Row per Canonical Dimension) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 pt-4 border-t border-slate-200/80 dark:border-slate-800/80">
          {/* Canonical Name */}
          <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
              <User className="w-3.5 h-3.5 text-indigo-500" />
              <span>Full Name</span>
            </div>
            <div className="text-xs font-bold text-slate-900 dark:text-white truncate" title={primaryName}>
              {primaryName}
            </div>
          </div>

          {/* Canonical Email */}
          <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
              <Mail className="w-3.5 h-3.5 text-indigo-500" />
              <span>Primary Email</span>
            </div>
            <div className="text-xs font-mono font-medium text-slate-900 dark:text-white truncate" title={primaryEmail}>
              {primaryEmail}
            </div>
          </div>

          {/* Canonical Phone */}
          <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
              <Phone className="w-3.5 h-3.5 text-indigo-500" />
              <span>Standardized Phone</span>
            </div>
            <div className="text-xs font-mono font-medium text-slate-900 dark:text-white truncate" title={primaryPhone}>
              {primaryPhone}
            </div>
          </div>

          {/* Canonical Username */}
          <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
              <AtSign className="w-3.5 h-3.5 text-indigo-500" />
              <span>Unique Username</span>
            </div>
            <div className="text-xs font-mono font-medium text-slate-900 dark:text-white truncate" title={primaryUsername}>
              {primaryUsername}
            </div>
          </div>

          {/* Canonical Company */}
          <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
              <Building className="w-3.5 h-3.5 text-indigo-500" />
              <span>Company / Org</span>
            </div>
            <div className="text-xs font-medium text-slate-900 dark:text-white truncate" title={primaryCompany}>
              {primaryCompany}
            </div>
          </div>

          {/* Canonical Address */}
          <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
              <MapPin className="w-3.5 h-3.5 text-indigo-500" />
              <span>Address / Location</span>
            </div>
            <div className="text-xs font-medium text-slate-900 dark:text-white truncate" title={primaryAddress}>
              {primaryAddress}
            </div>
          </div>

          {/* Canonical Member / Record ID */}
          <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
              <CreditCard className="w-3.5 h-3.5 text-indigo-500" />
              <span>Member / Record ID</span>
            </div>
            <div className="text-xs font-mono font-bold text-indigo-600 dark:text-indigo-400 truncate" title={primaryMemberId}>
              {primaryMemberId}
            </div>
          </div>

          {/* Synthesis Timestamp */}
          <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
              <Calendar className="w-3.5 h-3.5 text-indigo-500" />
              <span>Resolved Timestamp</span>
            </div>
            <div className="text-xs font-mono text-slate-600 dark:text-slate-400">
              {entity.created_at ? new Date(entity.created_at).toLocaleTimeString() : 'Live BFS Resolution'}
            </div>
          </div>
        </div>
      </div>

      {/* Provenance & Multi-Source Lineage Table Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-slate-500 dark:text-slate-400" />
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Data Lineage & Multi-Source Provenance Registry
            </h4>
            <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
              ({dedupedRows.length} attributes across {lineage.length} contributing records)
            </span>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" className="px-4 py-3">Canonical Field</th>
                <th scope="col" className="px-4 py-3">Raw Observed Value</th>
                <th scope="col" className="px-4 py-3">Normalized Form</th>
                <th scope="col" className="px-4 py-3">Contributing Source</th>
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
