/**
 * API client for the Multi-Agent Advising backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
export interface User {
  id: string;
  email: string;
  name: string;
  profile?: UserProfile;
}

export interface CourseTaken {
  code: string;
  name?: string;
  grade: string;
  semester: string;
  units?: number;
}

export interface UserProfile {
  major?: string;
  year?: string;  // First Year, Sophomore, Junior, Senior
  minors?: string[];
  concentration?: string;
  gpa?: number;
  expected_graduation?: string;
  completed_courses?: string[];
  courses_taken?: CourseTaken[];
  interests?: string[];
  career_goals?: string[];
}

export interface Conversation {
  _id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: Message[];
}

export interface Message {
  _id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: {
    agents_used?: string[];
  };
}

export interface ChatResponse {
  conversation_id: string;
  response: string;
  agents_used: string[];
  workflow_details?: {
    conflicts: number;
    risks: number;
  };
}

export interface SystemInfo {
  id: string;
  name: string;
  description: string;
  streaming: boolean;
  ablation_variable: string;
}

// Token management
let authToken: string | null = null;

export function setToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
}

export function getToken(): string | null {
  if (!authToken && typeof window !== 'undefined') {
    authToken = localStorage.getItem('auth_token');
  }
  return authToken;
}

// API helper
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth API
export const auth = {
  async register(email: string, name: string, password: string): Promise<{ user: User; token: string }> {
    const result = await apiFetch<{ user: User; token: string }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, name, password }),
    });
    setToken(result.token);
    return result;
  },

  async login(email: string, password: string): Promise<{ user: User; token: string }> {
    const result = await apiFetch<{ user: User; token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(result.token);
    return result;
  },

  async me(): Promise<User> {
    return apiFetch<User>('/api/auth/me');
  },

  async updateProfile(profile: UserProfile): Promise<{ success: boolean; profile: UserProfile }> {
    return apiFetch('/api/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  },

  logout() {
    setToken(null);
  },
};

// Conversations API
export const conversations = {
  async list(): Promise<{ conversations: Conversation[] }> {
    return apiFetch('/api/conversations');
  },

  async create(title?: string): Promise<Conversation> {
    return apiFetch('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  },

  async get(id: string): Promise<Conversation> {
    return apiFetch(`/api/conversations/${id}`);
  },

  async delete(id: string): Promise<{ success: boolean }> {
    return apiFetch(`/api/conversations/${id}`, {
      method: 'DELETE',
    });
  },
};

// Streaming event types
export interface StreamEvent {
  type: string;
  agent?: string;
  phase?: string;
  message?: string;
  timestamp?: string;
  data?: Record<string, unknown>;
}

export interface WorkflowDetails {
  agents_used: string[];
  agent_details: Record<string, {
    answer: string;
    confidence: number;
    risks: Array<{ type: string; severity: string; description: string }>;
    relevant_policies: string[];
  }>;
  execution_stats?: {
    execution_mode?: string;
    total_execution_time?: number;
    parallel_speedup?: number;
  };
  phase_timing?: Record<string, number>;
  stream_events?: StreamEvent[];
}

export interface StreamCallbacks {
  onEvent?: (event: StreamEvent) => void;
  onAnswer?: (answer: string, conversationId: string, workflowDetails?: WorkflowDetails) => void;
  onError?: (error: string) => void;
  onComplete?: () => void;
}

// Systems API
export const systems = {
  async list(): Promise<{ systems: SystemInfo[] }> {
    return apiFetch('/api/systems');
  },
};

// Chat API
export const chat = {
  async send(message: string, conversationId?: string, system: string = 'multi_agent'): Promise<ChatResponse> {
    return apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        system,
      }),
    });
  },

  /**
   * Send a message with streaming updates.
   * Returns real-time events as the multi-agent workflow progresses.
   */
  async sendStreaming(
    message: string,
    conversationId: string | undefined,
    callbacks: StreamCallbacks,
    system: string = 'multi_agent',
    signal?: AbortSignal
  ): Promise<void> {
    const token = getToken();

    const response = await fetch(`${API_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        system,
      }),
      signal,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      callbacks.onError?.(error.detail || `HTTP ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      callbacks.onError?.('No response body');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data.trim()) {
              try {
                const event = JSON.parse(data) as StreamEvent;

                // Handle different event types
                if (event.type === 'answer') {
                  const answerData = event.data as {
                    content: string;
                    conversation_id: string;
                    agents_used?: string[];
                    agent_details?: Record<string, unknown>;
                    execution_stats?: Record<string, unknown>;
                    phase_timing?: Record<string, number>;
                  };
                  const workflowDetails: WorkflowDetails = {
                    agents_used: answerData.agents_used || [],
                    agent_details: (answerData.agent_details || {}) as WorkflowDetails['agent_details'],
                    execution_stats: answerData.execution_stats as WorkflowDetails['execution_stats'],
                    phase_timing: answerData.phase_timing,
                  };
                  callbacks.onAnswer?.(answerData.content, answerData.conversation_id, workflowDetails);
                } else if (event.type === 'error') {
                  const errorData = event.data as { message: string };
                  callbacks.onError?.(errorData.message);
                } else if (event.type === 'done') {
                  callbacks.onComplete?.();
                } else {
                  // All other events (agent status, coordinator, etc.)
                  callbacks.onEvent?.(event);
                }
              } catch (e) {
                console.error('Failed to parse SSE event:', e, data);
              }
            }
          }
        }
      }

      // Handle any remaining data in buffer
      if (buffer.startsWith('data: ')) {
        const data = buffer.slice(6);
        if (data.trim()) {
          try {
            const event = JSON.parse(data) as StreamEvent;
            if (event.type === 'done') {
              callbacks.onComplete?.();
            }
          } catch {
            // Ignore incomplete data
          }
        }
      }

    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        callbacks.onComplete?.();
      } else {
        callbacks.onError?.(error instanceof Error ? error.message : 'Stream error');
      }
    } finally {
      reader.releaseLock();
    }
  },
};

