import React from 'react';
import { X, Trash2, Plus, MessageSquare } from 'lucide-react';
import { ChatSession } from '../../lib/chat.ts';

interface HistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onNewChat: () => void;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
  isOpen,
  onClose,
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onNewChat,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-40 select-none">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="absolute inset-0 bg-black/15 backdrop-blur-[2px] transition-opacity cursor-pointer"
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <div className="absolute top-0 left-0 sm:left-16 bottom-0 w-72 sm:w-80 bg-[#FAFAFB] border-r border-black/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.15)] flex flex-col z-50 animate-slideRight">
        {/* Header */}
        <div className="p-4 border-b border-black/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-[#6C5CFF]" />
            <h3 className="font-semibold text-sm text-[#111113]">Conversations</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-cursor="button"
            aria-label="Close history"
            className="w-7 h-7 rounded-full hover:bg-black/[0.05] flex items-center justify-center text-[#8A8A90] hover:text-[#111113] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* New Chat Action */}
        <div className="p-3 border-b border-black/[0.04]">
          <button
            type="button"
            onClick={() => {
              onNewChat();
              onClose();
            }}
            data-cursor="button"
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-[12px] bg-[#111113] hover:bg-[#25252A] text-white text-xs font-semibold shadow-xs transition-all cursor-pointer active:scale-98"
          >
            <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>New conversation</span>
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((s) => {
            const isActive = s.id === activeSessionId;
            const messageCount = s.messages.length;
            const dateStr = new Date(s.updatedAt).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
            });

            return (
              <div
                key={s.id}
                onClick={() => {
                  onSelectSession(s.id);
                  onClose();
                }}
                data-cursor="button"
                className={`group relative flex items-center justify-between p-2.5 rounded-[12px] text-xs transition-all cursor-pointer ${
                  isActive
                    ? 'bg-black/[0.06] text-[#111113] font-semibold'
                    : 'hover:bg-black/[0.03] text-[#55555D]'
                }`}
              >
                <div className="flex flex-col flex-1 pr-2 truncate">
                  <span className="truncate text-[13px]">{s.title}</span>
                  <span className="text-[10px] text-[#9E9EA8] mt-0.5 font-normal">
                    {dateStr} • {messageCount} {messageCount === 1 ? 'message' : 'messages'}
                  </span>
                </div>

                {sessions.length > 1 && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(s.id);
                    }}
                    title="Delete chat"
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-black/[0.08] text-[#8A8A90] hover:text-[#D9485F] transition-all cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
        @keyframes slideRight {
          from {
            transform: translateX(-100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slideRight {
          animation: slideRight 200ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
    </div>
  );
};
