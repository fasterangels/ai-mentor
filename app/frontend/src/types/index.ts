export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking_state?: string;
  used_online: boolean;
  created_at: string;
}

export interface Memory {
  id: number;
  content: string;
  importance: number;
  tags: string;
  created_at: string;
  updated_at: string;
}

export interface Knowledge {
  id: number;
  title: string;
  summary: string;
  content?: string;
  tags: string;
  sources?: string;
  created_at: string;
  updated_at: string;
}

export interface HealthStatus {
  status: string;
  ollama_connected: boolean;
  timestamp: string;
}