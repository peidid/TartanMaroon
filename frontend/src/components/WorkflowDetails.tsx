'use client';

/**
 * Post-answer transparency panel: a collapsible record of which tools the
 * orchestrator called and what they returned, attached under each assistant
 * message. Props are kept compatible with the page (agentsUsed / streamEvents);
 * the legacy multi-agent fields are accepted but unused.
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, Wrench, CheckCircle } from 'lucide-react';

interface StreamEvent {
  type: string;
  message?: string;
  data?: Record<string, unknown>;
}

interface WorkflowDetailsProps {
  agentsUsed?: string[];
  agentDetails?: Record<string, unknown>;
  executionStats?: Record<string, unknown>;
  phaseTiming?: Record<string, number>;
  streamEvents?: StreamEvent[];
}

export default function WorkflowDetails({ agentsUsed = [], streamEvents = [] }: WorkflowDetailsProps) {
  const [open, setOpen] = useState(true);

  const calls: { tool: string; args?: Record<string, unknown>; result?: string }[] = [];
  for (const ev of streamEvents) {
    if (ev.type === 'tool_call') {
      calls.push({ tool: (ev.data?.tool as string) || 'tool', args: ev.data?.args as Record<string, unknown> });
    } else if (ev.type === 'tool_result') {
      const tool = ev.data?.tool as string | undefined;
      const target = [...calls].reverse().find((c) => c.result === undefined && (!tool || c.tool === tool));
      if (target) target.result = (ev.data?.result as string) ?? '';
    }
  }

  const toolNames = agentsUsed.length ? agentsUsed : Array.from(new Set(calls.map((c) => c.tool)));
  if (!toolNames.length && !calls.length) return null;

  return (
    <div className="mt-2 ml-11 max-w-3xl">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        <Wrench className="w-3.5 h-3.5" />
        How I answered this {toolNames.length ? `· ${toolNames.length} tool${toolNames.length > 1 ? 's' : ''}` : ''}
      </button>

      {open && (
        <div className="mt-2 rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
          {calls.length === 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {toolNames.map((t) => (
                <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-white border border-gray-200 text-gray-600">{t}</span>
              ))}
            </div>
          ) : (
            calls.map((c, i) => (
              <div key={i} className="text-xs">
                <div className="flex items-center gap-1.5 text-gray-700 font-medium">
                  <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                  <code>{c.tool}</code>
                  {c.args && Object.keys(c.args).length > 0 && (
                    <code className="text-gray-400 font-normal">
                      ({Object.entries(c.args).map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`).join(', ')})
                    </code>
                  )}
                </div>
                {c.result && (
                  <pre className="mt-1 ml-5 text-[11px] text-gray-500 whitespace-pre-wrap break-words max-h-64 overflow-y-auto font-mono">
                    {c.result}
                  </pre>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
