/**
 * PlanningPanel - Displays the collaborative planning negotiation process.
 * Shows real-time updates as agents propose and critique course plans.
 */
'use client';

import { useState, useEffect, useRef } from 'react';
import {
  planning,
  PlanningStreamCallbacks,
  CoursePlan,
  AgentCritique,
  PlanningSession,
} from '@/lib/api';

interface PlanningPanelProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId?: string;
  initialRequest?: string;
}

interface RoundState {
  roundNumber: number;
  status: 'proposing' | 'critiquing' | 'complete';
  plan?: CoursePlan;
  critiques: AgentCritique[];
  allApproved: boolean;
}

export default function PlanningPanel({
  isOpen,
  onClose,
  conversationId,
  initialRequest,
}: PlanningPanelProps) {
  const [request, setRequest] = useState(initialRequest || '');
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentRound, setCurrentRound] = useState(0);
  const [rounds, setRounds] = useState<RoundState[]>([]);
  const [finalPlan, setFinalPlan] = useState<CoursePlan | null>(null);
  const [status, setStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [activeAgents, setActiveAgents] = useState<string[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new content appears
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [rounds, status]);

  const handleStartPlanning = async () => {
    if (!request.trim()) return;

    setIsRunning(true);
    setError(null);
    setRounds([]);
    setFinalPlan(null);
    setCurrentRound(0);
    setStatus('Starting planning session...');

    const callbacks: PlanningStreamCallbacks = {
      onSessionStart: (id) => {
        setSessionId(id);
        setStatus('Planning session started');
      },

      onRoundStart: (roundNumber) => {
        setCurrentRound(roundNumber);
        setStatus(`Round ${roundNumber}: Planning agent is proposing...`);
        setRounds((prev) => [
          ...prev,
          {
            roundNumber,
            status: 'proposing',
            critiques: [],
            allApproved: false,
          },
        ]);
      },

      onProposing: (agent) => {
        setStatus(`${agent} is generating a plan...`);
      },

      onProposal: (roundNumber, plan) => {
        setRounds((prev) =>
          prev.map((r) =>
            r.roundNumber === roundNumber
              ? { ...r, plan, status: 'critiquing' }
              : r
          )
        );
        setStatus(`Round ${roundNumber}: Agents are reviewing the plan...`);
      },

      onCritiquing: (agents) => {
        setActiveAgents(agents);
        setStatus(`Critiquing in parallel: ${agents.join(', ')}`);
      },

      onCritique: (roundNumber, critique) => {
        setRounds((prev) =>
          prev.map((r) =>
            r.roundNumber === roundNumber
              ? { ...r, critiques: [...r.critiques, critique] }
              : r
          )
        );
      },

      onRoundComplete: (roundNumber, allApproved) => {
        setRounds((prev) =>
          prev.map((r) =>
            r.roundNumber === roundNumber
              ? { ...r, status: 'complete', allApproved }
              : r
          )
        );
        setActiveAgents([]);

        if (allApproved) {
          setStatus(`Round ${roundNumber}: All agents approved!`);
        } else {
          setStatus(`Round ${roundNumber}: Revisions needed, continuing...`);
        }
      },

      onComplete: (session) => {
        setIsRunning(false);
        setFinalPlan(session.final_plan || null);
        setStatus(
          session.status === 'completed'
            ? 'Planning complete - consensus reached!'
            : 'Planning complete - max rounds reached'
        );
      },

      onError: (errorMsg) => {
        setIsRunning(false);
        setError(errorMsg);
        setStatus('Planning failed');
      },
    };

    try {
      await planning.startSession(request, conversationId, callbacks);
    } catch (err) {
      setIsRunning(false);
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleApprove = async () => {
    if (!sessionId) return;

    try {
      await planning.approveSession(sessionId);
      setStatus('Plan approved and saved!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve plan');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">
            Collaborative Course Planning
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col p-4 gap-4">
          {/* Input */}
          {!isRunning && !finalPlan && (
            <div className="flex gap-2">
              <input
                type="text"
                value={request}
                onChange={(e) => setRequest(e.target.value)}
                placeholder="Describe your course planning request..."
                className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2 border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={handleStartPlanning}
                disabled={!request.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Start Planning
              </button>
            </div>
          )}

          {/* Status */}
          <div className="text-sm text-gray-400">
            {status}
            {isRunning && (
              <span className="ml-2 inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300">
              {error}
            </div>
          )}

          {/* Rounds */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto space-y-4 pr-2"
          >
            {rounds.map((round) => (
              <RoundCard
                key={round.roundNumber}
                round={round}
                isActive={round.roundNumber === currentRound && isRunning}
                activeAgents={
                  round.roundNumber === currentRound ? activeAgents : []
                }
              />
            ))}

            {/* Final Plan */}
            {finalPlan && (
              <div className="bg-green-900/20 border border-green-700 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-green-400 mb-3">
                  Final Course Plan
                </h3>
                <PlanDisplay plan={finalPlan} />
                <button
                  onClick={handleApprove}
                  className="mt-4 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Approve & Save Plan
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Sub-component: Round Card
function RoundCard({
  round,
  isActive,
  activeAgents,
}: {
  round: RoundState;
  isActive: boolean;
  activeAgents: string[];
}) {
  const statusIcon =
    round.status === 'complete'
      ? round.allApproved
        ? '✅'
        : '🔄'
      : round.status === 'critiquing'
      ? '🔍'
      : '📝';

  return (
    <div
      className={`border rounded-lg p-4 ${
        isActive
          ? 'border-blue-500 bg-blue-900/20'
          : round.allApproved
          ? 'border-green-700 bg-green-900/10'
          : 'border-gray-700 bg-gray-800/50'
      }`}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{statusIcon}</span>
        <h3 className="font-semibold text-white">Round {round.roundNumber}</h3>
        <span className="text-sm text-gray-400 capitalize">
          ({round.status})
        </span>
      </div>

      {/* Proposed Plan */}
      {round.plan && (
        <div className="mb-3 bg-blue-900/30 border border-blue-600 rounded-lg p-3">
          <h4 className="text-sm font-semibold text-blue-300 mb-2 flex items-center gap-2">
            📋 Planning Agent's Proposal:
          </h4>
          <PlanDisplay plan={round.plan} compact />
        </div>
      )}

      {/* Show placeholder if plan is being generated */}
      {round.status === 'proposing' && !round.plan && (
        <div className="mb-3 bg-blue-900/20 border border-blue-700 rounded-lg p-3 animate-pulse">
          <h4 className="text-sm font-medium text-blue-400">
            ⏳ Planning Agent is generating a plan...
          </h4>
        </div>
      )}

      {/* Critiques */}
      {round.critiques.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-300">Agent Reviews:</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {round.critiques.map((critique) => (
              <CritiqueCard
                key={critique.agent_name}
                critique={critique}
                isActive={activeAgents.includes(critique.agent_name)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Active agents indicator */}
      {activeAgents.length > 0 && round.status === 'critiquing' && (
        <div className="mt-2 flex gap-2">
          {activeAgents.map((agent) => (
            <span
              key={agent}
              className="text-xs px-2 py-1 bg-blue-800 text-blue-200 rounded animate-pulse"
            >
              {agent.replace('_', ' ')}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// Sub-component: Critique Card
function CritiqueCard({
  critique,
  isActive,
}: {
  critique: AgentCritique;
  isActive: boolean;
}) {
  const agentLabel = critique.agent_name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div
      className={`p-3 rounded-lg ${
        critique.approved
          ? 'bg-green-900/30 border border-green-700'
          : 'bg-yellow-900/30 border border-yellow-700'
      } ${isActive ? 'animate-pulse' : ''}`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span>{critique.approved ? '✅' : '⚠️'}</span>
        <span className="text-sm font-medium text-white">{agentLabel}</span>
      </div>

      {critique.issues.length > 0 && (
        <div className="text-xs text-yellow-300 mt-1">
          {critique.issues.slice(0, 2).map((issue, i) => (
            <div key={i}>• {issue}</div>
          ))}
        </div>
      )}

      {critique.suggestions.length > 0 && (
        <div className="text-xs text-blue-300 mt-1">
          {critique.suggestions.slice(0, 2).map((sug, i) => (
            <div key={i}>💡 {sug}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// Sub-component: Plan Display
function PlanDisplay({
  plan,
  compact = false,
}: {
  plan: CoursePlan;
  compact?: boolean;
}) {
  // Safety checks for potentially undefined data
  const semesters = plan.semesters || [];
  const program = plan.program || 'Not specified';
  const startSemester = plan.start_semester || 'TBD';
  const targetGraduation = plan.target_graduation || 'TBD';
  const totalUnits = plan.total_units || 0;

  if (compact) {
    return (
      <div className="text-sm text-gray-300 space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-gray-500">Program:</span>{' '}
            <span className="text-white font-medium">{program}</span>
          </div>
          <div>
            <span className="text-gray-500">Units:</span>{' '}
            <span className="text-white font-medium">{totalUnits}</span>
          </div>
        </div>
        <div>
          <span className="text-gray-500">Timeline:</span>{' '}
          <span className="text-white">{startSemester} → {targetGraduation}</span>
        </div>
        {semesters.length > 0 && (
          <div className="mt-2">
            <span className="text-gray-500 text-xs">Semester Overview:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {semesters.slice(0, 4).map((sem) => (
                <span
                  key={sem.semester}
                  className="text-xs px-2 py-1 bg-gray-700 rounded text-white"
                >
                  {sem.semester}: {sem.courses?.length || 0} courses ({sem.total_units || 0}u)
                </span>
              ))}
              {semesters.length > 4 && (
                <span className="text-xs px-2 py-1 bg-gray-600 rounded">
                  +{semesters.length - 4} more semesters
                </span>
              )}
            </div>
          </div>
        )}
        {semesters.length === 0 && (
          <div className="text-yellow-400 text-xs mt-1">
            ⚠️ No semester details available
          </div>
        )}
      </div>
    );
  }

  const requirementsPending = plan.requirements_pending || [];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Program:</span>{' '}
          <span className="text-white font-medium">{program}</span>
        </div>
        <div>
          <span className="text-gray-500">Total Units:</span>{' '}
          <span className="text-white font-medium">{totalUnits}</span>
        </div>
        <div>
          <span className="text-gray-500">Start:</span>{' '}
          <span className="text-white">{startSemester}</span>
        </div>
        <div>
          <span className="text-gray-500">Graduation:</span>{' '}
          <span className="text-white">{targetGraduation}</span>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-medium text-gray-300">Semester Schedule:</h4>
        {semesters.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {semesters.map((sem) => (
              <div
                key={sem.semester}
                className="bg-gray-800 rounded-lg p-3 text-sm"
              >
                <div className="font-medium text-white mb-1">
                  {sem.semester}
                  <span className="text-gray-500 ml-2">
                    ({sem.total_units || 0} units)
                  </span>
                </div>
                <div className="text-gray-300">
                  {(sem.courses || []).join(', ') || 'No courses listed'}
                </div>
                {sem.notes && (
                  <div className="text-xs text-gray-500 mt-1">{sem.notes}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-yellow-400 text-sm">
            ⚠️ No semester schedule available
          </div>
        )}
      </div>

      {requirementsPending.length > 0 && (
        <div className="text-sm">
          <span className="text-gray-500">Pending Requirements:</span>{' '}
          <span className="text-yellow-400">
            {requirementsPending.join(', ')}
          </span>
        </div>
      )}
    </div>
  );
}
