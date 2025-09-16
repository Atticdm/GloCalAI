"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import useSWR from "swr";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { createProject, fetchProjects, type Project } from "@/lib/api";

export default function DashboardPage() {
  const { token } = useAuth();
  const toast = useToast();
  const router = useRouter();
  const { data, isLoading, mutate } = useSWR<Project[]>(token ? "projects" : null, fetchProjects);
  const [projectName, setProjectName] = React.useState("");
  const [creating, setCreating] = React.useState(false);

  const onCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!projectName.trim()) {
      return;
    }
    try {
      setCreating(true);
      const project = await createProject(projectName.trim());
      setProjectName("");
      toast({ title: "Project created", description: project.name });
      await mutate();
      router.push(`/projects/${project.id}`);
    } catch (error) {
      console.error(error);
      toast({ title: "Failed to create project", description: "Try again" });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Projects</h1>
          <p className="text-sm text-slate-400">Manage localization pipelines across campaigns.</p>
        </div>
        <form onSubmit={onCreate} className="flex items-center gap-2">
          <Input
            placeholder="Project name"
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
          />
          <Button type="submit" disabled={creating}>
            {creating ? "Creating..." : "New Project"}
          </Button>
        </form>
      </section>
      <section>
        {isLoading ? (
          <p className="text-sm text-slate-400">Loading projects...</p>
        ) : data && data.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {data.map((project) => (
              <Card key={project.id}>
                <CardHeader>
                  <CardTitle>{project.name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-slate-300">
                  <p>Created at: {new Date(project.created_at).toLocaleString()}</p>
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/projects/${project.id}`}>Open project</Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-800 p-10 text-center text-slate-500">
            No projects yet. Create one to start the localization workflow.
          </div>
        )}
      </section>
    </div>
  );
}
