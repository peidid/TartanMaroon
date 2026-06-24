'use client';

import { useState } from 'react';
import {
  MessageSquare,
  Plus,
  Trash2,
  LogOut,
  User,
  ChevronLeft,
  ChevronRight,
  Settings,
} from 'lucide-react';
import { Conversation, User as UserType } from '@/lib/api';

interface SidebarProps {
  user: UserType | null;
  conversations: Conversation[];
  currentConversationId: string | null;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onLogout: () => void;
  onOpenProfile: () => void;
}

export default function Sidebar({
  user,
  conversations,
  currentConversationId,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onLogout,
  onOpenProfile,
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div
      className={`flex flex-col bg-gray-900 text-white transition-all duration-300 ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        {!isCollapsed && (
          <h1 className="text-lg font-semibold text-cmu-red">TartanMaroon</h1>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 hover:bg-gray-700 rounded"
        >
          {isCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* New Conversation Button */}
      <div className="p-2">
        <button
          onClick={onNewConversation}
          className={`flex items-center gap-2 w-full p-2 rounded-lg border border-gray-600 hover:bg-gray-700 transition-colors ${
            isCollapsed ? 'justify-center' : ''
          }`}
        >
          <Plus className="w-5 h-5" />
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-2">
        {conversations.map((conv) => (
          <div
            key={conv._id}
            className={`group flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
              currentConversationId === conv._id
                ? 'bg-gray-700'
                : 'hover:bg-gray-800'
            }`}
            onClick={() => onSelectConversation(conv._id)}
          >
            <MessageSquare className="w-4 h-4 flex-shrink-0" />
            {!isCollapsed && (
              <>
                <span className="flex-1 truncate text-sm">{conv.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv._id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-600 rounded"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </>
            )}
          </div>
        ))}
      </div>

      {/* User Section */}
      {user && (
        <div className="border-t border-gray-700 p-2">
          <div
            className={`flex items-center gap-2 p-2 rounded-lg hover:bg-gray-800 cursor-pointer ${
              isCollapsed ? 'justify-center' : ''
            }`}
            onClick={onOpenProfile}
          >
            <div className="w-8 h-8 bg-cmu-red rounded-full flex items-center justify-center">
              <User className="w-4 h-4" />
            </div>
            {!isCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user.name}</p>
                <p className="text-xs text-gray-400 truncate">{user.email}</p>
              </div>
            )}
          </div>

          {!isCollapsed && (
            <div className="flex gap-1 mt-1">
              <button
                onClick={onOpenProfile}
                className="flex-1 flex items-center justify-center gap-1 p-2 text-sm text-gray-300 hover:bg-gray-800 rounded"
              >
                <Settings className="w-4 h-4" />
                Profile
              </button>
              <button
                onClick={onLogout}
                className="flex-1 flex items-center justify-center gap-1 p-2 text-sm text-gray-300 hover:bg-gray-800 rounded"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
