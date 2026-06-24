'use client';

import { FlaskConical } from 'lucide-react';
import { SystemInfo } from '@/lib/api';

interface SystemSelectorProps {
  systems: SystemInfo[];
  selectedId: string;
  onChange: (id: string) => void;
  disabled?: boolean;
}

// Short badge labels for each system id
const BADGE: Record<string, { label: string; color: string }> = {
  multi_agent:        { label: 'Full',    color: 'bg-cmu-red text-white' },
  multi_agent_opaque: { label: 'Opaque',  color: 'bg-gray-700 text-white' },
  one_shot:           { label: '1-Shot',  color: 'bg-blue-600 text-white' },
  single_agent_cot:   { label: 'CoT',     color: 'bg-purple-600 text-white' },
  single_agent:       { label: 'Single',  color: 'bg-gray-500 text-white' },
};

export default function SystemSelector({
  systems,
  selectedId,
  onChange,
  disabled = false,
}: SystemSelectorProps) {
  if (!systems.length) return null;

  const selected = systems.find((s) => s.id === selectedId);
  const badge = BADGE[selectedId] ?? { label: 'System', color: 'bg-gray-500 text-white' };

  return (
    <div className="flex items-center gap-2">
      <FlaskConical className="w-4 h-4 text-gray-400 shrink-0" />
      <div className="relative">
        <select
          value={selectedId}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          title={selected?.description}
          className="appearance-none pl-2 pr-6 py-1.5 text-sm rounded-lg border border-gray-300 bg-white text-gray-700 cursor-pointer focus:outline-none focus:border-cmu-red disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {systems.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        {/* chevron */}
        <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs">▾</span>
      </div>
      {/* Live badge */}
      <span className={`hidden sm:inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${badge.color}`}>
        {badge.label}
      </span>
      {selected && !selected.streaming && (
        <span className="hidden md:inline text-xs text-gray-400">(no live events)</span>
      )}
    </div>
  );
}
