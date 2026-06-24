'use client';

import { User, Bot, GraduationCap, BookOpen, Shield, Calendar } from 'lucide-react';
import { Message } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessageProps {
  message: Message;
}

// Agent info for visualization
const agentInfo: Record<string, { name: string; icon: React.ReactNode; color: string }> = {
  programs_requirements: {
    name: 'Programs Agent',
    icon: <GraduationCap className="w-4 h-4" />,
    color: 'bg-blue-100 text-blue-700',
  },
  course_scheduling: {
    name: 'Courses Agent',
    icon: <BookOpen className="w-4 h-4" />,
    color: 'bg-green-100 text-green-700',
  },
  policy_compliance: {
    name: 'Policy Agent',
    icon: <Shield className="w-4 h-4" />,
    color: 'bg-purple-100 text-purple-700',
  },
  academic_planning: {
    name: 'Planning Agent',
    icon: <Calendar className="w-4 h-4" />,
    color: 'bg-orange-100 text-orange-700',
  },
};

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const agentsUsed = message.metadata?.agents_used || [];

  return (
    <div className={`flex gap-3 message-enter ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-cmu-red text-white' : 'bg-gray-200 text-gray-600'
        }`}
      >
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      {/* Message content */}
      <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Agent badges (for assistant messages) */}
        {!isUser && agentsUsed.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1">
            {agentsUsed.map((agent) => {
              const info = agentInfo[agent];
              if (!info) return null;
              return (
                <span
                  key={agent}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${info.color}`}
                >
                  {info.icon}
                  {info.name}
                </span>
              );
            })}
          </div>
        )}

        {/* Message bubble */}
        <div
          className={`rounded-2xl px-4 py-2 ${
            isUser
              ? 'bg-cmu-red text-white rounded-tr-sm'
              : 'bg-gray-100 text-gray-800 rounded-tl-sm'
          }`}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <div className="prose prose-sm max-w-none prose-headings:mt-2 prose-headings:mb-1 prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-strong:text-gray-900">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="text-xs text-gray-400 mt-1">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </div>
  );
}
