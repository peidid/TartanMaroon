'use client';

/**
 * Live "reasoning trace" for the transparent orchestrator.
 *
 * Renders the streamed working process: each tool the orchestrator calls
 * (with its arguments), whether it has returned yet (+ a result preview), and
 * the answer as it is drafted token-by-token. Driven entirely by the SSE
 * `streamEvents` the page collects (types: tool_call | tool_result | thinking
 * | token).
 */

import { useState } from 'react';
import {
  Brain, Loader2, CheckCircle, ChevronDown, ChevronRight, Wrench,
  Search, BookOpen, GraduationCap, Network, ShieldCheck, CalendarDays, User,
} from 'lucide-react';

interface StreamEvent {
  type: string;
  agent?: string;
  phase?: string;
  message?: string;
  data?: Record<string, unknown>;
}

interface AgentStatusProps {
  activeAgents?: string[];
  completedAgents?: string[];
  streamEvents?: StreamEvent[];
  currentPhase?: string;
}

const TOOL_META: Record<string, { label: string; Icon: typeof Wrench }> = {
  my_profile: { label: 'Reading your profile', Icon: User },
  find_courses: { label: 'Searching the catalog', Icon: Search },
  course_details: { label: 'Reading course details', Icon: BookOpen },
  prerequisites: { label: 'Tracing prerequisites', Icon: Network },
  check_eligibility: { label: 'Checking eligibility', Icon: CheckCircle },
  courses_unlocked_by: { label: 'Finding unlocked courses', Icon: Network },
  course_offerings: { label: 'Looking up offerings', Icon: CalendarDays },
  is_offered: { label: 'Checking the schedule', Icon: CalendarDays },
  list_semesters: { label: 'Listing semesters', Icon: CalendarDays },
  list_programs: { label: 'Listing programs', Icon: GraduationCap },
  program_requirements: { label: 'Reading requirements', Icon: GraduationCap },
  degree_progress: { label: 'Computing degree progress', Icon: GraduationCap },
  search_handbook: { label: 'Searching policy & advising docs', Icon: ShieldCheck },
};

function metaFor(tool?: string) {
  return (tool && TOOL_META[tool]) || { label: tool || 'Working', Icon: Wrench };
}

function argSummary(args?: Record<string, unknown>): string {
  if (!args) return '';
  return Object.entries(args)
    .filter(([, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ');
}

interface ToolCall {
  tool: string;
  args?: Record<string, unknown>;
  result?: string;
}

export default function AgentStatus({ streamEvents = [], currentPhase = '' }: AgentStatusProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  // Pair tool_call events with the next matching tool_result (in order).
  const calls: ToolCall[] = [];
  for (const ev of streamEvents) {
    if (ev.type === 'tool_call') {
      calls.push({ tool: (ev.data?.tool as string) || ev.message || 'tool', args: ev.data?.args as Record<string, unknown> });
    } else if (ev.type === 'tool_result') {
      const tool = ev.data?.tool as string | undefined;
      const target = [...calls].reverse().find((c) => c.result === undefined && (!tool || c.tool === tool));
      if (target) target.result = (ev.data?.result as string) ?? '';
    }
  }

  // Accumulate streamed answer tokens for a live preview.
  const draft = streamEvents
    .filter((e) => e.type === 'token')
    .map((e) => (e.data?.text as string) || '')
    .join('');

  return (
    <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200 p-4 mb-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3 pb-3 border-b border-gray-200">
        <div className="relative">
          <Brain className="w-5 h-5 text-cmu-red" />
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-cmu-red rounded-full animate-ping" />
        </div>
        <span className="text-sm font-medium text-gray-700">
          {currentPhase || 'Thinking through your question…'}
        </span>
      </div>

      {/* Tool-call timeline */}
      <div className="space-y-2">
        {calls.map((call, i) => {
          const { label, Icon } = metaFor(call.tool);
          const done = call.result !== undefined;
          // Results are shown by default once a call returns (transparency first);
          // the chevron lets the user collapse a noisy one.
          const isOpen = done && (expanded[i] ?? true);
          const args = argSummary(call.args);
          return (
            <div key={i} className="rounded-lg border border-gray-200 bg-white/70 overflow-hidden">
              <button
                onClick={() => done && setExpanded((p) => ({ ...p, [i]: !(p[i] ?? true) }))}
                className={`w-full px-3 py-2 flex items-start gap-2 text-left ${done ? 'hover:bg-gray-50 cursor-pointer' : 'cursor-default'}`}
                disabled={!done}
              >
                <span className="mt-0.5 w-5 h-5 shrink-0 rounded-full bg-cmu-red/10 text-cmu-red text-[11px] font-semibold flex items-center justify-center">
                  {i + 1}
                </span>
                <Icon className="w-4 h-4 text-cmu-red shrink-0 mt-0.5" />
                <span className="flex-1 min-w-0">
                  <span className="text-sm text-gray-800 font-medium">{label}</span>
                  <code className="ml-1.5 text-[11px] text-gray-400">{call.tool}</code>
                  {args && (
                    <span className="block text-xs text-gray-500 font-mono break-words mt-0.5">{args}</span>
                  )}
                </span>
                <span className="shrink-0 mt-0.5">
                  {done ? <CheckCircle className="w-4 h-4 text-green-500" /> : <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />}
                </span>
                {done && (isOpen
                  ? <ChevronDown className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                  : <ChevronRight className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />)}
              </button>
              {isOpen && done && (
                <div className="px-3 pb-3 border-t border-gray-100 bg-white">
                  <div className="mt-2 text-[11px] uppercase tracking-wide text-gray-400 font-medium">Result</div>
                  <pre className="mt-1 text-xs text-gray-600 whitespace-pre-wrap break-words max-h-80 overflow-y-auto font-mono">
                    {call.result || '(no output)'}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Live answer draft */}
      {draft && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div className="text-xs font-medium text-gray-500 mb-1">Drafting answer…</div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {draft}
            <span className="inline-block w-1.5 h-4 bg-cmu-red/70 animate-pulse align-middle ml-0.5" />
          </p>
        </div>
      )}

      {calls.length === 0 && !draft && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" /> Planning the approach…
        </div>
      )}
    </div>
  );
}
