import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Bot, Plus, X, Github } from "lucide-react";
import type { Project, Agent } from "@/types";
import api from "@/lib/api";

const agentTypeColors: Record<string, string> = {
  orchestrator: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  architect: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  coder: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  tester: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
  reviewer: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
};

interface InfoPanelProps {
  project: Project;
  agents: Agent[];
  onAgentCreated: (agent: Agent) => void;
}

export default function InfoPanel({
  project,
  agents,
  onAgentCreated,
}: InfoPanelProps) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("coder");
  const [creating, setCreating] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      const { data } = await api.post(`/projects/${project.id}/agents`, {
        name: name.trim(),
        type,
      });
      onAgentCreated(data);
      setName("");
      setType("coder");
      setShowForm(false);
    } catch {
      // handled silently
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="flex h-full w-72 flex-col gap-4 overflow-y-auto border-l p-4">
      {/* Project Info */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Project</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="font-medium">{project.name}</p>
          {project.description && (
            <p className="text-muted-foreground">{project.description}</p>
          )}
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Github className="h-3.5 w-3.5" />
            <span className="text-xs">{project.github_repo}</span>
          </div>
          <Badge variant={project.is_active ? "default" : "secondary"}>
            {project.is_active ? "Active" : "Inactive"}
          </Badge>
        </CardContent>
      </Card>

      {/* Agents */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm">Agents</CardTitle>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          </Button>
        </CardHeader>
        <CardContent className="space-y-2">
          {showForm && (
            <form onSubmit={handleCreate} className="space-y-2 rounded-md border p-2">
              <Input
                placeholder="Agent name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-7 text-xs"
                required
              />
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="h-7 w-full rounded-md border bg-background px-2 text-xs"
              >
                <option value="orchestrator">Orchestrator</option>
                <option value="architect">Architect</option>
                <option value="coder">Coder</option>
                <option value="tester">Tester</option>
                <option value="reviewer">Reviewer</option>
              </select>
              <Button type="submit" size="xs" className="w-full" disabled={creating}>
                {creating ? "Adding..." : "Add Agent"}
              </Button>
            </form>
          )}

          {agents.length === 0 && !showForm && (
            <p className="text-xs text-muted-foreground">No agents yet</p>
          )}

          {agents.map((agent) => (
            <div
              key={agent.id}
              className="flex items-center gap-2 rounded-md border p-2"
            >
              <Bot className="h-4 w-4 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium">{agent.name}</p>
                <Badge
                  variant="outline"
                  className={agentTypeColors[agent.type] ?? ""}
                >
                  {agent.type}
                </Badge>
              </div>
              <span
                className={`h-2 w-2 rounded-full ${
                  agent.is_active ? "bg-green-500" : "bg-gray-300"
                }`}
              />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
