import React from 'react';

export function getSourceBadgeStyle(sourceName = '') {
  const lower = sourceName.toLowerCase();
  if (lower.includes('hr') || lower.includes('human')) {
    return {
      bg: 'bg-blue-500/10 dark:bg-blue-500/20',
      text: 'text-blue-600 dark:text-blue-400',
      border: 'border-blue-500/30',
      label: 'HR DB',
      dot: 'bg-blue-500',
    };
  }
  if (lower.includes('crm') || lower.includes('client') || lower.includes('sales')) {
    return {
      bg: 'bg-emerald-500/10 dark:bg-emerald-500/20',
      text: 'text-emerald-600 dark:text-emerald-400',
      border: 'border-emerald-500/30',
      label: 'CRM DB',
      dot: 'bg-emerald-500',
    };
  }
  if (lower.includes('platform') || lower.includes('app') || lower.includes('saas')) {
    return {
      bg: 'bg-purple-500/10 dark:bg-purple-500/20',
      text: 'text-purple-600 dark:text-purple-400',
      border: 'border-purple-500/30',
      label: 'Platform DB',
      dot: 'bg-purple-500',
    };
  }
  if (lower.includes('member') || lower.includes('loyalty') || lower.includes('rewards')) {
    return {
      bg: 'bg-amber-500/10 dark:bg-amber-500/20',
      text: 'text-amber-600 dark:text-amber-400',
      border: 'border-amber-500/30',
      label: 'Membership DB',
      dot: 'bg-amber-500',
    };
  }
  return {
    bg: 'bg-cyan-500/10 dark:bg-cyan-500/20',
    text: 'text-cyan-600 dark:text-cyan-400',
    border: 'border-cyan-500/30',
    label: sourceName || 'Custom DB',
    dot: 'bg-cyan-500',
  };
}

export default function SourceBadge({ sourceName, className = '' }) {
  const style = getSourceBadgeStyle(sourceName);
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style.bg} ${style.text} ${style.border} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {sourceName || style.label}
    </span>
  );
}
