/**
 * PlanningProgress - Shows detailed planning negotiation progress in chat.
 * Displays rounds, proposals, critiques, and final plan.
 */
'use client';

import { useState, useEffect } from 'react';
import { StreamEvent } from '@/lib/api';

interface SemesterPlan {
  semester: string;
  courses: string[];
  total_units: number;
  notes?: string;
}

interface CoursePlan {
  plan_id?: string;
  program?: string;
  start_semester?: string;
  target_graduation?: string;
  semesters?: SemesterPlan[];
  total_units?: number;
  requirements_met?: string[];
  requirements_pending?: string[];
}

interface AgentCritique {
  agent: string;
  approved: boolean;
  issues: string[];
  suggestions: string[];
}

interface PlanningRound {
  round: number;
  status: 'proposing' | 'critiquing' | 'complete';
  plan?: CoursePlan;
  critiques: AgentCritique[];
  allApproved: boolean;
}

interface PlanningProgressProps {
  events: StreamEvent[];
  isActive: boolean;
  currentPhase: string;
}

export default function PlanningProgress({
  events,
  isActive,
  currentPhase,
}: PlanningProgressProps) {
  const [rounds, setRounds] = useState<PlanningRound[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [finalStatus, setFinalStatus] = useState<string | null>(null);

  // Process events to build rounds
  useEffect(() => {
    const newRounds: PlanningRound[] = [];
    let currentRound: PlanningRound | null = null;

    for (const event of events) {
      const eventType = event.type;
      const data = event.data || {};

      if (eventType === 'planning_session_start') {
        setSessionId((data as { session_id?: string }).session_id || null);
      } else if (eventType === 'planning_round_start') {
        const roundNum = (data as { round?: number }).round || 1;
        currentRound = {
          round: roundNum,
          status: 'proposing',
          critiques: [],
          allApproved: false,
        };
        newRounds.push(currentRound);
      } else if (eventType === 'planning_proposal') {
        if (currentRound) {
          currentRound.plan = (data as { plan?: CoursePlan }).plan;
          currentRound.status = 'critiquing';
        }
      } else if (eventType === 'planning_critique') {
        if (currentRound) {
          currentRound.critiques.push({
            agent: (data as { agent?: string }).agent || 'unknown',
            approved: (data as { approved?: boolean }).approved || false,
            issues: (data as { issues?: string[] }).issues || [],
            suggestions: (data as { suggestions?: string[] }).suggestions || [],
          });
        }
      } else if (eventType === 'planning_round_complete') {
        if (currentRound) {
          currentRound.status = 'complete';
          currentRound.allApproved = (data as { all_approved?: boolean }).all_approved || false;
        }
      } else if (eventType === 'planning_complete') {
        setFinalStatus((data as { status?: string }).status || 'completed');
      }
    }

    setRounds(newRounds);
  }, [events]);

  // Don't show if no planning events
  if (rounds.length === 0 && !isActive) {
    return null;
  }

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 my-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">🗓️</span>
        <h3 className="font-semibold text-purple-800">Collaborative Course Planning</h3>
        {isActive && (
          <span className="ml-auto flex items-center gap-1 text-sm text-purple-600">
            <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
            {currentPhase}
          </span>
        )}
        {finalStatus && (
          <span className={`ml-auto text-sm font-medium ${
            finalStatus === 'completed' ? 'text-green-600' : 'text-yellow-600'
          }`}>
            {finalStatus === 'completed' ? '✅ Consensus Reached' : '⚠️ Max Rounds'}
          </span>
        )}
      </div>

      {/* Rounds */}
      <div className="space-y-3">
        {rounds.map((round) => (
          <RoundCard key={round.round} round={round} isLatest={round.round === rounds.length} />
        ))}
      </div>

      {/* Active indicator */}
      {isActive && rounds.length === 0 && (
        <div className="flex items-center justify-center py-4 text-purple-600">
          <span className="animate-spin mr-2">⏳</span>
          Initializing planning session...
        </div>
      )}
    </div>
  );
}

// Round Card Component
function RoundCard({ round, isLatest }: { round: PlanningRound; isLatest: boolean }) {
  const [expanded, setExpanded] = useState(isLatest);

  const statusIcon = round.status === 'complete'
    ? (round.allApproved ? '✅' : '🔄')
    : round.status === 'critiquing'
    ? '🔍'
    : '📝';

  const statusColor = round.allApproved
    ? 'border-green-300 bg-green-50'
    : round.status === 'complete'
    ? 'border-yellow-300 bg-yellow-50'
    : 'border-purple-300 bg-white';

  return (
    <div className={`border rounded-lg ${statusColor} overflow-hidden`}>
      {/* Round Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 p-3 text-left hover:bg-black/5 transition-colors"
      >
        <span className="text-lg">{statusIcon}</span>
        <span className="font-medium text-gray-800">Round {round.round}</span>
        <span className="text-sm text-gray-500 capitalize">({round.status})</span>

        {/* Critique summary */}
        {round.critiques.length > 0 && (
          <div className="ml-auto flex gap-1">
            {round.critiques.map((c) => (
              <span
                key={c.agent}
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                  c.approved
                    ? 'bg-green-200 text-green-700'
                    : 'bg-yellow-200 text-yellow-700'
                }`}
                title={`${c.agent}: ${c.approved ? 'Approved' : 'Needs revision'}`}
              >
                {c.approved ? '✓' : '!'}
              </span>
            ))}
          </div>
        )}

        <span className={`ml-2 transition-transform ${expanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t p-3 space-y-3">
          {/* Plan Preview */}
          {round.plan && (
            <div className="bg-white rounded-lg p-3 border">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Proposed Plan</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500">Program:</span>{' '}
                  <span className="text-gray-800">{round.plan.program || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-gray-500">Units:</span>{' '}
                  <span className="text-gray-800">{round.plan.total_units || 0}</span>
                </div>
              </div>
              {round.plan.semesters && round.plan.semesters.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {round.plan.semesters.slice(0, 4).map((sem) => (
                    <span
                      key={sem.semester}
                      className="text-xs px-2 py-1 bg-gray-100 rounded"
                    >
                      {sem.semester}: {sem.courses?.length || 0} courses
                    </span>
                  ))}
                  {round.plan.semesters.length > 4 && (
                    <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                      +{round.plan.semesters.length - 4} more
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Critiques */}
          {round.critiques.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">Agent Reviews</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                {round.critiques.map((critique) => (
                  <CritiqueCard key={critique.agent} critique={critique} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Critique Card Component
function CritiqueCard({ critique }: { critique: AgentCritique }) {
  const agentLabel = critique.agent
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div
      className={`p-2 rounded-lg text-sm ${
        critique.approved
          ? 'bg-green-100 border border-green-200'
          : 'bg-yellow-100 border border-yellow-200'
      }`}
    >
      <div className="flex items-center gap-1 mb-1">
        <span>{critique.approved ? '✅' : '⚠️'}</span>
        <span className="font-medium text-gray-800 text-xs">{agentLabel}</span>
      </div>

      {!critique.approved && critique.issues.length > 0 && (
        <div className="text-xs text-yellow-800 space-y-0.5">
          {critique.issues.slice(0, 2).map((issue, i) => (
            <div key={i} className="truncate" title={issue}>• {issue}</div>
          ))}
        </div>
      )}

      {critique.suggestions.length > 0 && (
        <div className="text-xs text-blue-700 mt-1">
          {critique.suggestions.slice(0, 1).map((sug, i) => (
            <div key={i} className="truncate" title={sug}>💡 {sug}</div>
          ))}
        </div>
      )}
    </div>
  );
}
