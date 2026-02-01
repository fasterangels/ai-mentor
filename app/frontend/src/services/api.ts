import { Conversation, Message, Memory, Knowledge, HealthStatus } from '@/types';

const API_BASE_URL = 'http://127.0.0.1:8000';

class APIClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Health check
  async checkHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/health');
  }

  // Conversations
  async getConversations(): Promise<Conversation[]> {
    return this.request<Conversation[]>('/conversations');
  }

  async createConversation(title: string): Promise<Conversation> {
    return this.request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  }

  async deleteConversation(id: number): Promise<void> {
    await this.request(`/conversations/${id}`, { method: 'DELETE' });
  }

  // Messages
  async getMessages(conversationId: number): Promise<Message[]> {
    return this.request<Message[]>(`/conversations/${conversationId}/messages`);
  }

  async sendMessage(
    conversationId: number,
    content: string,
    useOnline: boolean = false
  ): Promise<Message> {
    return this.request<Message>('/messages', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        content,
        use_online: useOnline,
      }),
    });
  }

  async generateSummary(conversationId: number): Promise<{ summary: string }> {
    return this.request<{ summary: string }>(
      `/conversations/${conversationId}/summary`,
      { method: 'POST' }
    );
  }

  // Memories
  async getMemories(minImportance: number = 0): Promise<Memory[]> {
    return this.request<Memory[]>(`/memories?min_importance=${minImportance}`);
  }

  async createMemory(
    content: string,
    importance: number = 0.5,
    tags: string = ''
  ): Promise<Memory> {
    return this.request<Memory>('/memories', {
      method: 'POST',
      body: JSON.stringify({ content, importance, tags }),
    });
  }

  async updateMemory(
    id: number,
    content: string,
    importance: number,
    tags: string
  ): Promise<Memory> {
    return this.request<Memory>(`/memories/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ content, importance, tags }),
    });
  }

  async deleteMemory(id: number): Promise<void> {
    await this.request(`/memories/${id}`, { method: 'DELETE' });
  }

  // Knowledge
  async getKnowledge(): Promise<Knowledge[]> {
    return this.request<Knowledge[]>('/knowledge');
  }

  async createKnowledge(
    title: string,
    summary: string,
    content: string = '',
    tags: string = '',
    sources: string = ''
  ): Promise<Knowledge> {
    return this.request<Knowledge>('/knowledge', {
      method: 'POST',
      body: JSON.stringify({ title, summary, content, tags, sources }),
    });
  }

  async updateKnowledge(
    id: number,
    title: string,
    summary: string,
    content: string,
    tags: string,
    sources: string
  ): Promise<Knowledge> {
    return this.request<Knowledge>(`/knowledge/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ title, summary, content, tags, sources }),
    });
  }

  async deleteKnowledge(id: number): Promise<void> {
    await this.request(`/knowledge/${id}`, { method: 'DELETE' });
  }
}

export const apiClient = new APIClient();