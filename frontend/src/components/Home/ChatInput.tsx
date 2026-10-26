import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Square, Code, Sparkles } from 'lucide-react';

interface ChatInputProps {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  deepThink: boolean;
  onToggleDeepThink: () => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  onStop,
  isStreaming,
  deepThink,
  onToggleDeepThink,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Auto-expand textarea up to ~120px height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 130)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (isStreaming) {
      onStop();
      return;
    }
    const trimmed = input.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleInsertSnippet = () => {
    setInput((prev) =>
      prev ? `${prev}\n\n\`\`\`typescript\n// Paste problem or code here\n\`\`\`` : `\`\`\`typescript\n// Paste problem or code here\n\`\`\``
    );
    textareaRef.current?.focus();
  };

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col items-center select-none pt-2">
      {/* Capsule Container */}
      <div className="w-full bg-[#FAFAFB] rounded-[24px] border border-black/[0.08] shadow-[0_10px_30px_rgba(0,0,0,0.06)] focus-within:ring-2 focus-within:ring-[#6C5CFF]/30 transition-all p-2 flex flex-col gap-2">
        {/* Top Textarea Row */}
        <div className="w-full flex items-start gap-2 px-2 pt-1">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask pebble anything about algorithms, code, or complexity..."
            rows={1}
            data-cursor="input"
            className="flex-1 max-h-[130px] resize-none bg-transparent text-[14px] text-[#111113] placeholder:text-[#8A8A90] outline-none leading-relaxed py-1"
          />
        </div>

        {/* Bottom Actions Row */}
        <div className="w-full flex items-center justify-between pt-1 border-t border-black/[0.04]">
          {/* Left Actions: Code Snippet inserter */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleInsertSnippet}
              data-cursor="button"
              title="Insert code snippet template"
              className="px-2.5 py-1.5 rounded-full text-xs font-medium text-[#6B6B73] hover:text-[#111113] hover:bg-black/[0.05] transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Code className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Snippet</span>
            </button>
          </div>

          {/* Right Actions: Deep Think / Visual Mode toggle & Send / Stop Button */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onToggleDeepThink}
              data-cursor="button"
              title="Toggle step-by-step visual mode"
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                deepThink
                  ? 'bg-gradient-to-r from-[#6C5CFF]/15 to-[#3CC8FF]/15 text-[#5241E0] border border-[#6C5CFF]/25 shadow-2xs'
                  : 'text-[#6B6B73] hover:text-[#111113] hover:bg-black/[0.05]'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Visual mode</span>
            </button>

            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                data-cursor="button"
                title="Stop response"
                className="w-8 h-8 rounded-full bg-[#111113] text-white hover:bg-[#2A2A30] flex items-center justify-center transition-all cursor-pointer shadow-xs active:scale-95"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!input.trim()}
                data-cursor="button"
                title="Send message"
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all cursor-pointer shadow-xs active:scale-95 ${
                  input.trim()
                    ? 'text-white hover:scale-105'
                    : 'text-white/40 cursor-not-allowed opacity-40'
                }`}
                style={{
                  background: 'linear-gradient(135deg, #B33CF0 0%, #6C5CFF 50%, #3CC8FF 100%)',
                }}
              >
                <ArrowUp className="w-4 h-4 stroke-[2.5]" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tiny Disclaimer */}
      <p className="text-[11px] text-[#9E9EA8] mt-2 select-none tracking-tight">
        pebble explains algorithms step-by-step. Verify important code.
      </p>
    </div>
  );
};
