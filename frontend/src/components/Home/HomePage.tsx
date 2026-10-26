import React, { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { HexBackground } from '../HexBackground.tsx';
import { Sidebar } from './Sidebar.tsx';
import { MessageList } from './MessageList.tsx';
import { ChatInput } from './ChatInput.tsx';
import { HistoryPanel } from './HistoryPanel.tsx';
import { SettingsPanel } from './SettingsPanel.tsx';
import { useChat } from '../../hooks/useChat.ts';

interface HomePageProps {
  onLogout: () => void;
  onGoToLanding: () => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onLogout, onGoToLanding }) => {
  const {
    sessions,
    activeSession,
    activeSessionId,
    isStreaming,
    deepThink,
    setDeepThink,
    sendMessage,
    stopStreaming,
    createNewChat,
    selectSession,
    deleteSession,
    clearCurrentChat,
    updateMessageMeta,
  } = useChat();

  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <div className="fixed inset-0 z-30 bg-[#F7F7F8] p-2 flex overflow-hidden select-none">
      {/* Inner Card Container with Neumorphic Styling */}
      <div
        className="relative flex-1 bg-[#ECECEE] rounded-[24px] sm:rounded-[28px] flex overflow-hidden border border-black/[0.04]"
        style={{
          boxShadow: 'inset 0 1px 2px rgba(255, 255, 255, 0.8), 0 12px 36px rgba(0, 0, 0, 0.03)',
        }}
      >
        {/* Static Hex Honeycomb Background */}
        <div className="absolute inset-0 z-0 pointer-events-none rounded-[24px] sm:rounded-[28px] overflow-hidden opacity-50">
          <HexBackground isStatic={true} />
        </div>

        {/* Left Icon Sidebar */}
        <Sidebar
          onNewChat={createNewChat}
          onToggleHistory={() => setIsHistoryOpen((prev) => !prev)}
          isHistoryOpen={isHistoryOpen}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onQuickStarter={(q) => sendMessage(q)}
          onLogout={onLogout}
          onLogoClick={onGoToLanding}
        />

        {/* Center / Main Chat Stage */}
        <main className="relative z-10 flex-1 flex flex-col h-full overflow-hidden">
          {/* Top Bar Header */}
          <header className="w-full h-14 border-b border-black/[0.05] px-4 sm:px-8 flex items-center justify-between bg-white/40 backdrop-blur-md">
            {/* Left: Breadcrumbs / Title */}
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs uppercase tracking-wider text-[#8A8A90]">
                pebble
              </span>
              <span className="text-xs text-[#C0C0C6]">/</span>
              <span className="font-medium text-xs sm:text-sm text-[#111113] truncate max-w-[200px] sm:max-w-[360px]">
                {activeSession.title}
              </span>
            </div>

            {/* Right: Status Pill & Actions */}
            <div className="flex items-center gap-2.5">
              {/* Ready / Streaming Status Pill */}
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/70 border border-black/[0.06] text-[11px] font-medium text-[#44444C]">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isStreaming
                      ? 'bg-[#3CC8FF] animate-pulse'
                      : 'bg-emerald-500'
                  }`}
                />
                <span>{isStreaming ? 'streaming' : 'ready'}</span>
              </div>

              {/* Clear Chat Button */}
              {activeSession.messages.length > 0 && (
                <button
                  type="button"
                  onClick={clearCurrentChat}
                  data-cursor="button"
                  title="Clear conversation"
                  aria-label="Clear conversation"
                  className="p-1.5 rounded-lg text-[#8A8A90] hover:text-[#D9485F] hover:bg-black/[0.05] transition-colors cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </header>

          {/* Chat Messages or Empty Greeting State */}
          <div className="flex-1 flex flex-col overflow-hidden relative">
            <MessageList
              messages={activeSession.messages}
              isStreaming={isStreaming}
              onSelectStarter={(prompt) => sendMessage(prompt)}
              onUpdateMessageMeta={updateMessageMeta}
            />
          </div>

          {/* Floating Chat Input Bar */}
          <footer className="w-full px-4 sm:px-8 pb-4 shrink-0 bg-gradient-to-t from-[#ECECEE] via-[#ECECEE]/95 to-transparent">
            <ChatInput
              onSend={sendMessage}
              onStop={stopStreaming}
              isStreaming={isStreaming}
              deepThink={deepThink}
              onToggleDeepThink={() => setDeepThink(!deepThink)}
            />
          </footer>
        </main>

        {/* History Slide-over Drawer */}
        <HistoryPanel
          isOpen={isHistoryOpen}
          onClose={() => setIsHistoryOpen(false)}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={selectSession}
          onDeleteSession={deleteSession}
          onNewChat={createNewChat}
        />

        {/* Settings Modal */}
        <SettingsPanel
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
        />
      </div>
    </div>
  );
};
