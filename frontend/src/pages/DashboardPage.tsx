import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FolderKanban, Bot, MessageSquare, DollarSign } from "lucide-react";
import api from "@/lib/api";
import type { Project } from "@/types";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/projects")
      .then(({ data }) => setProjects(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const activeCount = projects.filter((p) => p.is_active).length;

  const stats = [
    { label: "Projects", value: String(projects.length), icon: FolderKanban },
    { label: "Active Projects", value: String(activeCount), icon: Bot },
    { label: "Conversations", value: "—", icon: MessageSquare },
    { label: "Budget Used", value: "—", icon: DollarSign },
  ];

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
              <div className="text-2xl font-bold">
                {loading ? "…" : stat.value}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {projects.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Projects</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 font-medium">Name</th>
                    <th className="pb-2 font-medium">Repository</th>
                    <th className="pb-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((p) => (
                    <tr key={p.id} className="border-b last:border-0">
                      <td className="py-2">
                        <Link
                          to={`/projects/${p.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {p.name}
                        </Link>
                      </td>
                      <td className="py-2 text-muted-foreground">
                        {p.github_repo}
                      </td>
                      <td className="py-2">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                            p.is_active
                              ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
                              : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300"
                          }`}
                        >
                          {p.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

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
