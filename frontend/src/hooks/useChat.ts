
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  ChatMessage,
  ChatSession,
  loadChatSessions,
  saveChatSessions,
  createChatSession,
  askPebble,
  formatAskResponse,
} from '../lib/chat.ts';
import { request } from '../lib/api.ts';

export function useChat() {

  const [initialSessions] = useState<ChatSession[]>(() => {
    const loaded = loadChatSessions();
    return loaded.length > 0
      ? loaded
      : [createChatSession('New conversation')];
  });

  const [sessions, setSessions] =
    useState<ChatSession[]>(initialSessions);

  const [activeSessionId, setActiveSessionId] = useState<string>(
    () => initialSessions[0]?.id ?? ''
  );


  const [isStreaming, setIsStreaming] = useState(false);
  const [deepThink, setDeepThink] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Ensure the initial active session always exists.
  useEffect(() => {
    if (!sessions.some((s) => s.id === activeSessionId)) {
      setActiveSessionId(sessions[0]?.id ?? '');
    }
  }, [sessions, activeSessionId]);

  // Persist sessions with a small debounce.
  useEffect(() => {
    const id = window.setTimeout(
      () => saveChatSessions(sessions),
      isStreaming ? 1000 : 150
    );

    return () => window.clearTimeout(id);
  }, [sessions, isStreaming]);

  const activeSession =
    sessions.find((s) => s.id === activeSessionId) ?? sessions[0];

  const cancelRequest = useCallback(() => {
    const controller = abortControllerRef.current;

    if (controller) {
      abortControllerRef.current = null;
      controller.abort();
      setIsStreaming(false);
    }
  }, []);

  const createNewChat = useCallback(() => {
    cancelRequest();

    const newSession = createChatSession('New conversation');

    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
  }, [cancelRequest]);

  const selectSession = useCallback(
    (id: string) => {
      cancelRequest();
      setActiveSessionId(id);
    },
    [cancelRequest]
  );

  const deleteSession = useCallback(
    (id: string) => {
      if (id === activeSessionId) {
        cancelRequest();
      }

      setSessions((prev) => {
        const filtered = prev.filter((s) => s.id !== id);

        if (filtered.length > 0) {
          return filtered;
        }

        return [createChatSession('New conversation')];
      });

      if (id === activeSessionId) {
        const nextSession = sessions.find((s) => s.id !== id);

        if (nextSession) {
          setActiveSessionId(nextSession.id);
        } else {
          // The replacement session is created in the state updater.
          // The effect above selects it once it appears in sessions.
          setActiveSessionId('');
        }
      }
    },
    [activeSessionId, cancelRequest, sessions]
  );

  const clearCurrentChat = useCallback(() => {
    cancelRequest();

    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? {
            ...s,
            title: 'New conversation',
            messages: [],
            updatedAt: Date.now(),
          }
          : s
      )
    );
  }, [activeSessionId, cancelRequest]);

  const stopStreaming = cancelRequest;

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();

      if (!trimmed || abortControllerRef.current) return;

      const sessionId = activeSession?.id;
      if (!sessionId) return;

      const now = Date.now();

      const userMsg: ChatMessage = {
        id: `msg_${now}_u`,
        role: 'user',
        content: trimmed,
        timestamp: now,
      };

      const assistantMsgId = `msg_${now}_a`;

      const initialAssistantMsg: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: now,
      };

      const currentTitle =
        activeSession.messages.length === 0
          ? trimmed.slice(0, 36) +
          (trimmed.length > 36 ? '...' : '')
          : activeSession.title;

      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? {
              ...s,
              title: currentTitle,
              updatedAt: now,
              messages: [
                ...s.messages,
                userMsg,
                initialAssistantMsg,
              ],
            }
            : s
        )
      );

      const controller = new AbortController();
      abortControllerRef.current = controller;
      setIsStreaming(true);

      const setReply = (content: string) => {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? {
                ...s,
                messages: s.messages.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, content }
                    : m
                ),
                updatedAt: Date.now(),
              }
              : s
          )
        );
      };

      try {
        const response = await askPebble(
          trimmed,
          'python',
          controller.signal
        );

        const reply = formatAskResponse(response);

        if (!controller.signal.aborted) {
          setSessions((prev) =>
            prev.map((s) =>
              s.id === sessionId
                ? {
                    ...s,
                    messages: s.messages.map((m) =>
                      m.id === assistantMsgId
                        ? { ...m, content: String(reply), meta: response }
                        : m
                    ),
                    updatedAt: Date.now(),
                  }
                : s
            )
          );
        }
      } catch (err) {
        if (controller.signal.aborted) {
          setReply('*Stopped.*');
        } else {
          setReply(
            `Warning: ${err instanceof Error
              ? err.message
              : 'Something went wrong'
            }`
          );
        }
      } finally {
        // An older request must not reset a newer request's state.
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
          setIsStreaming(false);
        }
      }
    },
    [activeSession]
  );

  const updateMessageMeta = useCallback(
    async (messageId: string, metaUpdates: Record<string, any>) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? {
                ...s,
                messages: s.messages.map((m) =>
                  m.id === messageId
                    ? { ...m, meta: { ...(m.meta || {}), ...metaUpdates } }
                    : m
                ),
                updatedAt: Date.now(),
              }
            : s
        )
      );

      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (uuidRegex.test(activeSessionId) && uuidRegex.test(messageId)) {
        try {
          await request(`/conversations/${activeSessionId}/messages/${messageId}`, {
            method: 'PATCH',
            body: { meta: metaUpdates },
          });
        } catch {
          // Keep local state intact if network sync fails
        }
      }
    },
    [activeSessionId]
  );

  return {
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
  };
}
