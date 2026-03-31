import React from 'react';

const severityConfig = {
  CRITICAL: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/40', dot: 'bg-red-400' },
  HIGH:     { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/40', dot: 'bg-orange-400' },
  MEDIUM:   { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/40', dot: 'bg-yellow-400' },
  LOW:      { bg: 'bg-green-500/20',  text: 'text-green-400',  border: 'border-green-500/40',  dot: 'bg-green-400' },
};

export default function AlertBadge({ severity }) {
  const c = severityConfig[severity] || severityConfig.LOW;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${c.bg} ${c.text} ${c.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${c.dot}`} />
      {severity}
    </span>
  );
}
