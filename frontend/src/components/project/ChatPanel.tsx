import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Loader2 } from "lucide-react";
import type { Message, Agent, Conversation } from "@/types";
import api from "@/lib/api";

interface ChatPanelProps {
  projectId: string;
  conversation: Conversation | null;
  messages: Message[];
  agents: Agent[];
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  onMessageSent: (msg: Message) => void;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ChatPanel({
  projectId,
  conversation,
  messages,
  agents,
  hasMore,
  loadingMore,
  onLoadMore,
  onMessageSent,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const agentMap = new Map(agents.map((a) => [a.id, a]));

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !conversation) return;
    setSending(true);
    try {
      const { data } = await api.post(
        `/projects/${projectId}/conversations/${conversation.id}/messages`,
        { content: input.trim() }
      );
      onMessageSent(data);
      setInput("");
    } catch {
      // handled silently
    } finally {
      setSending(false);
    }
  }

  if (!conversation) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        Select a conversation to start chatting
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div>
          <h3 className="text-sm font-semibold">
            {conversation.title || `${conversation.type} conversation`}
          </h3>
          <span className="text-xs text-muted-foreground">
            {conversation.status}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-4 py-3">
        {hasMore && (
          <div className="mb-3 text-center">
            <Button
              variant="ghost"
              size="xs"
              onClick={onLoadMore}
              disabled={loadingMore}
            >
              {loadingMore ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : null}
              Load more
            </Button>
          </div>
        )}

        <div className="space-y-4">
          {messages.map((msg) => {
            const isUser = msg.author_type === "user";
            const agent = msg.agent_id ? agentMap.get(msg.agent_id) : null;
            const author = isUser ? "You" : agent?.name ?? "Agent";
            const cost = parseFloat(msg.cost_usd);

            return (
              <div key={msg.id} className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
                <div className="mb-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-medium">{author}</span>
                  <span>{formatTime(msg.created_at)}</span>
                </div>
                <div
                  className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
                {!isUser && cost > 0 && (
                  <span className="mt-0.5 text-[10px] text-muted-foreground">
                    {msg.tokens_in + msg.tokens_out} tokens &middot; ${cost.toFixed(4)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSend}
        className="flex items-center gap-2 border-t px-4 py-3"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={sending || conversation.status !== "active"}
          className="flex-1"
        />
        <Button type="submit" size="icon" disabled={sending || !input.trim()}>
          {sending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </form>
    </div>
  );
}
