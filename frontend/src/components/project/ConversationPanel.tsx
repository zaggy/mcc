import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Plus, MessageSquare, X } from "lucide-react";
import type { Conversation, Agent } from "@/types";
import api from "@/lib/api";

const typeColors: Record<string, string> = {
  general: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  issue: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  task: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
  review: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
};

interface ConversationPanelProps {
  projectId: string;
  conversations: Conversation[];
  agents: Agent[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreated: (c: Conversation) => void;
}

export default function ConversationPanel({
  projectId,
  conversations,
  agents,
  activeId,
  onSelect,
  onCreated,
}: ConversationPanelProps) {
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("general");
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const { data } = await api.post(`/projects/${projectId}/conversations`, {
        title: title || null,
        type,
        agent_ids: selectedAgents,
      });
      onCreated(data);
      setTitle("");
      setType("general");
      setSelectedAgents([]);
      setShowForm(false);
    } catch {
      // handled silently
    } finally {
      setCreating(false);
    }
  }

  function toggleAgent(id: string) {
    setSelectedAgents((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    );
  }

  const grouped = conversations.reduce<Record<string, Conversation[]>>(
    (acc, c) => {
      const key = c.type || "general";
      (acc[key] ??= []).push(c);
      return acc;
    },
    {}
  );

  return (
    <div className="flex h-full w-64 flex-col border-r">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <span className="text-sm font-semibold">Conversations</span>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="space-y-2 border-b p-3">
          <Input
            placeholder="Title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="h-7 text-xs"
          />
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="h-7 w-full rounded-md border bg-background px-2 text-xs"
          >
            <option value="general">General</option>
            <option value="issue">Issue</option>
            <option value="task">Task</option>
            <option value="review">Review</option>
          </select>
          {agents.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs text-muted-foreground">Agents:</span>
              {agents.map((a) => (
                <label key={a.id} className="flex items-center gap-1.5 text-xs">
                  <input
                    type="checkbox"
                    checked={selectedAgents.includes(a.id)}
                    onChange={() => toggleAgent(a.id)}
                    className="rounded"
                  />
                  {a.name}
                </label>
              ))}
            </div>
          )}
          <Button type="submit" size="xs" className="w-full" disabled={creating}>
            {creating ? "Creating..." : "Create"}
          </Button>
        </form>
      )}

      <div className="flex-1 overflow-y-auto">
        {Object.entries(grouped).map(([groupType, convos]) => (
          <div key={groupType}>
            <div className="px-3 pt-3 pb-1">
              <Badge
                variant="outline"
                className={typeColors[groupType] ?? ""}
              >
                {groupType}
              </Badge>
            </div>
            {convos.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelect(c.id)}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-accent ${
                  activeId === c.id ? "bg-accent" : ""
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">
                  {c.title || `${c.type} conversation`}
                </span>
              </button>
            ))}
          </div>
        ))}
        {conversations.length === 0 && (
          <p className="p-3 text-xs text-muted-foreground">
            No conversations yet
          </p>
        )}
      </div>
    </div>
  );
}
