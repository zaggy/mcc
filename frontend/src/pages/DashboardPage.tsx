import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FolderKanban, Bot, MessageSquare, DollarSign } from "lucide-react";

const stats = [
  { label: "Projects", value: "0", icon: FolderKanban },
  { label: "Active Agents", value: "0", icon: Bot },
  { label: "Conversations", value: "0", icon: MessageSquare },
  { label: "Budget Used", value: "$0.00", icon: DollarSign },
];

export default function DashboardPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to Mission Control Center
        </p>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Getting Started</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>1. Create a project and connect a GitHub repository</p>
          <p>2. Configure your AI agents (Architect, Coder, Tester, Reviewer)</p>
          <p>3. Set up budget limits and notification preferences</p>
          <p>4. Start a conversation to kick off your first task</p>
        </CardContent>
      </Card>
    </div>
  );
}
