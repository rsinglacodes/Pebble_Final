import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '../../lib/chat.ts';
import { Message } from './Message.tsx';
import { Greeting } from './Greeting.tsx';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onSelectStarter: (prompt: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isStreaming,
  onSelectStarter,
}) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom on new messages or streaming tokens
  const stickRef = useRef(true);
  const prevLenRef = useRef(0);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (messages.length !== prevLenRef.current) {
      stickRef.current = true; // new message: jump to it
      prevLenRef.current = messages.length;
    }
    if (!stickRef.current) return; // user scrolled up to read: don't yank them down
    const id = requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
    return () => cancelAnimationFrame(id);
  }, [messages]);

  <div
    ref={containerRef}
    onScroll={handleScroll}
    className="flex-1 w-full overflow-y-auto overflow-x-hidden px-2 sm:px-4 py-4 space-y-2 chat-scrollbar"
  ></div>
  if (messages.length === 0) {
    return <Greeting onSelectPrompt={onSelectStarter} />;
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 w-full overflow-y-auto overflow-x-hidden px-2 sm:px-4 py-4 space-y-2 chat-scrollbar"
    >
      <div className="max-w-3xl mx-auto w-full flex flex-col justify-end min-h-full">
        {messages.map((msg, idx) => (
          <Message
            key={msg.id}
            message={msg}
            isStreaming={isStreaming && idx === messages.length - 1 && msg.role === 'assistant'}
          />
        ))}
        <div ref={bottomRef} className="h-4" />
      </div>

      <style>{`
        .chat-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: rgba(17, 17, 17, 0.15) transparent;
        }
        .chat-scrollbar::-webkit-scrollbar {
          width: 5px;
        }
        .chat-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .chat-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(17, 17, 17, 0.15);
          border-radius: 9999px;
        }
      `}</style>
    </div>
  );
};
