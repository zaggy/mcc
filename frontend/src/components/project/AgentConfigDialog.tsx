import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Agent } from "@/types";
import api from "@/lib/api";

const agentTypeColors: Record<string, string> = {
  orchestrator:
    "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  architect:
    "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  coder: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  tester:
    "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
  reviewer: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
};

interface AgentConfigDialogProps {
  agent: Agent;
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (agent: Agent) => void;
}

export default function AgentConfigDialog({
  agent,
  projectId,
  open,
  onOpenChange,
  onSaved,
}: AgentConfigDialogProps) {
  const [model, setModel] = useState(
    (agent.model_config_json.model as string) ?? ""
  );
  const [temperature, setTemperature] = useState(
    (agent.model_config_json.temperature as number) ?? 0.7
  );
  const [systemPrompt, setSystemPrompt] = useState(
    agent.system_prompt ?? ""
  );
  const [isActive, setIsActive] = useState(agent.is_active);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      const { data } = await api.patch<Agent>(
        `/projects/${projectId}/agents/${agent.id}`,
        {
          model_config_json: {
            ...agent.model_config_json,
            model: model || undefined,
            temperature,
          },
          system_prompt: systemPrompt || null,
          is_active: isActive,
        }
      );
      onSaved(data);
      onOpenChange(false);
    } catch {
      // handled silently
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {agent.name}
            <Badge
              variant="outline"
              className={agentTypeColors[agent.type] ?? ""}
            >
              {agent.type}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Configure model settings and system prompt for this agent.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="model">Model</Label>
            <Input
              id="model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Default (uses OpenRouter setting)"
              className="h-8 text-sm"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="temperature">Temperature</Label>
            <Input
              id="temperature"
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value) || 0)}
              className="h-8 text-sm w-24"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="system-prompt">System Prompt</Label>
            <Textarea
              id="system-prompt"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="Leave empty to use default prompt for this agent type"
              rows={6}
              className="text-sm"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="is-active"
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-input"
            />
            <Label htmlFor="is-active">Active</Label>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
