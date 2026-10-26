import React from 'react';
import { Plus, MessageSquare, Code2, Sparkles, Settings } from 'lucide-react';
import { UserChip } from './UserChip.tsx';

interface SidebarProps {
  onNewChat: () => void;
  onToggleHistory: () => void;
  isHistoryOpen: boolean;
  onOpenSettings: () => void;
  onQuickStarter: (query: string) => void;
  onLogout: () => void;
  onLogoClick: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onNewChat,
  onToggleHistory,
  isHistoryOpen,
  onOpenSettings,
  onQuickStarter,
  onLogout,
  onLogoClick,
}) => {
  return (
    <aside className="w-16 h-full border-r border-black/[0.06] bg-[#ECECEE]/90 flex flex-col items-center justify-between py-4 select-none shrink-0 z-20">
      {/* Top: Small pebble logo glyph */}
      <div className="flex flex-col items-center gap-6">
        <button
          type="button"
          onClick={onLogoClick}
          data-cursor="button"
          title="pebble home"
          aria-label="pebble home"
          className="w-10 h-10 rounded-2xl bg-white/70 hover:bg-white flex items-center justify-center border border-black/[0.06] shadow-xs transition-all hover:scale-105 active:scale-95 cursor-pointer group"
        >
          <div
            className="w-6 h-5 rounded-[48%_52%_68%_32%_/_42%_44%_56%_58%] p-[1.5px] transition-transform duration-300 group-hover:rotate-6"
            style={{
              background: 'linear-gradient(135deg, #B33CF0 0%, #6C5CFF 50%, #3CC8FF 100%)',
            }}
          >
            <div className="w-full h-full bg-[#121217] rounded-[46%_54%_66%_34%_/_40%_42%_58%_60%] flex items-center justify-center gap-0.5 px-0.5">
              <span className="w-1 h-1.5 bg-gradient-to-b from-white to-[#C7D2FE] rounded-full" />
              <span className="w-1 h-1.5 bg-gradient-to-b from-white to-[#A5F3FC] rounded-full" />
            </div>
          </div>
        </button>

        {/* New Chat Primary Button */}
        <button
          type="button"
          onClick={onNewChat}
          data-cursor="button"
          title="Start new chat"
          aria-label="Start new chat"
          className="w-10 h-10 rounded-xl bg-[#111113] hover:bg-[#25252A] text-white flex items-center justify-center shadow-xs transition-all hover:scale-105 active:scale-95 cursor-pointer"
        >
          <Plus className="w-5 h-5 stroke-[2]" />
        </button>

        {/* Middle Navigation Icons */}
        <div className="flex flex-col items-center gap-2 pt-2">
          {/* History Toggle */}
          <button
            type="button"
            onClick={onToggleHistory}
            data-cursor="button"
            title="Chat history"
            aria-label="Chat history"
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all cursor-pointer ${
              isHistoryOpen
                ? 'bg-white text-[#111113] shadow-xs'
                : 'text-[#6B6B73] hover:text-[#111113] hover:bg-white/60'
            }`}
          >
            <MessageSquare className="w-5 h-5 stroke-[1.75]" />
          </button>

          {/* Quick Algorithm Library */}
          <button
            type="button"
            onClick={() => onQuickStarter('Explain Two Sum with two pointers')}
            data-cursor="button"
            title="Two Pointers starter"
            aria-label="Two Pointers starter"
            className="w-10 h-10 rounded-xl flex items-center justify-center text-[#6B6B73] hover:text-[#111113] hover:bg-white/60 transition-all cursor-pointer"
          >
            <Code2 className="w-5 h-5 stroke-[1.75]" />
          </button>

          {/* Visualizer Playground */}
          <button
            type="button"
            onClick={() => onQuickStarter('How does Binary Search divide the array?')}
            data-cursor="button"
            title="Binary Search visualizer"
            aria-label="Binary Search visualizer"
            className="w-10 h-10 rounded-xl flex items-center justify-center text-[#6B6B73] hover:text-[#111113] hover:bg-white/60 transition-all cursor-pointer"
          >
            <Sparkles className="w-5 h-5 stroke-[1.75]" />
          </button>
        </div>
      </div>

      {/* Bottom: Settings & User Profile Chip */}
      <div className="flex flex-col items-center gap-3">
        <button
          type="button"
          onClick={onOpenSettings}
          data-cursor="button"
          title="Visualizer settings"
          aria-label="Visualizer settings"
          className="w-10 h-10 rounded-xl flex items-center justify-center text-[#6B6B73] hover:text-[#111113] hover:bg-white/60 transition-all cursor-pointer"
        >
          <Settings className="w-5 h-5 stroke-[1.75]" />
        </button>

        <UserChip onLogout={onLogout} onOpenSettings={onOpenSettings} />
      </div>
    </aside>
  );
};