// Health check
export async function checkHealth(): Promise<{ status: string; database: string }> {
  const response = await fetch(`${API_URL}/api/health`);
  return response.json();
}

// =============================================================================
// Planning Mode Types and API
// =============================================================================

export interface SemesterPlan {
  semester: string;
  courses: string[];
  total_units: number;
  notes?: string;
}

export interface CoursePlan {
  plan_id: string;
  student_id: string;
  program: string;
  start_semester: string;
  target_graduation: string;
  semesters: SemesterPlan[];
  total_units: number;
  requirements_met: string[];
  requirements_pending: string[];
}

export interface AgentCritique {
  agent_name: string;
  approved: boolean;
  issues: string[];
  suggestions: string[];
  confidence: number;
  details?: Record<string, unknown>;
}

export interface PlanningRound {
  round_number: number;
  proposed_plan: CoursePlan;
  critiques: AgentCritique[];
  all_approved: boolean;
  revision_notes: string;
  timestamp: string;
}

export interface PlanningSession {
  session_id: string;
  user_id: string;
  request: string;
  status: string;
  total_rounds: number;
  rounds: PlanningRound[];
  final_plan?: CoursePlan;
  created_at?: string;
}

export interface PlanningStreamEvent {
  type: string;
  data: Record<string, unknown>;
}

export interface PlanningStreamCallbacks {
  onSessionStart?: (sessionId: string) => void;
  onRoundStart?: (roundNumber: number) => void;
  onProposing?: (agentName: string) => void;
  onProposal?: (roundNumber: number, plan: CoursePlan) => void;
  onCritiquing?: (agents: string[]) => void;
  onCritique?: (roundNumber: number, critique: AgentCritique) => void;
  onRoundComplete?: (roundNumber: number, allApproved: boolean) => void;
  onComplete?: (session: PlanningSession) => void;
  onError?: (error: string) => void;
}

// Planning API
export const planning = {
  /**
   * Start a collaborative planning session with SSE streaming.
   */
  async startSession(
    request: string,
    conversationId: string | undefined,
    callbacks: PlanningStreamCallbacks
  ): Promise<void> {
    const token = getToken();

    const response = await fetch(`${API_URL}/api/planning/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        request,
        conversation_id: conversationId,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      callbacks.onError?.(error.detail || `HTTP ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      callbacks.onError?.('No response body');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data.trim()) {
              try {
                const event = JSON.parse(data) as PlanningStreamEvent;
                this.handlePlanningEvent(event, callbacks);
              } catch (e) {
                console.error('Failed to parse planning SSE event:', e, data);
              }
            }
          }
        }
      }
    } catch (error) {
      callbacks.onError?.(error instanceof Error ? error.message : 'Stream error');
    } finally {
      reader.releaseLock();
    }
  },

  handlePlanningEvent(event: PlanningStreamEvent, callbacks: PlanningStreamCallbacks) {
    const data = event.data || event;

    switch (event.type) {
      case 'planning_session_start':
        callbacks.onSessionStart?.((data as { session_id: string }).session_id);
        break;

      case 'planning_round_start':
        callbacks.onRoundStart?.((data as { round: number }).round);
        break;

      case 'planning_proposing':
        callbacks.onProposing?.((data as { agent: string }).agent);
        break;

      case 'planning_proposal':
        callbacks.onProposal?.(
          (data as { round: number }).round,
          (data as { plan: CoursePlan }).plan
        );
        break;

      case 'planning_critiquing':
        callbacks.onCritiquing?.((data as { agents: string[] }).agents);
        break;

      case 'planning_critique':
        callbacks.onCritique?.(
          (data as { round: number }).round,
          {
            agent_name: (data as { agent: string }).agent,
            approved: (data as { approved: boolean }).approved,
            issues: (data as { issues: string[] }).issues || [],
            suggestions: (data as { suggestions: string[] }).suggestions || [],
            confidence: 0.8,
          }
        );
        break;

      case 'planning_round_complete':
        callbacks.onRoundComplete?.(
          (data as { round: number }).round,
          (data as { all_approved: boolean }).all_approved
        );
        break;

      case 'planning_complete':
        callbacks.onComplete?.({
          session_id: (data as { session_id: string }).session_id,
          user_id: '',
          request: '',
          status: (data as { status: string }).status,
          total_rounds: (data as { total_rounds: number }).total_rounds,
          rounds: [],
          final_plan: (data as { final_plan?: CoursePlan }).final_plan,
        });
        break;

      case 'error':
        callbacks.onError?.((data as { message: string }).message);
        break;

      case 'done':
        // Session complete
        break;
    }
  },

  /**
   * Get a specific planning session.
   */
  async getSession(sessionId: string): Promise<PlanningSession> {
    return apiFetch(`/api/planning/${sessionId}`);
  },

  /**
   * Get user's planning history.
   */
  async getHistory(limit: number = 10): Promise<{ sessions: PlanningSession[] }> {
    return apiFetch(`/api/planning/user/history?limit=${limit}`);
  },

  /**
   * Approve and save the final plan.
   */
  async approveSession(sessionId: string): Promise<{ status: string; plan: CoursePlan }> {
    return apiFetch(`/api/planning/${sessionId}/approve`, {
      method: 'POST',
    });
  },
};
