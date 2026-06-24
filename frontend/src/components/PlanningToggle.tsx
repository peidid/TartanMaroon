/**
 * PlanningToggle - Toggle button to switch between chat and planning modes.
 */
'use client';

interface PlanningToggleProps {
  isPlanningMode: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export default function PlanningToggle({
  isPlanningMode,
  onToggle,
  disabled = false,
}: PlanningToggleProps) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={`
        flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm
        transition-all duration-200
        ${
          isPlanningMode
            ? 'bg-purple-600 text-white hover:bg-purple-700'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      title={isPlanningMode ? 'Exit planning mode' : 'Enter collaborative planning mode'}
    >
      {/* Icon */}
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        {isPlanningMode ? (
          // Planning mode icon (calendar/grid)
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
          />
        ) : (
          // Chat mode icon
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        )}
      </svg>

      {/* Label */}
      <span>{isPlanningMode ? 'Planning Mode' : 'Chat Mode'}</span>

      {/* Toggle indicator */}
      <div
        className={`
          relative w-10 h-5 rounded-full transition-colors
          ${isPlanningMode ? 'bg-purple-400' : 'bg-gray-500'}
        `}
      >
        <div
          className={`
            absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform shadow
            ${isPlanningMode ? 'translate-x-5' : 'translate-x-0.5'}
          `}
        />
      </div>
    </button>
  );
}
