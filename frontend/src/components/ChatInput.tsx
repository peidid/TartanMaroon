'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  onSend,
  onStop,
  disabled = false,
  placeholder = 'Ask me anything about your academic journey...',
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border-t bg-white p-4">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full resize-none rounded-xl border px-4 py-3 pr-12 outline-none disabled:bg-gray-100 disabled:cursor-not-allowed border-gray-300 focus:border-cmu-red focus:ring-1 focus:ring-cmu-red"
          />
        </div>
        {disabled && onStop ? (
          <button
            type="button"
            onClick={onStop}
            className="flex-shrink-0 w-12 h-12 rounded-xl text-white flex items-center justify-center transition-colors bg-cmu-red hover:bg-cmu-darkred"
            title="Stop generation"
          >
            <Square className="w-5 h-5 fill-current" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!message.trim() || disabled}
            className="flex-shrink-0 w-12 h-12 rounded-xl text-white flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-cmu-red hover:bg-cmu-darkred"
          >
            <Send className="w-5 h-5" />
          </button>
        )}
      </div>
      <p className="text-center text-xs text-gray-400 mt-2">
        Press Enter to send, Shift+Enter for new line
      </p>
    </form>
  );
}
