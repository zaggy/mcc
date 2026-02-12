import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import api from "@/lib/api";
import { connectSocket, disconnectSocket, getSocket } from "@/lib/socket";
import ConversationPanel from "@/components/project/ConversationPanel";
import ChatPanel from "@/components/project/ChatPanel";
import InfoPanel from "@/components/project/InfoPanel";
import type {
  Project,
  Agent,
  Conversation,
  Message,
  PaginatedMessages,
} from "@/types";

export default function ProjectPage() {
  const { id: projectId } = useParams<{ id: string }>();

  const [project, setProject] = useState<Project | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loading, setLoading] = useState(true);

  const prevConvoRef = useRef<string | null>(null);
  const activeIdRef = useRef<string | null>(null);

  // Fetch project, agents, conversations on mount
  useEffect(() => {
    if (!projectId) return;

    async function load() {
      try {
        const [projRes, agentsRes, convosRes] = await Promise.all([
          api.get(`/projects/${projectId}`),
          api.get(`/projects/${projectId}/agents`),
          api.get(`/projects/${projectId}/conversations`),
        ]);
        setProject(projRes.data);
        setAgents(agentsRes.data);
        setConversations(convosRes.data);
      } catch {
        // handled silently
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [projectId]);

  // Connect WebSocket on mount, disconnect on unmount
  useEffect(() => {
    const socket = connectSocket();

    socket.on("message", (data: { id: string; conversation_id: string; author_type: string; agent_id: string | null; content: string; created_at: string }) => {
      if (data.conversation_id !== activeIdRef.current) return;
      setMessages((prev) => {
        if (prev.some((m) => m.id === data.id)) return prev;
        return [
          ...prev,
          {
            id: data.id,
            conversation_id: data.conversation_id,
            author_type: data.author_type as "user" | "agent",
            user_id: null,
            agent_id: data.agent_id,
            content: data.content,
            tokens_in: 0,
            tokens_out: 0,
            cost_usd: "0",
            model_used: null,
            created_at: data.created_at,
          },
        ];
      });
    });

    return () => {
      disconnectSocket();
    };
  }, []);

  // Join/leave conversation rooms on activeConversationId change
  useEffect(() => {
    const socket = getSocket();
    if (!socket) return;

    if (prevConvoRef.current) {
      socket.emit("leave_conversation", {
        conversation_id: prevConvoRef.current,
      });
    }

    if (activeConversationId) {
      socket.emit("join_conversation", {
        conversation_id: activeConversationId,
      });
    }

    prevConvoRef.current = activeConversationId;
    activeIdRef.current = activeConversationId;
  }, [activeConversationId]);

  // Fetch messages when active conversation changes
  useEffect(() => {
    if (!projectId || !activeConversationId) {
      setMessages([]);
      setHasMore(false);
      setNextCursor(null);
      return;
    }

    async function fetchMessages() {
      try {
        const { data } = await api.get<PaginatedMessages>(
          `/projects/${projectId}/conversations/${activeConversationId}/messages`
        );
        setMessages([...data.messages].reverse());
        setHasMore(data.has_more);
        setNextCursor(data.next_cursor);
      } catch {
        // handled silently
      }
    }

    fetchMessages();
  }, [projectId, activeConversationId]);

  const handleLoadMore = useCallback(async () => {
    if (!projectId || !activeConversationId || !nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const { data } = await api.get<PaginatedMessages>(
        `/projects/${projectId}/conversations/${activeConversationId}/messages`,
        { params: { before: nextCursor, limit: 50 } }
      );
      setMessages((prev) => [...[...data.messages].reverse(), ...prev]);
      setHasMore(data.has_more);
      setNextCursor(data.next_cursor);
    } catch {
      // handled silently
    } finally {
      setLoadingMore(false);
    }
  }, [projectId, activeConversationId, nextCursor, loadingMore]);

  const handleMessageSent = useCallback((msg: Message) => {
    setMessages((prev) => {
      if (prev.some((m) => m.id === msg.id)) return prev;
      return [...prev, msg];
    });
  }, []);

  const handleConversationCreated = useCallback((c: Conversation) => {
    setConversations((prev) => [c, ...prev]);
    setActiveConversationId(c.id);
  }, []);

  const handleAgentCreated = useCallback((agent: Agent) => {
    setAgents((prev) => [...prev, agent]);
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Project not found
      </div>
    );
  }

  const activeConversation =
    conversations.find((c) => c.id === activeConversationId) ?? null;

  return (
    <div className="flex h-full">
      <ConversationPanel
        projectId={project.id}
        conversations={conversations}
        agents={agents}
        activeId={activeConversationId}
        onSelect={setActiveConversationId}
        onCreated={handleConversationCreated}
      />
      <ChatPanel
        projectId={project.id}
        conversation={activeConversation}
        messages={messages}
        agents={agents}
        hasMore={hasMore}
        loadingMore={loadingMore}
        onLoadMore={handleLoadMore}
        onMessageSent={handleMessageSent}
      />
      <InfoPanel
        project={project}
        agents={agents}
        onAgentCreated={handleAgentCreated}
      />
    </div>
  );
}
