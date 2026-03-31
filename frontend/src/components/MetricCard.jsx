import React from 'react';

export default function MetricCard({ title, value, unit, icon, color, subtext }) {
  const colorMap = {
    cyan: 'border-cyan-500/30 bg-cyan-500/5 text-cyan-400',
    red: 'border-red-500/30 bg-red-500/5 text-red-400',
    yellow: 'border-yellow-500/30 bg-yellow-500/5 text-yellow-400',
    green: 'border-green-500/30 bg-green-500/5 text-green-400',
    purple: 'border-purple-500/30 bg-purple-500/5 text-purple-400',
  };
  return (
    <div className={`glass border p-5 rounded-xl fade-in-up ${colorMap[color] || colorMap.cyan}`}>
      <div className="flex justify-between items-start">
        <div>
          <p className="text-gray-400 text-xs font-medium uppercase tracking-widest">{title}</p>
          <p className="text-3xl font-bold mt-1 font-mono">
            {value}<span className="text-sm ml-1 font-normal opacity-70">{unit}</span>
          </p>
          {subtext && <p className="text-xs text-gray-500 mt-1">{subtext}</p>}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  );
}
