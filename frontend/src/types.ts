export interface Project {
  id: string;
  name: string;
  description: string | null;
  github_repo: string;
  is_active: boolean;
  owner_id: string;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
  model_config_json: Record<string, unknown>;
  is_active: boolean;
  project_id: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  type: string;
  status: string;
  project_id: string | null;
  created_by_user_id: string | null;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  author_type: "user" | "agent";
  user_id: string | null;
  agent_id: string | null;
  content: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: string;
  model_used: string | null;
  created_at: string;
}

export interface PaginatedMessages {
  messages: Message[];
  has_more: boolean;
  next_cursor: string | null;
}
