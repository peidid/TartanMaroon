'use client';

import { useState, useEffect, useRef } from 'react';
import { Bot, GraduationCap } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import ChatMessage from '@/components/ChatMessage';
import ChatInput from '@/components/ChatInput';
import AgentStatus from '@/components/AgentStatus';
import WorkflowDetails from '@/components/WorkflowDetails';
import AuthModal from '@/components/AuthModal';
import ProfileModal from '@/components/ProfileModal';
import SystemSelector from '@/components/SystemSelector';
import {
  auth,
  conversations,
  chat,
  systems as systemsApi,
  getToken,
  User,
  Conversation,
  Message,
  UserProfile,
  StreamEvent,
  SystemInfo,
  WorkflowDetails as WorkflowDetailsType,
} from '@/lib/api';

export default function Home() {
  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [showAuth, setShowAuth] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [loading, setLoading] = useState(true);

  // Chat state
  const [conversationList, setConversationList] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [currentPhase, setCurrentPhase] = useState<string>('');
  const [messageWorkflows, setMessageWorkflows] = useState<Record<string, WorkflowDetailsType>>({});

  // System selector state (for ablation study)
  const [availableSystems, setAvailableSystems] = useState<SystemInfo[]>([]);
  const [selectedSystem, setSelectedSystem] = useState<string>('advisor');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamEventsRef = useRef<StreamEvent[]>([]);
  // AbortController for cancelling in-flight generation
  const abortControllerRef = useRef<AbortController | null>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check auth on load and fetch available systems
  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const userData = await auth.me();
          setUser(userData);
          await loadConversations();
        } catch {
          auth.logout();
        }
      }
      setLoading(false);
    };

    const loadSystems = async () => {
      try {
        const result = await systemsApi.list();
        if (result.systems?.length) {
          setAvailableSystems(result.systems);
        }
      } catch {
        // Backend may not have /api/systems yet — degrade gracefully
      }
    };

    checkAuth();
    loadSystems();
  }, []);

  // Load conversations
  const loadConversations = async () => {
    try {
      const result = await conversations.list();
      setConversationList(result.conversations);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  // Load a conversation
  const loadConversation = async (id: string) => {
    try {
      const conv = await conversations.get(id);
      setCurrentConversation(conv);
      setMessages(conv.messages || []);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  };

  // Handle auth success
  const handleAuthSuccess = async () => {
    setShowAuth(false);
    const userData = await auth.me();
    setUser(userData);
    await loadConversations();
  };

  // Handle new conversation
  const handleNewConversation = () => {
    setCurrentConversation(null);
    setMessages([]);
    setActiveAgents([]);
    setCompletedAgents([]);
  };

  // Handle select conversation
  const handleSelectConversation = async (id: string) => {
    await loadConversation(id);
    setActiveAgents([]);
    setCompletedAgents([]);
  };

  // Handle delete conversation
  const handleDeleteConversation = async (id: string) => {
    try {
      await conversations.delete(id);
      setConversationList((prev) => prev.filter((c) => c._id !== id));
      if (currentConversation?._id === id) {
        handleNewConversation();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  // Handle logout
  const handleLogout = () => {
    auth.logout();
    setUser(null);
    setConversationList([]);
    handleNewConversation();
  };

  // Handle profile save
  const handleProfileSave = (profile: UserProfile) => {
    if (user) {
      setUser({ ...user, profile });
    }
  };

  // Stop current generation
  const handleStop = () => {
    abortControllerRef.current?.abort();
  };

  // Handle send message with streaming
  const handleSendMessage = async (message: string) => {
    if (!user) {
      setShowAuth(true);
      return;
    }

    // Add user message immediately
    const userMessage: Message = {
      _id: `temp-${Date.now()}`,
      conversation_id: currentConversation?._id || '',
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Reset streaming state
    setSending(true);
    setActiveAgents([]);
    setCompletedAgents([]);
    setStreamEvents([]);
    streamEventsRef.current = [];
    setCurrentPhase('starting');

    // Create a fresh AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      // Use streaming endpoint for real-time updates
      await chat.sendStreaming(
        message,
        currentConversation?._id,
        {
          onEvent: (event: StreamEvent) => {
            // Add event to stream for display
            setStreamEvents((prev) => {
              const updated = [...prev, event];
              streamEventsRef.current = updated;
              return updated;
            });

            // Update phase indicator
            if (event.message) {
              setCurrentPhase(event.message);
            }

            // Track agent status
            if (event.type === 'agent_start' && event.agent) {
              setActiveAgents((prev) => [...prev, event.agent!]);
            } else if (event.type === 'agent_complete' && event.agent) {
              setActiveAgents((prev) => prev.filter((a) => a !== event.agent));
              setCompletedAgents((prev) => [...prev, event.agent!]);
            } else if (event.type === 'coordinator_routing') {
              const agents = (event.data?.agents as string[]) || [];
              setActiveAgents(agents);
            } else if (event.type === 'coordinator_evaluation') {
              const evalData = event.data as {
                round: number;
                sufficient: boolean;
                quality_score: number;
                reasoning: string;
              };
              if (evalData.sufficient) {
                setCurrentPhase(`Quality: ${evalData.quality_score}/100 - Ready for synthesis`);
              } else {
                setCurrentPhase(`Evaluation ${evalData.round}/3: Score ${evalData.quality_score}/100 - Need more info`);
              }
            } else if (event.type === 'agent_rerun_start') {
              const agentsToRerun = (event.data?.agents as string[]) || [];
              setCurrentPhase(`Re-running ${agentsToRerun.length} agent(s) with enhanced retrieval...`);
              setActiveAgents(agentsToRerun);
            } else if (event.type === 'agent_rerun_complete' && event.agent) {
              setActiveAgents((prev) => prev.filter((a) => a !== event.agent));
            } else if (event.type === 'synthesis_start') {
              setCurrentPhase('Synthesizing final answer...');
            }
          },
          onAnswer: async (answer: string, conversationId: string, workflowDetails?: WorkflowDetailsType) => {
            const messageId = `temp-${Date.now()}-response`;
            const assistantMessage: Message = {
              _id: messageId,
              conversation_id: conversationId,
              role: 'assistant',
              content: answer,
              timestamp: new Date().toISOString(),
              metadata: { agents_used: workflowDetails?.agents_used || completedAgents },
            };
            setMessages((prev) => [...prev, assistantMessage]);

            if (workflowDetails) {
              setMessageWorkflows((prev) => ({
                ...prev,
                [messageId]: {
                  ...workflowDetails,
                  stream_events: streamEventsRef.current,
                },
              }));
            }

            if (!currentConversation) {
              try {
                const conv = await conversations.get(conversationId);
                setCurrentConversation(conv);
                await loadConversations();
              } catch (e) {
                console.error('Failed to load conversation:', e);
              }
            }
          },
          onError: (error: string) => {
            console.error('Streaming error:', error);
            const errorMessage: Message = {
              _id: `temp-${Date.now()}-error`,
              conversation_id: currentConversation?._id || '',
              role: 'assistant',
              content: `Sorry, I encountered an error: ${error}`,
              timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMessage]);
          },
          onComplete: () => {
            setCurrentPhase('');
          },
        },
        selectedSystem,
        abortController.signal
      );
    } catch (err) {
      // AbortError = user clicked stop — not an error worth showing
      if (err instanceof Error && err.name === 'AbortError') {
        // silent — the finally block handles cleanup
      } else {
        console.error('Failed to send message:', err);
        const errorMessage: Message = {
          _id: `temp-${Date.now()}-error`,
          conversation_id: currentConversation?._id || '',
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } finally {
      abortControllerRef.current = null;
      setSending(false);
      setActiveAgents([]);
      setCurrentPhase('');
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Bot className="w-12 h-12 text-cmu-red mx-auto animate-pulse" />
          <p className="mt-2 text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex">
      {/* Sidebar */}
      <Sidebar
        user={user}
        conversations={conversationList}
        currentConversationId={currentConversation?._id || null}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onLogout={handleLogout}
        onOpenProfile={() => setShowProfile(true)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Header */}
        <header className="border-b px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-10 h-10 bg-cmu-red rounded-lg flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-gray-900">TartanMaroon</h1>
              <p className="text-sm text-gray-500">CMU-Q Multi-Agent System for Academic Advising</p>
            </div>
          </div>

          {/* System selector (ablation study) */}
          {availableSystems.length > 0 && (
            <SystemSelector
              systems={availableSystems}
              selectedId={selectedSystem}
              onChange={setSelectedSystem}
              disabled={sending}
            />
          )}

          <div className="flex items-center gap-3 shrink-0">
            {!user && (
              <button
                onClick={() => setShowAuth(true)}
                className="px-4 py-2 bg-cmu-red text-white rounded-lg hover:bg-cmu-darkred transition-colors"
              >
                Sign In
              </button>
            )}
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-gray-700 mb-2">
                  Welcome to TartanMaroon
                </h2>
                <p className="text-gray-500 max-w-md mx-auto">
                  I&apos;m a verified advising assistant. I plan, call tools over the real
                  course/requirement data, and show my work as I go — ask about course
                  requirements, prerequisites, schedules, policies, or degree progress.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {[
                    'Can I add a CS minor?',
                    'What courses should I take next semester?',
                    'How do I graduate in 4 years?',
                    'What are the IS degree requirements?',
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => handleSendMessage(suggestion)}
                      className="px-4 py-2 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <div key={msg._id}>
                    <ChatMessage message={msg} />
                    {msg.role === 'assistant' && messageWorkflows[msg._id] && (
                      <WorkflowDetails
                        agentsUsed={messageWorkflows[msg._id].agents_used}
                        agentDetails={messageWorkflows[msg._id].agent_details}
                        executionStats={messageWorkflows[msg._id].execution_stats}
                        phaseTiming={messageWorkflows[msg._id].phase_timing}
                        streamEvents={messageWorkflows[msg._id].stream_events}
                      />
                    )}
                  </div>
                ))}
              </>
            )}

            {/* Agent status while processing — only for streaming-capable systems */}
            {sending && availableSystems.find((s) => s.id === selectedSystem)?.streaming !== false && (
              <AgentStatus
                activeAgents={activeAgents}
                completedAgents={completedAgents}
                streamEvents={streamEvents}
                currentPhase={currentPhase}
              />
            )}
            {/* Baseline processing indicator for non-streaming systems */}
            {sending && availableSystems.find((s) => s.id === selectedSystem)?.streaming === false && (
              <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl border border-gray-200">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                <span className="text-sm text-gray-500">
                  Processing with {availableSystems.find((s) => s.id === selectedSystem)?.name}…
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <ChatInput
          onSend={handleSendMessage}
          onStop={handleStop}
          disabled={sending}
        />
      </div>

      {/* Modals */}
      {showAuth && (
        <AuthModal
          onSuccess={handleAuthSuccess}
          onClose={() => setShowAuth(false)}
        />
      )}

      {showProfile && user && (
        <ProfileModal
          profile={user.profile}
          onClose={() => setShowProfile(false)}
          onSave={handleProfileSave}
        />
      )}
    </div>
  );
}
