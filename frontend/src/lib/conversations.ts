import { request } from './api.ts';

export interface ApiMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  mode?: string | null;
  meta?: Record<string, any> | null;
  created_at: string;
}

export interface ApiConversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ApiConversationDetail extends ApiConversation {
  messages: ApiMessage[];
}

export interface CreateMessagePayload {
  role: 'user' | 'assistant';
  content: string;
  mode?: string;
  meta?: Record<string, any>;
}

export async function fetchConversations(limit = 50, offset = 0): Promise<ApiConversation[]> {
  return request<ApiConversation[]>(`/conversations?limit=${limit}&offset=${offset}`);
}

export async function createConversation(title?: string): Promise<ApiConversation> {
  return request<ApiConversation>('/conversations', {
    method: 'POST',
    body: title ? { title } : undefined,
  });
}

export async function fetchConversationDetail(conversationId: string): Promise<ApiConversationDetail> {
  return request<ApiConversationDetail>(`/conversations/${conversationId}`);
}

export async function createConversationMessage(
  conversationId: string,
  payload: CreateMessagePayload
): Promise<ApiMessage> {
  return request<ApiMessage>(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: payload,
  });
}

export async function updateConversationTitle(
  conversationId: string,
  title: string
): Promise<ApiConversation> {
  return request<ApiConversation>(`/conversations/${conversationId}`, {
    method: 'PATCH',
    body: { title },
  });
}

export async function deleteConversationApi(conversationId: string): Promise<void> {
  return request<void>(`/conversations/${conversationId}`, {
    method: 'DELETE',
  });
}

export async function updateMessageMetaApi(
  conversationId: string,
  messageId: string,
  meta: Record<string, any>
): Promise<ApiMessage> {
  return request<ApiMessage>(`/conversations/${conversationId}/messages/${messageId}`, {
    method: 'PATCH',
    body: { meta },
  });
}
